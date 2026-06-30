from .base import FeatureExtractor

import numpy as np
from skimage.feature import local_binary_pattern
from pyspark.sql.types import ArrayType, FloatType


class LBPExtractor(FeatureExtractor):
  name = "lbp"
  order = 3

  def extract(self, ctx):
    gray = ctx["gray"]

    lbp = local_binary_pattern(gray, P=8, R=1, method="uniform")

    hist, _ = np.histogram(
      lbp.ravel(),
      bins=20,
      range=(0, 20),
      density=True
    )

    return {
      "lbp_hist": hist.astype(float).tolist()
    }

  def schema(self):
    return {
      "lbp_hist": ArrayType(FloatType())
    }
