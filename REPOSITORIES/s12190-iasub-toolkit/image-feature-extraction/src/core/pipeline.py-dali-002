from core.metrics import Metrics
from core.logging import get_logger

import gc
import time
import threading
import numpy as np
import cv2
from pyspark.sql import Row

import nvidia.dali.fn as fn
import nvidia.dali.types as types
from nvidia.dali.pipeline import Pipeline

logger = get_logger()


# ──────────────────────────────────────────────
#  GPU concurrency guard
#
#  Spark runs N tasks in parallel on the same GPU. Without a semaphore,
#  every task calls pipe.build() simultaneously, each requesting large
#  CUDA pre-allocations and instantly exhausting VRAM.
#
#  Serializing build() costs only ~100-200 ms per partition. Decode
#  itself is NOT under the lock, so GPU parallelism is preserved.
# ──────────────────────────────────────────────

_GPU_BUILD_LOCK = threading.Semaphore(1)


# ──────────────────────────────────────────────
#  DALI Pipeline
# ──────────────────────────────────────────────

class DecodePipeline(Pipeline):
  """
  NVIDIA DALI pipeline for GPU-accelerated JPEG decoding.

  - Uses batch_size (the correct kwarg for DALI 2.1.0).
  - max_batch_size attribute is set manually for internal use so
    _decode_batch_gpu can read it without touching DALI internals.
  - __del__ is overridden to suppress DALI's own broken __del__ which
    crashes with AttributeError when build() was never called.
  """

  def __init__(self, batch_size: int, num_threads: int = 2):
    # Store before super().__init__ so __del__ is always safe.
    self._built       = False
    self._batch_size = batch_size

    super().__init__(
      batch_size=batch_size,
      num_threads=num_threads,
      device_id=0,
      exec_async=False,
      exec_pipelined=False,
      prefetch_queue_depth=1,
    )

  def define_graph(self):
    jpegs = fn.external_source(
      name="input_bytes",
      dtype=types.UINT8,
    )
    images = fn.decoders.image(
      jpegs,
      device="mixed",
      output_type=types.RGB,
    )
    return images

  def build(self):
    super().build()
    self._built = True

  def __del__(self):
    # DALI 2.1.0 __del__ raises AttributeError when _pipe was never
    # set (i.e. build() raised before backend init). Guard it here.
    try:
      super().__del__()
    except Exception:
      pass


# ──────────────────────────────────────────────
#  Pipeline factory with serialized build + retry
# ──────────────────────────────────────────────

def _build_pipeline(batch_size: int, max_attempts: int = 4) -> "DecodePipeline | None":
  """
  Build a DecodePipeline under the GPU lock with exponential backoff.

  Returns the built pipeline, or None when all attempts fail (caller
  then falls back to CPU decoding for the whole partition).
  """
  wait = 1.0

  for attempt in range(1, max_attempts + 1):
    with _GPU_BUILD_LOCK:
      try:
        pipe = DecodePipeline(batch_size=batch_size)
        pipe.build()
        logger.debug(f"DALI pipeline built (attempt {attempt}, batch_size={batch_size})")
        return pipe
      except (MemoryError, RuntimeError, Exception) as exc:
        # Catch broadly: DALI wraps CUDA OOM as RuntimeError or
        # plain Exception depending on the version.
        logger.warning(
          f"DALI build failed (attempt {attempt}/{max_attempts}, "
          f"batch_size={batch_size}): {exc}"
        )
        gc.collect()

    if attempt < max_attempts:
      logger.debug(f"Retrying DALI build in {wait:.1f}s")
      time.sleep(wait)
      wait *= 2.0

  logger.error(
    f"All {max_attempts} DALI build attempts failed — "
    "partition will use CPU decoder"
  )
  return None


# ──────────────────────────────────────────────
#  CPU fallback decoder
# ──────────────────────────────────────────────

def _decode_cpu(contents: list) -> list:
  """
  Decode JPEG byte-buffers with OpenCV (CPU).

  Zero VRAM required. Returns one uint8 RGB ndarray per input buffer,
  or None for buffers that fail to decode.
  """
  imgs = []
  for buf in contents:
    bgr = cv2.imdecode(buf, cv2.IMREAD_COLOR)
    if bgr is None:
      imgs.append(None)
    else:
      imgs.append(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB))
  return imgs


