import os
import hashlib
import rasterio
import numpy as np
from pyspark.sql import SparkSession
from pyspark.sql.types import *


# =========================================================
# ICEBERG / SPARK FINAL SCHEMA (STRICT + FLAT SAFE TYPES)
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
        StructField("interleave", StringType(), True),
        StructField("is_georeferenced", BooleanType(), True),
        StructField("metadata", MapType(StringType(), StringType()), True),
    ])),

    StructField("tiff_structure", StructType([
        StructField("byte_order", StringType(), True),
        StructField("bigtiff", BooleanType(), True),
        StructField("compression", StringType(), True),
        StructField("block_shapes", ArrayType(ArrayType(IntegerType())), True),
        StructField("tiles", BooleanType(), True),
    ])),

    StructField("geotiff", StructType([
        StructField("pixel_scale", StringType(), True),
        StructField("tie_points", StringType(), True),
        StructField("ascii_params", StringType(), True),
        StructField("double_params", StringType(), True),
    ])),

    StructField("spatial", StructType([
        StructField("bbox", ArrayType(DoubleType()), True),
        StructField("center", ArrayType(DoubleType()), True),
    ])),

    StructField("image", StructType([
        StructField("format", StringType(), True),
        StructField("mode", StringType(), True),
        StructField("width", IntegerType(), True),
        StructField("height", IntegerType(), True),
        StructField("bands", ArrayType(StringType()), True),
    ])),

    StructField("exif", StructType([
        StructField("raw", MapType(StringType(), StringType()), True),
    ])),

    StructField("gdal", StructType([
        StructField("driver", StringType(), True),
        StructField("projection", StringType(), True),
        StructField("geotransform", ArrayType(DoubleType()), True),
        StructField("metadata", MapType(StringType(), StringType()), True),
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
# SAFE HELPERS
# =========================================================

def md5_file(path):
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def safe_str(x):
    return str(x) if x is not None else None


def crs_to_epsg(crs):
    try:
        return int(crs.to_epsg()) if crs else None
    except:
        return None


# =========================================================
# GEO-TIFF TAG EXTRACTION (FIXED + COMPLETE)
# =========================================================

def extract_geotiff_tags(src):
    return {
        "pixel_scale": str(src.tags().get("ModelPixelScaleTag")),
        "tie_points": str(src.tags().get("ModelTiepointTag")),
        "ascii_params": str(src.tags().get("GeoAsciiParamsTag")),
        "double_params": None,
    }


# =========================================================
# MAIN EXTRACTOR (FIXED)
# =========================================================

def extract_tiff(path):

    with rasterio.open(path) as src:

        bounds = src.bounds
        minx, miny, maxx, maxy = bounds

        band_stats = {
            f"band_{i+1}": {
                "min": float(np.nanmin(src.read(i + 1))),
                "max": float(np.nanmax(src.read(i + 1))),
                "mean": float(np.nanmean(src.read(i + 1))),
                "std": float(np.nanstd(src.read(i + 1))),
            }
            for i in range(src.count)
        }

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
                "crs": safe_str(src.crs),
                "crs_wkt": src.crs.to_wkt() if src.crs else None,
                "epsg": crs_to_epsg(src.crs),
                "transform": list(src.transform),
                "res": list(src.res),
                "bounds": [minx, miny, maxx, maxy],
                "interleave": src.interleaving if hasattr(src, "interleaving") else None,
                "is_georeferenced": src.crs is not None,
                "metadata": dict(src.tags()),
            },

            "tiff_structure": {
                "byte_order": None,
                "bigtiff": src.profile.get("bigtiff", False),
                "compression": str(src.compression) if src.compression else None,
                "block_shapes": list(src.block_shapes),
                "tiles": src.is_tiled if hasattr(src, "is_tiled") else None,
            },

            "geotiff": extract_geotiff_tags(src),

            "spatial": {
                "bbox": [minx, miny, maxx, maxy],
                "center": [
                    (minx + maxx) / 2,
                    (miny + maxy) / 2
                ]
            },

            "image": {
                "format": "TIFF",
                "mode": "RGB" if src.count == 3 else "UNKNOWN",
                "width": src.width,
                "height": src.height,
                "bands": [f"B{i}" for i in range(1, src.count + 1)]
            },

            "exif": {
                "raw": dict(src.tags()),
            },

            "gdal": {
                "driver": src.driver,
                "projection": safe_str(src.crs),
                "geotransform": list(src.transform),
                "metadata": dict(src.tags()),
            },

            "quality": {
                "band_stats": band_stats
            }
        }


# =========================================================
# SPARK EXECUTION (ICEBERG SAFE)
# =========================================================

def run_spark(path):

    spark = SparkSession.builder \
        .appName("GeoTIFF-Iceberg-Extractor") \
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
