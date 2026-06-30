from .base import FeatureExtractor

import io
from PIL import Image, ExifTags
from pyspark.sql.types import MapType, StringType


class ExifExtractor(FeatureExtractor):
  name = "exif"
  order = 4

  def extract(self, ctx):
    content = ctx["content"]
    exif_dict = {}

    try:
      img = Image.open(io.BytesIO(content))

      if hasattr(img, "_getexif") and img._getexif():
        for tag, value in img._getexif().items():
          tag_name = ExifTags.TAGS.get(tag, str(tag))
          exif_dict[tag_name] = str(value)

    except Exception:
      pass

    return {
      "exif": exif_dict
    }

  def schema(self):
    return {
      "exif": MapType(StringType(), StringType())
    }
