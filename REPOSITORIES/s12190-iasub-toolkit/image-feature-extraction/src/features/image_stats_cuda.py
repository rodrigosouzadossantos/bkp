from .base import FeatureExtractor

import cv2
from pyspark.sql.types import IntegerType, FloatType
from pyspark.sql.types import *

from nvidia import nvimgcodec
import cupy as cp
import numpy as np

import threading

_thread_local = threading.local()

import logging

import ctypes, ctypes.util

#libtiff = ctypes.CDLL("libtiff.so.5") 
#libtiff.TIFFSetWarningHandler.argtypes = [ctypes.c_void_p]
#libtiff.TIFFSetWarningHandler(None)

_libtiff = ctypes.util.find_library("tiff")
if _libtiff:
    ctypes.cdll.LoadLibrary(_libtiff).TIFFSetWarningHandler(None)

import os
os.environ["OPENCV_LOG_LEVEL"] = "ERROR"


class ImageStatsExtractor(FeatureExtractor):
  name = "image_stats_cuda"
  order = 1

  def __init__(self):
    self._decoder = None #nvimgcodec.Decoder()

  @property
  def decoder(self):
    if not hasattr(_thread_local, 'decoder') or _thread_local.decoder is None:
      from nvidia import nvimgcodec
      _thread_local.decoder = nvimgcodec.Decoder(backends=[
        nvimgcodec.Backend(nvimgcodec.BackendKind.CPU_ONLY),
        nvimgcodec.Backend(nvimgcodec.BackendKind.GPU_ONLY),
      ])
    return _thread_local.decoder

  def extract(self, ctx):

    return self.process_record(ctx['content'], ctx['path'])


  def schema(self):
    return {
      "format_info": StructType([
        #StructField("codec", StringType(), True),
        StructField("resolution", ArrayType(IntegerType()), True),
        #StructField("dtype", StringType(), True)
      ]),

      "subsea_eda": StructType([
        StructField("uciqe_score", DoubleType(), True),      # Qualidade científica
        StructField("red_loss_ratio", DoubleType(), True),   # Atenuação de cor
        StructField("avg_saturation", DoubleType(), True),   # Saturação subaquática
        StructField("sharpness_tenengrad", DoubleType(), True),
        StructField("data_coverage_pct", DoubleType(), True) # Pixels úteis vs pretos
      ]),

      "clustering_identity": StructType([
        StructField("phash", StringType(), True),            # Detecção de duplicatas
        StructField("feature_vector", ArrayType(LongType()), True) # Histograma RGB p/ K-Means
      ]),
    }


  def decode_geokeys(self, directory):
    if directory is None: return {}
    KEYS = {1024: "ModelType", 1025: "RasterType", 2048: "GeogType", 3072: "ProjType"}
    decoded = {}
    for i in range(1, int(directory[3]) + 1):
      k, v = directory[i*4], directory[i*4 + 3]
      decoded[KEYS.get(k, f"Key_{k}")] = int(v)
    return decoded

  def process_record(self, image_bytes, record_id):

    #logging.warning(f"[{record_id}] gpu_img.shape={gpu_img.shape} dtype={gpu_img.dtype}")
    # --- 1. Decode & Header Parsing ---
    cs = nvimgcodec.CodeStream(image_bytes)

    #self.process_metadata(cs)

    return self.process_image(cs)

    #try:
    #  self.metadata(cs)
    ##  # 3. Process the tags using your existing logic structure
    ##  #tags = {
    ##  #    str(m.id): (m.buffer.decode('utf-8') if m.kind != nvimgcodec.MetadataKind.ICC_PROFILE else m.buffer[:20])
    ##  #    for m in metadata
    ##  #}
    ##  #tags = {
    ##  #  #str(t.id): (t.value.tolist() if isinstance(t.value, np.ndarray) else str(t.value))
    ##  #  #for t in image.metadata
    ##  #  str(t.id): (t.value.tolist() if hasattr(t.value, 'tolist') else str(t.value))
    ##  #  for t in image.info.metadata
    ##  #}
    #  tags = {}
    ##  for m in metadata_items:
    ##      # Convert buffer to list/string so we can use it for bbox math
    ##      if m.kind == nvimgcodec.MetadataKind.UNKNOWN:
    ##          # For GeoTIFF/EXIF tags, m.value is often a numpy array or scalar
    ##          tags[m.id] = m.value 
    ##      else:
    ##          tags[m.id] = m.buffer.decode('utf-8', errors='ignore') if hasattr(m, 'buffer') else m.value
    #except AttributeError:
    #  tags = {}

    # --- 2. Spatial / GeoTIFF Logic ---
    ##geokeys = self.decode_geokeys(image.metadata.get(34735))

    #bbox, center = None, None
    ##if "33922" in tags and "33550" in tags:
    ##  t, p = image.metadata[33922], image.metadata[33550]
    ##  bbox = [float(t[3]), float(t[4] - (h * p[1])), float(t[3] + (w * p[0])), float(t[4])]
    ##  center = [float(t[3] + (w * p[0]/2)), float(t[4] - (h * p[1]/2))]

  def process_metadata(self, cs):
    from PIL.TiffTags import TAGS
    #print("Number of images:", cs.num_images)
    for code_stream_idx in range(0, cs.num_images):
      #try:
        scs = cs.get_sub_code_stream(code_stream_idx)
        for tag_id, tag_name in TAGS.items():
          if not isinstance(tag_id, int):
            continue
          try:
            tag_metadata = self.decoder.get_metadata(scs, id=tag_id)
            if tag_metadata is not None:
              print(f"Image #{code_stream_idx} {tag_name}: {tag_metadata.value}")
          except Exception as e:
            pass

        #metadata = self.decoder.get_metadata(scs)
        #if len(metadata) > 0:
          #print(f"No metadata for image {code_stream_idx}")
          #print("="*50)
        #else:
          #print(f"Metadata for image {code_stream_idx}:")
          #print("="*50)
          #for m in metadata:
          #  print(m)
          #  if m.kind != nvimgcodec.MetadataKind.ICC_PROFILE:
          #    print(" "*5, m.buffer.decode('utf-8'))
          #  else:
          #    print(f"{' ' * 5}{m.buffer[:200]}")

      #except Exception as e:
      #  print(f">>> An error occurred: {e}")


  def process_image(self, cs):

    ## --- 3. GPU Features ---
    #codec = cs.codec_name
    scs = cs.get_sub_code_stream(0)
    image = self.decoder.decode(scs)

    w, h = image.width, image.height
    #dtype = image.sample_type

    gpu_img = cp.asarray(image.cuda()).astype(cp.float32)

    del image

    # Normalize shape to (H, W, 3) regardless of source channels
    if gpu_img.ndim == 2:
      # Grayscale → replicate to RGB
      gpu_img = cp.stack([gpu_img, gpu_img, gpu_img], axis=2)
    elif gpu_img.ndim == 3 and gpu_img.shape[2] == 1:
      # Single-channel with trailing dim → replicate
      gpu_img = cp.repeat(gpu_img, 3, axis=2)
    elif gpu_img.ndim == 3 and gpu_img.shape[2] == 4:
      # RGBA → drop alpha
      gpu_img = gpu_img[:, :, :3]
    elif gpu_img.ndim == 3 and gpu_img.shape[2] > 4:
      # Multispectral (e.g. sonar with N bands) → take first 3
      gpu_img = gpu_img[:, :, :3]
    # else: already (H, W, 3) — nothing to do

    max_val = float(cp.max(gpu_img))
    if max_val > 255.0:
      gpu_img = gpu_img * (255.0 / max_val)

    r, g, b = gpu_img[:,:,0], gpu_img[:,:,1], gpu_img[:,:,2]

    ## Subsea Specifics
    red_loss = (
      float(cp.mean(r)) / (
        float(cp.mean(g)) + float(cp.mean(b)) + 1e-7
      )
    )

    r_f = r.astype(cp.float32)
    g_f = g.astype(cp.float32)
    b_f = b.astype(cp.float32)

    ## UCIQE (Quality Index)
    #chroma_a = r.astype(cp.float32) - g.astype(cp.float32)
    #chroma_b = 0.5 * (r.astype(cp.float32) + g.astype(cp.float32)) - b.astype(cp.float32)
    chroma_a = r_f - g_f
    chroma_b = 0.5 * (r_f + g_f) - b_f
    del r_f, g_f, b_f

    chroma = cp.sqrt(chroma_a**2 + chroma_b**2)
    del chroma_a, chroma_b

    uciqe = float(
        (0.4680 * cp.std(chroma))
      + (0.2745 * float(cp.max(r)) - float(cp.min(r)))
      + (0.2576 * cp.mean(chroma))
    )
    avg_sat = float(cp.mean(chroma) / 255.0)
    del chroma

    coverage = float(cp.count_nonzero(gpu_img) / gpu_img.size)

    # Sharpness & Identity
    dx, dy = cp.diff(gpu_img, axis=1), cp.diff(gpu_img, axis=0)
    sharpness = float(cp.var(cp.sqrt(dx[:-1, :]**2 + dy[:, :-1]**2)))

    ## pHash for Duplicates
    #img_small = cp.resize(gpu_img, (8, 8))
    #phash = "".join(["1" if x > cp.mean(img_small) else "0" for x in img_small.flatten().tolist()])
    #phash_hex = hex(int(phash, 2))[2:]
    from cupyx.scipy.ndimage import zoom as cp_zoom
    gray = (0.299 * r + 0.587 * g + 0.114 * b)

    img_small = cp_zoom(gray, (8.0 / gray.shape[0], 8.0 / gray.shape[1]), order=1)
    del gray

    flat = img_small.flatten()
    del img_small

    mean_val = float(cp.mean(flat))
    bits = "".join("1" if float(x) > mean_val else "0" for x in flat.tolist())
    del flat

    phash_hex = f"{int(bits, 2):016x}"

    ## Cluster Vector (RGB Histogram 3x32 bins)
    h_r = cp.histogram(r, 32, (0, 255))[0]
    h_g = cp.histogram(g, 32, (0, 255))[0]
    h_b = cp.histogram(b, 32, (0, 255))[0]
    cluster_vec = [int(x) for x in
      cp.concatenate([h_r, h_g, h_b]).tolist()
    ]

    del gpu_img, r, g, b
    cp.get_default_memory_pool().free_all_blocks()

    return {
      "format_info": {
        #"codec": codec,
        "resolution": [int(w), int(h)],
        #"dtype": str(dtype)
      },
      "subsea_eda": {
        "uciqe_score": float(uciqe),
        "red_loss_ratio": float(red_loss),
        "avg_saturation": float(avg_sat),
        "sharpness_tenengrad": sharpness,
        "data_coverage_pct": float(coverage)
      },
      "clustering_identity": {
        "phash": str(phash_hex),
        "feature_vector": cluster_vec
      },
    }
