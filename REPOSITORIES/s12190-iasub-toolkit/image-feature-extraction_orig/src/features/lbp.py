from .base import FeatureExtractor

import cupy as cp
import numpy as np
from pyspark.sql.types import ArrayType, FloatType
import logging

logger = logging.getLogger(__name__)

class LBPExtractorGPUKernel(FeatureExtractor):
  """GPU-accelerated LBP using CuPy array operations"""

  name = "lbp_gpu_kernel"
  order = 3

  def __init__(self):
    super().__init__()
    self.device_id = 0

  def extract(self, ctx):
    """
    Extract LBP histogram on GPU

    Args:
        ctx: Context with 'gray' (CPU numpy array)

    Returns:
        Dictionary with LBP histogram
    """
    try:
      gray = ctx["gray"]  # NumPy array on CPU

      # Transfer to GPU
      gray_gpu = cp.asarray(gray, dtype=cp.uint8)

      # Fast LBP computation
      lbp_gpu = self._compute_lbp_fast(gray_gpu)

      # Histogram on GPU
      hist_gpu = cp.histogram(
        lbp_gpu.ravel(),
        bins=20,
        range=(0, 20),
        density=True
      )[0]

      # Transfer back to CPU and convert to list
      hist = cp.asnumpy(hist_gpu).astype(float).tolist()

      return {"lbp_hist": hist}

    except Exception as e:
      logger.error(f"LBP GPU extraction failed: {e}")
      return {"lbp_hist": [0.0] * 20}

  @staticmethod
  def _compute_lbp_fast(gray_gpu):
    """
    Fast LBP computation using GPU array operations

    Args:
        gray_gpu: CuPy array (grayscale image on GPU)

    Returns:
        CuPy array with LBP values
    """
    height, width = gray_gpu.shape

    # Extract center region (exclude borders)
    center = gray_gpu[1:-1, 1:-1]

    # Initialize LBP result array
    lbp = cp.zeros_like(center, dtype=cp.uint8)

    # Compute LBP by comparing 8 neighbors to center pixel
    # Neighbor positions in circular order (0-7):
    # 0 1 2
    # 7 C 3
    # 6 5 4

    neighbors = [
      gray_gpu[:-2, :-2],     # 0: top-left
      gray_gpu[:-2, 1:-1],    # 1: top
      gray_gpu[:-2, 2:],      # 2: top-right
      gray_gpu[1:-1, 2:],     # 3: right
      gray_gpu[2:, 2:],       # 4: bottom-right
      gray_gpu[2:, 1:-1],     # 5: bottom
      gray_gpu[2:, :-2],      # 6: bottom-left
      gray_gpu[1:-1, :-2],    # 7: left
    ]

    # Build binary pattern: if neighbor >= center, set bit
    for i, neighbor in enumerate(neighbors):
      lbp += cp.where(neighbor >= center, 1 << i, 0).astype(cp.uint8)

    # Pad result back to original dimensions
    lbp_padded = cp.zeros((height, width), dtype=cp.uint8)
    lbp_padded[1:-1, 1:-1] = lbp

    return lbp_padded

  def schema(self):
    """Return schema for Spark"""
    return {
      "lbp_hist": ArrayType(FloatType())
    }

