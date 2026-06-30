import os
import hashlib
import numpy as np
import rasterio
from rasterio.enums import Resampling
from pyspark.sql import SparkSession
from pyspark.sql.types import *


# =========================================================
# ICEBERG SCHEMA (COMPLETE + TYPE SAFE)
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
        StructField("is_tiled", BooleanType(), True),
        StructField("metadata", MapType(StringType(), StringType()), True),
    ])),

    StructField("tiff_structure", StructType([
        StructField("compression", StringType(), True),
        StructField("block_shapes", ArrayType(ArrayType(IntegerType())), True),
        StructField("tiles", BooleanType(), True),
        StructField("overviews", MapType(StringType(), ArrayType(IntegerType())), True),
    ])),

    StructField("geotiff", StructType([
        StructField("pixel_scale", ArrayType(DoubleType()), True),
        StructField("tie_points", ArrayType(DoubleType()), True),
        StructField("geo_keys", MapType(StringType(), StringType()), True),
    ])),

    StructField("gdal", StructType([
        StructField("default", MapType(StringType(), StringType()), True),
        StructField("image_structure", MapType(StringType(), StringType()), True),
        StructField("rpc", MapType(StringType(), StringType()), True),
        StructField("exif", MapType(StringType(), StringType()), True),
        StructField("gdal", MapType(StringType(), StringType()), True),
    ])),

    StructField("spatial", StructType([
        StructField("bbox", ArrayType(DoubleType()), True),
        StructField("center", ArrayType(DoubleType()), True),
    ])),

    StructField("rpc", MapType(StringType(), StringType()), True),

    StructField("gcps", StructType([
        StructField("count", IntegerType(), True),
        StructField("points", ArrayType(MapType(StringType(), StringType())), True),
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
# HELPERS
# =========================================================

def md5_file(path):
    h = hashlib.md5()
    with open(path, "rb") as f:
        for c in iter(lambda: f.read(8192), b""):
            h.update(c)
    return h.hexdigest()


def safe(v):
    return str(v) if v is not None else None


def epsg_from_crs(crs):
    try:
        return int(crs.to_epsg()) if crs else None
    except:
        return None


def flatten_tags(tags):
    return {str(k): str(v) for k, v in (tags or {}).items()}


# =========================================================
# OVERVIEW EXTRACTION (FIXED)
# =========================================================

def extract_overviews(src):
    try:
        out = {}
        for i in range(1, src.count + 1):
            ovs = src.overviews(i)
            if ovs:
                out[str(i)] = list(ovs)
        return out
    except:
        return {}


# =========================================================
# GDAL + TIFF TAGS (FULL DOMAINS)
# =========================================================

def extract_gdal_domains(src):
    return {
        "default": flatten_tags(src.tags()),
        "image_structure": flatten_tags(src.tags(ns="IMAGE_STRUCTURE")),
        "rpc": flatten_tags(src.tags(ns="RPC")),
        "exif": flatten_tags(src.tags(ns="EXIF")),
        "gdal": flatten_tags(src.tags(ns="GDAL")),
    }


# =========================================================
# GEOTIFF IFD / KEYS
# =========================================================

def extract_geotiff(src):
    return {
        "pixel_scale": list(src.tags().get("ModelPixelScaleTag") or []),
        "tie_points": list(src.tags().get("ModelTiepointTag") or []),
        "geo_keys": flatten_tags(src.tags(ns="GeoKeyDirectoryTag")),
    }


# =========================================================
# GCP + RPC ENRICHMENT
# =========================================================

def extract_gcps(src):
    try:
        gcps, crs = src.get_gcps()
        return {
            "count": len(gcps),
            "points": [
                {
                    "row": str(g.row),
                    "col": str(g.col),
                    "x": str(g.x),
                    "y": str(g.y),
                    "z": str(g.z),
                }
                for g in gcps
            ]
        }
    except:
        return {"count": 0, "points": []}


def extract_rpc(src):
    try:
        return flatten_tags(src.rpcs)
    except:
        return {}


# =========================================================
# MAIN EXTRACTOR (VECTORIZED + SAFE)
# =========================================================

def extract_tiff(path):

    with rasterio.open(path) as src:

        arr = src.read()  # vectorized load once

        band_stats = {
            f"band_{i+1}": {
                "min": float(np.nanmin(arr[i])),
                "max": float(np.nanmax(arr[i])),
                "mean": float(np.nanmean(arr[i])),
                "std": float(np.nanstd(arr[i])),
            }
            for i in range(src.count)
        }

        bounds = src.bounds

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
                "crs": safe(src.crs),
                "crs_wkt": src.crs.to_wkt() if src.crs else None,
                "epsg": epsg_from_crs(src.crs),
                "transform": list(src.transform),
                "res": list(src.res),
                "bounds": [bounds.left, bounds.bottom, bounds.right, bounds.top],
                "is_tiled": src.is_tiled if hasattr(src, "is_tiled") else False,
                "metadata": flatten_tags(src.tags()),
            },

            "tiff_structure": {
                "compression": str(src.compression) if src.compression else None,
                "block_shapes": list(src.block_shapes),
                "tiles": src.is_tiled if hasattr(src, "is_tiled") else False,
                "overviews": extract_overviews(src),
            },

            "geotiff": extract_geotiff(src),

            "gdal": extract_gdal_domains(src),

            "spatial": {
                "bbox": [bounds.left, bounds.bottom, bounds.right, bounds.top],
                "center": [
                    (bounds.left + bounds.right) / 2,
                    (bounds.top + bounds.bottom) / 2
                ]
            },

            "rpc": extract_rpc(src),

            "gcps": extract_gcps(src),

            "quality": {
                "band_stats": band_stats
            }
        }


# =========================================================
# SPARK EXECUTION (ICEBERG SAFE)
# =========================================================

def run_spark(path):

    spark = SparkSession.builder \
        .appName("GeoTIFF-Iceberg") \
        .getOrCreate()

    data = extract_tiff(path)

    df = spark.createDataFrame([data], schema=ICEBERG_SCHEMA)

    return df


# =========================================================
# ENTRY
# =========================================================

if __name__ == "__main__":
    import sys

    path = sys.argv[1]
    df = run_spark(path)

    df.printSchema()
    df.show(truncate=False,vertical=True)
