import os
import json
from typing import Dict, Any

import numpy as np
from PIL import Image
import rasterio
from rasterio.io import MemoryFile

import tifffile

# pip install pyexiftool
import exiftool

from pyspark.sql import SparkSession


def normalize(obj):
    if hasattr(obj, "to_string"):
        return obj.to_string()
    return obj

# ----------------------------
# EXIFTOOL WRAPPER (NO subprocess)
# ----------------------------
class ExifToolReader:
    def __init__(self):
        self.et = exiftool.ExifToolHelper()

    def get_metadata(self, path: str):
        try:
            result = self.et.get_metadata(path)
            return result[0] if result else {}
        except Exception:
            return {}

    def close(self):
        pass


# ----------------------------
# TIFF STRUCTURE EXTRACTOR
# ----------------------------
class TIFFExtractor:

    def _normalize(self, obj):
        if obj is None:
            return None

        if isinstance(obj, str):
            return obj

        if hasattr(obj, "to_string"):
            return obj.to_string()

        return str(obj)

    def extract_structure(self, path: str) -> Dict[str, Any]:
        with rasterio.open(path) as src:

            bands = src.count
            height = src.height
            width = src.width

            dtype = src.dtypes[0]

            return {
                "driver": src.driver,
                "width": width,
                "height": height,
                "count": bands,
                "dtypes": src.dtypes,
                "nodata": src.nodata,
                "crs": self._normalize(src.crs),
                "transform": list(src.transform),
                "bounds": list(src.bounds),
                "res": list(src.res),
                "metadata": dict(src.meta),
                "band_tags": {
                    str(i + 1): src.tags(i + 1)
                    for i in range(bands)
                },
                "tags": src.tags()
            }


# ----------------------------
# IMAGE INFO (PIL ONLY)
# ----------------------------
class ImageExtractor:

    def extract(self, path: str) -> Dict[str, Any]:
        with Image.open(path) as img:
            return {
                "format": img.format,
                "mode": img.mode,
                "size": list(img.size),
                "bands": img.getbands(),
                "info": dict(img.info)
            }


# ----------------------------
# TIFF LOW LEVEL STRUCTURE
# ----------------------------
class TIFFStructureExtractor:

    def extract(self, path: str) -> Dict[str, Any]:
        with tifffile.TiffFile(path) as tif:

            pages = []
            for i, page in enumerate(tif.pages):
                pages.append({
                    "index": i,
                    "shape": page.shape,
                    "dtype": str(page.dtype),
                    "compression": str(page.compression),
                    "photometric": str(page.photometric),
                    "tile_shape": getattr(page, "tile_shape", None),
                    "is_tiled": page.is_tiled
                })

            return {
                "pages_count": len(tif.pages),
                "pages": pages,
                "is_bigtiff": tif.is_bigtiff,
                "byteorder": tif.byteorder,
                "compression": str(tif.pages[0].compression) if tif.pages else None,
                "interleaving": str(getattr(tif, "series", [None])[0])
            }


# ----------------------------
# MAIN UNIFIED EXTRACTOR
# ----------------------------
class UnifiedGeoTIFFExtractor:

    def __init__(self):
        self.tiff = TIFFExtractor()
        self.image = ImageExtractor()
        self.structure = TIFFStructureExtractor()
        self.exif = ExifToolReader()

    def extract(self, path: str) -> Dict[str, Any]:

        result = {
            "file": {
                "path": path,
                "filename": os.path.basename(path),
                "extension": os.path.splitext(path)[1],
                "size_bytes": os.path.getsize(path)
            },

            # RAW STRUCTURE
            "tiff": self.tiff.extract_structure(path),
            "tiff_structure": self.structure.extract(path),
            "image": self.image.extract(path),

            # EXIF (RAW FULL DICT)
            "exiftool": self.exif.get_metadata(path),

            # GEOSPATIAL PLACEHOLDERS (NO TRANSFORMATIONS)
            "geospatial_extended": {
                "gcps": None,
                "rpcs": None
            },

            "overviews": {}
        }

        return result

    def close(self):
        self.exif.close()


# ----------------------------
# SPARK SCHEMA LAYER (FLAT SAFE)
# ----------------------------
def to_spark_row(data: Dict[str, Any]):
    return json.dumps(data)


# ----------------------------
# PIPELINE ENTRYPOINT
# ----------------------------
def run_spark_ingestion(file_path: str):

    spark = SparkSession.builder.appName("GeoTIFFExtractor").getOrCreate()

    extractor = UnifiedGeoTIFFExtractor()

    try:
        data = extractor.extract(file_path)

        rdd = spark.sparkContext.parallelize([to_spark_row(data)])

        df = spark.read.json(rdd)

        return df

    finally:
        extractor.close()


# ----------------------------
# CLI
# ----------------------------
if __name__ == "__main__":
    import sys

    path = sys.argv[1]

    df = run_spark_ingestion(path)

    df.show(truncate=False)
    df.printSchema()
