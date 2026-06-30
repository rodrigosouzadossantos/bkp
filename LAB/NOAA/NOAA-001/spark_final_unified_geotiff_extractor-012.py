import os
import hashlib
import subprocess
import json
import numpy as np
import rasterio
import tifffile as tiff
from pyspark.sql import SparkSession
from pyspark.sql.types import *


# =========================================================
# ICEBERG SCHEMA (LOSSLESS, STRUCTURED, TYPE SAFE)
# =========================================================

ICEBERG_SCHEMA = StructType([

    StructField("file", StructType([
        StructField("path", StringType(), False),
        StructField("filename", StringType(), False),
        StructField("extension", StringType(), True),
        StructField("size_bytes", LongType(), True),
        StructField("md5", StringType(), True),
    ])),

    StructField("exiftool", MapType(StringType(), StringType()), True),

    StructField("gdal", StructType([
        StructField("driver", StringType(), True),
        StructField("width", IntegerType(), True),
        StructField("height", IntegerType(), True),
        StructField("bands", IntegerType(), True),
        StructField("dtype", ArrayType(StringType()), True),
        StructField("crs_wkt", StringType(), True),
        StructField("epsg", IntegerType(), True),
        StructField("transform", ArrayType(DoubleType()), True),
        StructField("nodata", DoubleType(), True),

        StructField("bounds", StructType([
            StructField("left", DoubleType(), True),
            StructField("bottom", DoubleType(), True),
            StructField("right", DoubleType(), True),
            StructField("top", DoubleType(), True),
        ])),

        StructField("center", StructType([
            StructField("x", DoubleType(), True),
            StructField("y", DoubleType(), True),
        ]))
    ])),

    StructField("tiff_ifd", StructType([
        StructField("pages", ArrayType(StructType([
            StructField("index", IntegerType(), True),
            StructField("shape", ArrayType(IntegerType()), True),
            StructField("dtype", StringType(), True),

            # FULL TAG MAP (NO STRING LOSS)
            StructField("tags", MapType(StringType(), StringType()), True),
        ])))
    ])),

    StructField("quality", MapType(StringType(),
        StructType([
            StructField("min", DoubleType(), True),
            StructField("max", DoubleType(), True),
            StructField("mean", DoubleType(), True),
            StructField("std", DoubleType(), True),
        ])
    ))
])


# =========================================================
# HELPERS
# =========================================================

def md5_file(path):
    h = hashlib.md5()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(8192), b""):
            h.update(b)
    return h.hexdigest()


def run_exiftool(path):
    cmd = [
        "exiftool", "-G", "-j", "-struct", "-a", "-u", "-U", path
    ]
    raw = subprocess.check_output(cmd)
    return json.loads(raw)[0]


# =========================================================
# GDAL EXTRACTION
# =========================================================

def extract_gdal(src):
    crs = src.crs

    return {
        "driver": src.driver,
        "width": src.width,
        "height": src.height,
        "bands": src.count,
        "dtype": list(src.dtypes),
        "crs_wkt": crs.to_wkt() if crs else None,
        "epsg": crs.to_epsg() if crs and crs.to_epsg() else None,
        "transform": list(src.transform),
        "nodata": src.nodata,

        "bounds": {
            "left": src.bounds.left,
            "bottom": src.bounds.bottom,
            "right": src.bounds.right,
            "top": src.bounds.top
        },

        "center": {
            "x": (src.bounds.left + src.bounds.right) / 2,
            "y": (src.bounds.top + src.bounds.bottom) / 2
        }
    }


# =========================================================
# TIFF IFD EXTRACTION (FULL STRUCTURE)
# =========================================================

def extract_ifd(path):
    with tiff.TiffFile(path) as tf:
        pages = []

        for page in tf.pages:
            tags = {}

            for tag in page.tags.values():
                try:
                    val = tag.value
                    # keep structure, not flattening
                    if isinstance(val, (list, tuple, np.ndarray)):
                        val = [str(x) for x in val]
                    else:
                        val = str(val)
                    tags[tag.name] = val
                except:
                    tags[tag.name] = str(tag.value)

            pages.append({
                "index": page.index,
                "shape": list(page.shape),
                "dtype": str(page.dtype),
                "tags": tags
            })

        return {"pages": pages}


# =========================================================
# QUALITY METRICS
# =========================================================

def quality(src):
    arr = src.read()

    return {
        f"band_{i+1}": {
            "min": float(np.min(arr[i])),
            "max": float(np.max(arr[i])),
            "mean": float(np.mean(arr[i])),
            "std": float(np.std(arr[i]))
        }
        for i in range(src.count)
    }


# =========================================================
# MAIN EXTRACTOR
# =========================================================

def extract(path):

    with rasterio.open(path) as src:

        return {
            "file": {
                "path": path,
                "filename": os.path.basename(path),
                "extension": os.path.splitext(path)[1],
                "size_bytes": os.path.getsize(path),
                "md5": md5_file(path)
            },

            "exiftool": run_exiftool(path),

            "gdal": extract_gdal(src),

            "tiff_ifd": extract_ifd(path),

            "quality": quality(src)
        }


# =========================================================
# SPARK ENTRY (ICEBERG SAFE)
# =========================================================

def run(path):

    spark = SparkSession.builder \
        .appName("GeoTIFF-Iceberg-Full-Fidelity") \
        .getOrCreate()

    data = extract(path)

    df = spark.createDataFrame([data], schema=ICEBERG_SCHEMA)

    return df


# =========================================================
# ENTRY
# =========================================================

if __name__ == "__main__":
    import sys

    df = run(sys.argv[1])

    df.printSchema()
    df.show(truncate=False, vertical=True)