# ──────────────────────────────────────────────
#  Low-level helpers
# ──────────────────────────────────────────────

def _row_to_numpy(row) -> "np.ndarray | None":
  """Convert a Spark row's binary content to a uint8 numpy array."""
  if row.content is None:
    return None
  return np.frombuffer(row.content, dtype=np.uint8)


def _pad_batch(contents: list, target_size: int) -> list:
  """
  Pad *contents* to *target_size* by repeating the last element.

  DALI requires exactly batch_size items per feed. The final batch of
  a partition is often smaller; we pad and discard extras after decode.
  """
  deficit = target_size - len(contents)
  if deficit > 0:
    contents = contents + [contents[-1]] * deficit
  return contents


def _tensor_to_uint8(tensor_cpu) -> np.ndarray:
  """Convert a DALI CPU tensor to a contiguous uint8 numpy array."""
  arr = np.array(tensor_cpu)
  if arr.dtype != np.uint8:
    arr = arr.astype(np.uint8)
  return np.ascontiguousarray(arr)


def _rgb_to_bgr(img_rgb: np.ndarray) -> np.ndarray:
  """Convert an RGB image (DALI output) to BGR (OpenCV convention)."""
  return cv2.cvtColor(img_rgb, cv2.COLOR_RGB2BGR)


def _build_context(row, img_bgr: np.ndarray) -> dict:
  """
  Assemble the per-image context dict for feature extractors.

  Grayscale is pre-computed once here so extractors never repeat it.
  """
  return {
    "path":   row.path,
    "img":    img_bgr,
    "gray":   cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY),
    "_cache": {},
  }


def _null_row(row, features) -> Row:
  """Return a Row with path filled and all feature values as None."""
  result = {"path": row.path}
  for f in features:
    result[f.name] = None
  return Row(**result)


# ──────────────────────────────────────────────
#  Batch-level operations
# ──────────────────────────────────────────────

def _prepare_batch(batch_rows: list, metrics: Metrics):
  """
  Validate rows and build numpy byte-buffers for the decoder.

  Returns:
    contents   – list[np.ndarray]  valid encoded image buffers
    valid_rows – list[Row]         rows aligned 1-to-1 with contents
  """
  contents   = []
  valid_rows = []

  for row in batch_rows:
    arr = _row_to_numpy(row)
    if arr is None:
      metrics.inc("row_content_none")
      continue
    contents.append(arr)
    valid_rows.append(row)

  return contents, valid_rows


def _decode_batch_gpu(
  pipe: DecodePipeline,
  contents: list,
  actual_size: int,
) -> list:
  """
  Feed *contents* into *pipe*, run one step, return decoded arrays.

  Only the first *actual_size* outputs are returned; padding is dropped.
  Raises on any DALI/CUDA error so the caller can fall back to CPU.
  """
  padded = _pad_batch(contents, pipe._batch_size)

  pipe.feed_input("input_bytes", padded)
  dali_out          = pipe.run()
  images_tensorlist = dali_out[0]

  imgs = []
  for i in range(actual_size):
    tensor_cpu = images_tensorlist[i].as_cpu()
    imgs.append(_tensor_to_uint8(tensor_cpu))

  return imgs


def _decode_batch(
  pipe: "DecodePipeline | None",
  contents: list,
  metrics: Metrics,
) -> tuple:
  """
  Decode *contents* via GPU when pipe is available, CPU otherwise.

  Returns (imgs: list, source: str) where source is "gpu" or "cpu".
  """
  if pipe is not None:
    try:
      imgs = _decode_batch_gpu(pipe, contents, len(contents))
      return imgs, "gpu"
    except Exception as exc:
      logger.warning(f"GPU decode failed mid-batch, falling back to CPU: {exc}")
      metrics.inc("dali_mid_batch_fail")

  return _decode_cpu(contents), "cpu"


