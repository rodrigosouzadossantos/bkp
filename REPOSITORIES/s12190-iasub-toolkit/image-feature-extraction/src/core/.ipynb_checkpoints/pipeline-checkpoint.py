from core.metrics import Metrics
from core.logging import get_logger

import gc
import time
import logging
import numpy as np
import cv2
from pyspark.sql import Row

import nvidia.dali.fn as fn
import nvidia.dali.types as types
from nvidia.dali.pipeline import Pipeline

logger = get_logger()


# ──────────────────────────────────────────────
#  DALI Pipeline
# ──────────────────────────────────────────────

class DecodePipeline(Pipeline):
  """
  NVIDIA DALI pipeline for GPU-accelerated JPEG decoding.

  One instance is built per Spark partition and reused across all
  batches, keeping CUDA allocations stable throughout the partition
  lifetime.
  """

  def __init__(self, batch_size: int, num_threads: int = 4):
    super().__init__(
      batch_size=batch_size,
      num_threads=num_threads,
      device_id=0,
      exec_async=False,
      exec_pipelined=False,
      prefetch_queue_depth=1,
    )

    self.input = fn.external_source(
      name="input_bytes",
      dtype=types.UINT8,
    )

  def define_graph(self):
    jpegs = self.input
    images = fn.decoders.image(
      jpegs,
      device="mixed",
      output_type=types.RGB,
    )
    return images


# ──────────────────────────────────────────────
#  Low-level helpers
# ──────────────────────────────────────────────

def _row_to_numpy(row) -> np.ndarray | None:
  """Convert a Spark row's binary content to a uint8 numpy array."""
  if row.content is None:
    return None
  return np.frombuffer(row.content, dtype=np.uint8)


def _pad_batch(contents: list, target_size: int) -> list:
  """
  Pad *contents* to *target_size* by repeating the last element.

  DALI pipelines are built with a fixed batch_size; the final batch of
  a partition is often smaller, so we pad it and later discard the
  extra decoded images.
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
  """Convert an RGB image (from DALI) to BGR (OpenCV convention)."""
  return cv2.cvtColor(img_rgb, cv2.COLOR_RGB2BGR)


def _build_context(row, img_bgr: np.ndarray) -> dict:
  """
  Assemble the per-image context dict consumed by feature extractors.

  Pre-computes the grayscale version once so individual extractors do
  not need to repeat the conversion.
  """
  return {
    "path":   row.path,
    "img":    img_bgr,
    "gray":   cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY),
    "_cache": {},
  }


def _null_row(row, features) -> Row:
  """Return a Row with all feature values set to None."""
  result = {"path": row.path}
  for f in features:
    result[f.name] = None
  return Row(**result)


# ──────────────────────────────────────────────
#  Batch-level operations
# ──────────────────────────────────────────────

def _prepare_batch(batch_rows: list, metrics: Metrics):
  """
  Validate rows and build the list of numpy byte-buffers for DALI.

  Returns:
    contents   – list[np.ndarray]  (valid encoded images)
    valid_rows – list[Row]         (rows that match each buffer)
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


def _decode_batch(pipe: DecodePipeline, contents: list, actual_size: int):
  """
  Feed *contents* into *pipe*, run one iteration, and return decoded
  uint8 numpy arrays for the first *actual_size* images (padding is
  silently discarded).

  Raises the underlying DALI / CUDA exception on failure so callers
  can handle it uniformly.
  """
  padded = _pad_batch(contents, pipe.batch_size)

  pipe.feed_input("input_bytes", padded)
  dali_out          = pipe.run()
  images_tensorlist = dali_out[0]

  imgs = []
  for i in range(actual_size):
    tensor_cpu = images_tensorlist[i].as_cpu()
    imgs.append(_tensor_to_uint8(tensor_cpu))

  return imgs


def _extract_features(row, img_rgb: np.ndarray, features, metrics, profiler) -> Row:
  """
  Run every feature extractor against *img_rgb* and return a Row.

  Each extractor is timed individually; failures are caught per-feature
  so a single bad extractor does not abort the whole row.
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

def _process_batch(pipe, batch_rows, features, metrics, profiler, max_retries):
  """
  Decode one batch with DALI and extract features row by row.

  Yields Row objects — either fully populated or null-filled on error.
  """
  contents, valid_rows = _prepare_batch(batch_rows, metrics)

  if not contents:
    return

  # ── GPU decode ──────────────────────────────
  try:
    imgs = _decode_batch(pipe, contents, len(valid_rows))
    metrics.inc("dali_decode_success")
  except Exception as exc:
    logger.error(f"DALI pipeline failed: {exc}")
    metrics.inc("dali_decode_fail")
    for row in valid_rows:
      yield _null_row(row, features)
      metrics.inc("rows_fail")
    return

  # ── Feature extraction ──────────────────────
  for i, row in enumerate(valid_rows):
    for attempt in range(max_retries + 1):
      try:
        yield _extract_features(row, imgs[i], features, metrics, profiler)
        metrics.inc("rows_ok")
        break
      except Exception as exc:
        if attempt == max_retries:
          logger.error(
            f"Row processing failed after {max_retries} retries: {exc}"
          )
          metrics.inc("rows_fail")
          yield _null_row(row, features)
        else:
          metrics.inc("retries")
          logger.debug(f"Retry {attempt + 1}/{max_retries} for {row.path}")


# ──────────────────────────────────────────────
#  Public entry point
# ──────────────────────────────────────────────

def process_partition(features, max_retries: int = 2, batch_size: int = 64):
  """
  Return a Spark mapPartitions-compatible function that processes each
  partition with a single DALI pipeline instance.

  The pipeline is built once at partition start and destroyed at the
  end, keeping GPU memory pressure low and constant.

  Args:
    features:    List of feature extractor objects (must expose
                 .name and .extract(ctx)).
    max_retries: Per-row retry budget for feature extraction.
    batch_size:  Number of images per DALI decode call.  Smaller values
                 reduce peak VRAM usage; 32–64 is a safe default for
                 most GPU configurations running alongside Spark.
  """

  def _inner(iterator):
    from core.profiler_instance import PROFILER

    metrics = Metrics()

    rows = list(iterator)
    if not rows:
      return

    # ── Build pipeline once for this partition ──
    pipe = DecodePipeline(batch_size=batch_size)
    pipe.build()

    try:
      for i in range(0, len(rows), batch_size):
        batch_rows = rows[i : i + batch_size]
        yield from _process_batch(
          pipe, batch_rows, features, metrics, PROFILER, max_retries
        )
    finally:
      # ── Guaranteed cleanup regardless of exceptions ──
      del pipe
      gc.collect()

    # ── Partition summary ────────────────────────────
    logger.info({"feature_profile": PROFILER.snapshot()})
    logger.info(f"Partition metrics: {metrics.report()}")

  return _inner

