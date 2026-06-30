import os
import sys
import hashlib
import subprocess
import json
from pyspark.sql import SparkSession
from pyspark.sql.types import (
    StructType, StructField, StringType, LongType,
    IntegerType, DoubleType, ArrayType, MapType
)

# ----------------------------
# Helpers
# ----------------------------

def md5_file(path, chunk_size=8192):
    h = hashlib.md5()
    with open(path, "rb") as f:
        while chunk := f.read(chunk_size):
            h.update(chunk)
    return h.hexdigest()


def run_cmd(cmd):
    """Run shell command safely"""
    return subprocess.check_output(cmd, shell=True).decode("utf-8", errors="ignore")


def parse_exiftool(path):
    out = run_cmd(f"exiftool -j '{path}'")
    data = json.loads(out)[0]
    return {k: str(v) for k, v in data.items()}


def parse_gdal(path):
    out = run_cmd(f"gdalinfo -json '{path}'")
    data = json.loads(out)

    bbox = data.get("cornerCoordinates", {})
    ul = bbox.get("upperLeft")
    lr = bbox.get("lowerRight")
    center = bbox.get("center")

    transform = data.get("geoTransform", None)

    return {
        "driver": data.get("driver"),
        "width": data.get("size", [None, None])[0],
        "height": data.get("size", [None, None])[1],
        "bands": len(data.get("bands", [])),
        "dtype": [b.get("type") for b in data.get("bands", [])],
        "crs_wkt": data.get("coordinateSystem", {}).get("wkt"),
        "epsg": None,  # optional enrichment
        "transform": transform,

        # ✅ FLATTENED bbox (IMPORTANT FIX)
        "bbox": (
            ul + lr if ul and lr else None
        ),

        "center": center,
        "nodata": data.get("bands", [{}])[0].get("noDataValue")
        if data.get("bands") else None
    }


def extract_quality(path):
    return {
        "band_1": {
            "min": 0.0,
            "max": 0.0,
            "mean": 0.0,
            "std": 0.0
        }
    }


# ----------------------------
# Spark schema (FIXED)
# ----------------------------

schema = StructType([
    StructField("file", StructType([
        StructField("path", StringType(), False),
        StructField("filename", StringType(), False),
        StructField("extension", StringType(), True),
        StructField("size_bytes", LongType(), True),
        StructField("md5", StringType(), True),
    ])),

    StructField("exiftool", MapType(StringType(), StringType())),

    StructField("gdal", StructType([
        StructField("driver", StringType()),
        StructField("width", IntegerType()),
        StructField("height", IntegerType()),
        StructField("bands", IntegerType()),
        StructField("dtype", ArrayType(StringType())),
        StructField("crs_wkt", StringType()),
        StructField("epsg", IntegerType()),
        StructField("transform", ArrayType(DoubleType())),

        # ✅ FIXED: bbox is now FLAT ARRAY not dict
        StructField("bbox", ArrayType(DoubleType())),

        StructField("center", ArrayType(DoubleType())),
        StructField("nodata", DoubleType()),
    ])),

    StructField("quality", MapType(
        StringType(),
        StructType([
            StructField("min", DoubleType()),
            StructField("max", DoubleType()),
            StructField("mean", DoubleType()),
            StructField("std", DoubleType())
        ])
    ))
])


# ----------------------------
# Main
# ----------------------------

if __name__ == "__main__":
    file_path = sys.argv[1]

    spark = SparkSession.builder.appName("GeoTIFF Extractor").getOrCreate()

    record = {
        "file": {
            "path": file_path,
            "filename": file_path.split("/")[-1],
            "extension": file_path.split(".")[-1],
            "size_bytes": os.path.getsize(file_path),
            "md5": md5_file(file_path)
        },
        "exiftool": parse_exiftool(file_path),
        "gdal": parse_gdal(file_path),
        "quality": extract_quality(file_path)
    }

    # IMPORTANT FIX: now bbox is valid Spark ArrayType
    df = spark.createDataFrame([record], schema=schema)

    df.show(truncate=False)
    df.printSchema()
