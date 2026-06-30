from .base import FeatureExtractor

import cv2
from pyspark.sql.types import ArrayType, FloatType


class HistogramExtractor(FeatureExtractor):
  name = "histogram"
  order = 2

  def extract(self, ctx):
    img = ctx["img"]
    rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

    def norm_hist(channel):
      h = cv2.calcHist([rgb], [channel], None, [32], [0, 256]).flatten()
      s = h.sum()
      return (h / s if s > 0 else h).astype(float).tolist()

    return {
      "hist_r": norm_hist(0),
      "hist_g": norm_hist(1),
      "hist_b": norm_hist(2),
    }

  def schema(self):
    return {
      "hist_r": ArrayType(FloatType()),
      "hist_g": ArrayType(FloatType()),
      "hist_b": ArrayType(FloatType()),
    }
