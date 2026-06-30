from .base import FeatureExtractor

import cv2
from pyspark.sql.types import IntegerType, FloatType


class ImageStatsExtractor(FeatureExtractor):
  name = "image_stats"
  order = 1

  def extract(self, ctx):
    img = ctx["img"]
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

    mean_b, mean_g, mean_r = img.mean(axis=(0, 1))

    return {
      "width": int(img.shape[1]),
      "height": int(img.shape[0]),
      "brightness": float(hsv[:, :, 2].mean()),
      "contrast": float(img.std()),
      "blur": float(cv2.Laplacian(img, cv2.CV_64F).var()),
      "mean_r": float(mean_r),
      "mean_g": float(mean_g),
      "mean_b": float(mean_b),
    }

  def schema(self):
    return {
      "width": IntegerType(),
      "height": IntegerType(),
      "brightness": FloatType(),
      "contrast": FloatType(),
      "blur": FloatType(),
      "mean_r": FloatType(),
      "mean_g": FloatType(),
      "mean_b": FloatType(),
    }
