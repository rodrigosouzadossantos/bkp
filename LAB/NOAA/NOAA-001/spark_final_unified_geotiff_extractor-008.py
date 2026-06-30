import os
import hashlib
import rasterio
import numpy as np
from pyspark.sql import SparkSession
from pyspark.sql.types import *


# =========================================================
# STRICT ICEBERG SCHEMA (NO INFERENCE EVER)
# =========================================================

ICEBERG_SCHEMA = StructType([

    StructField("file", StructType([
        StructField("path", StringType(), False),
        StructField("filename", StringType(), False),
        StructField("extension", StringType(), True),
        StructField("size_bytes", LongType(), True),
        StructField("checksum_md5", StringType(), True),
    ])),

    StructField("raster", StructType([
        StructField("driver", StringType(), True),
        StructField("width", IntegerType(), True),
        StructField("height", IntegerType(), True),
        StructField("bands_count", IntegerType(), True),
        StructField("dtypes", ArrayType(StringType()), True),
        StructField("indexes", ArrayType(IntegerType()), True),
        StructField("nodata", DoubleType(), True),
        StructField("crs", StringType(), True),
        StructField("crs_wkt", StringType(), True),
        StructField("epsg", IntegerType(), True),
        StructField("transform", ArrayType(DoubleType()), True),
        StructField("res", ArrayType(DoubleType()), True),
        StructField("bounds", ArrayType(DoubleType()), True),
        StructField("metadata", MapType(StringType(), StringType()), True),
    ])),

    StructField("tiff_structure", StructType([
        StructField("compression", StringType(), True),
        StructField("block_shapes", ArrayType(ArrayType(IntegerType())), True),
        StructField("tiles", BooleanType(), True),
        StructField("overviews", MapType(StringType(), ArrayType(IntegerType())), True),
    ])),

    StructField("geotiff", StructType([
        StructField("gcps", MapType(StringType(), StringType()), True),
        StructField("rpc", MapType(StringType(), StringType()), True),
    ])),

    StructField("spatial", StructType([
        StructField("bbox", ArrayType(DoubleType()), True),
        StructField("center", ArrayType(DoubleType()), True),
    ])),

    StructField("gdal", StructType([
        StructField("default", MapType(StringType(), StringType()), True),
        StructField("image_structure", MapType(StringType(), StringType()), True),
        StructField("rpc", MapType(StringType(), StringType()), True),
        StructField("exif", MapType(StringType(), StringType()), True),
        StructField("gdal", MapType(StringType(), StringType()), True),
    ])),

    StructField("quality", StructType([
        StructField("band_stats", MapType(StringType(),
            StructType([
                StructField("min", DoubleType(), True),
                StructField("max", DoubleType(), True),
                StructField("mean", DoubleType(), True),
                StructField("std", DoubleType(), True),
            ])
        ), True)
    ])),
])


# =========================================================
# SAFE HELPERS (CRITICAL FIX)
# =========================================================

def md5_file(path):
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def safe_map(d):
    """
    FORCE Spark-safe Map[String, String]
    """
    if not d:
        return {}
    return {str(k): str(v) for k, v in d.items()}


def safe_list(x):
    return list(x) if x is not None else []


def crs_to_epsg(crs):
    try:
        return int(crs.to_epsg()) if crs else None
    except:
        return None


# =========================================================
# GDAL DOMAINS (FIXED)
# =========================================================

def gdal_domains(src):
    try:
        return {
            "default": safe_map(src.tags()),
            "image_structure": safe_map(src.tags(ns="IMAGE_STRUCTURE")),
            "rpc": safe_map(src.tags(ns="RPC")),
            "exif": safe_map(src.tags(ns="EXIF")),
            "gdal": safe_map(src.tags(ns="GDAL")),
        }
    except:
        return {
            "default": {},
            "image_structure": {},
            "rpc": {},
            "exif": {},
            "gdal": {},
        }


# =========================================================
# OVERVIEWS (FIXED TYPE CONSISTENCY)
# =========================================================

def get_overviews(src):
    try:
        return {
            str(i): safe_list(src.overviews(i))
            for i in range(1, src.count + 1)
            if src.overviews(i)
        }
    except:
        return {}


# =========================================================
# GCP + RPC (SAFE STRING ONLY)
# =========================================================

def get_gcps(src):
    try:
        gcps, crs = src.get_gcps()
        return {
            "crs": str(crs) if crs else None,
            "points": str([
                (g.row, g.col, g.x, g.y, g.z)
                for g in gcps
            ])
        }
    except:
        return {"crs": None, "points": "[]"}


def get_rpc(src):
    try:
        rpc = getattr(src, "rpcs", None)
        return safe_map(rpc) if rpc else {}
    except:
        return {}


# =========================================================
# MAIN EXTRACTOR (CLEAN + SAFE)
# =========================================================

def extract_tiff(path):

    with rasterio.open(path) as src:

        arr = src.read()

        band_stats = {
            f"band_{i+1}": {
                "min": float(np.nanmin(arr[i])),
                "max": float(np.nanmax(arr[i])),
                "mean": float(np.nanmean(arr[i])),
                "std": float(np.nanstd(arr[i])),
            }
            for i in range(src.count)
        }

        minx, miny, maxx, maxy = src.bounds

        return {
            "file": {
                "path": path,
                "filename": os.path.basename(path),
                "extension": os.path.splitext(path)[1],
                "size_bytes": os.path.getsize(path),
                "checksum_md5": md5_file(path),
            },

            "raster": {
                "driver": src.driver,
                "width": src.width,
                "height": src.height,
                "bands_count": src.count,
                "dtypes": list(src.dtypes),
                "indexes": list(range(1, src.count + 1)),
                "nodata": src.nodata,
                "crs": str(src.crs),
                "crs_wkt": src.crs.to_wkt() if src.crs else None,
                "epsg": crs_to_epsg(src.crs),
                "transform": list(src.transform),
                "res": list(src.res),
                "bounds": [minx, miny, maxx, maxy],
                "metadata": safe_map(src.tags()),
            },

            "tiff_structure": {
                "compression": str(src.compression) if src.compression else None,
                "block_shapes": list(src.block_shapes),
                "tiles": src.is_tiled,
                "overviews": get_overviews(src),
            },

            "geotiff": {
                "gcps": get_gcps(src),
                "rpc": get_rpc(src),
            },

            "spatial": {
                "bbox": [minx, miny, maxx, maxy],
                "center": [(minx + maxx) / 2, (miny + maxy) / 2],
            },

            "gdal": gdal_domains(src),

            "quality": {
                "band_stats": band_stats,
            },
        }


# =========================================================
# SPARK EXECUTION (NO INFERENCE)
# =========================================================

def run_spark(path):

    spark = SparkSession.builder \
        .appName("GeoTIFF-Iceberg-Final") \
        .getOrCreate()

    data = extract_tiff(path)

    df = spark.createDataFrame([data], schema=ICEBERG_SCHEMA)

    return df


# =========================================================
# ENTRYPOINT
# =========================================================

if __name__ == "__main__":
    import sys

    path = sys.argv[1]
    df = run_spark(path)

    df.printSchema()
    df.show(truncate=False)