def _extract_features(
  row,
  img_rgb: np.ndarray,
  features,
  metrics: Metrics,
  profiler,
) -> Row:
  """
  Run all feature extractors on *img_rgb* and return a populated Row.

  Each extractor is timed and isolated: one failure does not abort
  the others.
  """
  img_bgr = _rgb_to_bgr(img_rgb)
  ctx     = _build_context(row, img_bgr)
  result  = {"path": ctx["path"]}

  for f in features:
    t0 = time.time()
    try:
      result.update(f.extract(ctx))
      metrics.inc(f"{f.name}_ok")
    except Exception as exc:
      logger.warning(f"{f.name} extraction failed: {exc}")
      metrics.inc(f"{f.name}_fail")
      result[f.name] = None
    finally:
      profiler.record(f.name, time.time() - t0)

  return Row(**result)


# ──────────────────────────────────────────────
#  Partition-level orchestration
# ──────────────────────────────────────────────

def _process_batch(
  pipe,
  batch_rows: list,
  features,
  metrics: Metrics,
  profiler,
  max_retries: int,
):
  """
  Decode one batch and extract features row by row.

  Yields fully populated or null-filled Row objects.
  """
  contents, valid_rows = _prepare_batch(batch_rows, metrics)

  if not contents:
    return

  # ── Decode (GPU with CPU fallback) ──────────
  imgs, source = _decode_batch(pipe, contents, metrics)
  metrics.inc(f"decode_{source}")

  # ── Per-row feature extraction ───────────────
  for i, row in enumerate(valid_rows):
    img_rgb = imgs[i]

    if img_rgb is None:
      logger.warning(f"Null decode for {row.path}")
      metrics.inc("decode_none")
      yield _null_row(row, features)
      continue

    for attempt in range(max_retries + 1):
      try:
        yield _extract_features(row, img_rgb, features, metrics, profiler)
        metrics.inc("rows_ok")
        break
      except Exception as exc:
        if attempt == max_retries:
          logger.error(
            f"Row failed after {max_retries} retries ({row.path}): {exc}"
          )
          metrics.inc("rows_fail")
          yield _null_row(row, features)
        else:
          metrics.inc("retries")
          logger.debug(f"Retry {attempt + 1}/{max_retries} — {row.path}")


# ──────────────────────────────────────────────
#  Public entry point
# ──────────────────────────────────────────────

def process_partition(
  features,
  max_retries: int = 2,
  batch_size:  int = 8,
):
  """
  Return a Spark mapPartitions-compatible generator function.

  Design decisions
  ────────────────
  batch_size=8   DALI pre-allocates decode scratch proportional to
                 batch_size × worst-case decoded image size. 8 images
                 costs ~180 MB vs ~1.4 GB at 64, leaving budget for
                 RAPIDS and concurrent tasks on the same GPU.

  GPU semaphore  _GPU_BUILD_LOCK serializes pipe.build() calls across
                 all Spark tasks sharing the process. Decode itself is
                 NOT locked, preserving GPU parallelism.

  CPU fallback   If GPU memory is exhausted at build time the partition
                 still completes using cv2.imdecode, yielding real
                 feature values rather than all-None rows.

  Args:
    features:    Extractor objects exposing .name and .extract(ctx).
    max_retries: Per-row retry budget for feature extraction failures.
    batch_size:  Images per DALI decode call (keep ≤ 16 with RAPIDS).
  """

  def _inner(iterator):
    from core.profiler_instance import PROFILER

    metrics = Metrics()

    rows = list(iterator)
    if not rows:
      return

    # ── Build pipeline once for this partition ──
    pipe = _build_pipeline(batch_size=batch_size)
    if pipe is None:
      metrics.inc("gpu_build_failed")

    try:
      for i in range(0, len(rows), batch_size):
        batch_rows = rows[i : i + batch_size]
        yield from _process_batch(
          pipe, batch_rows, features, metrics, PROFILER, max_retries
        )
    finally:
      if pipe is not None:
        del pipe
        gc.collect()

    # ── Partition summary ────────────────────────
    logger.info({"feature_profile": PROFILER.snapshot()})
    logger.info(f"Partition metrics: {metrics.report()}")

  return _inner

