import os
import numpy as np

import rasterio
from PIL import Image
import tifffile
import exiftool

from pyspark.sql import SparkSession
from pyspark.sql.types import (
    StructType, StructField, StringType, IntegerType,
    ArrayType, DoubleType, LongType, MapType
)


# -----------------------------
# SAFE NORMALIZATION (CRITICAL)
# -----------------------------
def normalize(obj):
    if obj is None:
        return None

    if hasattr(obj, "to_string"):  # CRS
        return obj.to_string()

    if isinstance(obj, (list, tuple)):
        return list(obj)

    if isinstance(obj, np.ndarray):
        return obj.tolist()

    if isinstance(obj, (np.integer, np.floating)):
        return obj.item()

    return obj


# -----------------------------
# EXIF TOOL (NO subprocess)
# -----------------------------
class ExifReader:
    def __init__(self):
        self.et = exiftool.ExifToolHelper()

    def read(self, path):
        try:
            data = self.et.get_metadata(path)
            return data[0] if data else {}
        except Exception:
            return {}


# -----------------------------
# TIFF EXTRACTOR
# -----------------------------
class GeoTIFFExtractor:

    def extract(self, path):

        with rasterio.open(path) as src:

            image = Image.open(path)

            # SAFE primitives only
            return {
                "file_path": path,
                "filename": os.path.basename(path),
                "size_bytes": os.path.getsize(path),

                # raster core
                "width": src.width,
                "height": src.height,
                "bands": src.count,
                "dtype": str(src.dtypes[0]),

                # geospatial (NORMALIZED)
                "crs": normalize(src.crs),
                "transform": list(src.transform),
                "bounds": list(src.bounds),
                "res": list(src.res),
                "nodata": float(src.nodata) if src.nodata else None,

                # image
                "format": image.format,
                "mode": image.mode,
                "img_size": list(image.size),

                # metadata
                "tags": dict(src.tags())
            }


# -----------------------------
# SPARK SCHEMA (STRICT)
# -----------------------------
def get_schema():

    return StructType([
        StructField("file_path", StringType(), True),
        StructField("filename", StringType(), True),
        StructField("size_bytes", LongType(), True),

        StructField("width", IntegerType(), True),
        StructField("height", IntegerType(), True),
        StructField("bands", IntegerType(), True),
        StructField("dtype", StringType(), True),

        StructField("crs", StringType(), True),
        StructField("transform", ArrayType(DoubleType()), True),
        StructField("bounds", ArrayType(DoubleType()), True),
        StructField("res", ArrayType(DoubleType()), True),
        StructField("nodata", DoubleType(), True),

        StructField("format", StringType(), True),
        StructField("mode", StringType(), True),
        StructField("img_size", ArrayType(IntegerType()), True),

        StructField("tags", MapType(StringType(), StringType()), True),
    ])


# -----------------------------
# SPARK INGESTION ENGINE
# -----------------------------
def ingest_spark(files):

    spark = SparkSession.builder.appName("GeoTIFF-Ingestor").getOrCreate()

    extractor = GeoTIFFExtractor()

    # mapPartitions-ready design (scalable)
    def generator(paths):
        for p in paths:
            yield extractor.extract(p)

    rdd = spark.sparkContext.parallelize(files, numSlices=4).mapPartitions(generator)

    df = spark.createDataFrame(rdd, schema=get_schema())

    return df


# -----------------------------
# CLI
# -----------------------------
if __name__ == "__main__":
    import sys

    file_path = sys.argv[1]

    df = ingest_spark([file_path])

    df.show(truncate=False)
    df.printSchema()
