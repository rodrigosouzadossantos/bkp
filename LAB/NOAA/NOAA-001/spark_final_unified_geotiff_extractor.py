import os
import json
import subprocess
from datetime import datetime

import rasterio
from rasterio.io import MemoryFile
from PIL import Image

from pyspark.sql import SparkSession
from pyspark.sql.types import *


# ==============================
# 1. SPARK SCHEMA (CANONICAL)
# ==============================

file_schema = StructType([
    StructField("path", StringType(), False),
    StructField("filename", StringType(), False),
    StructField("extension", StringType(), True),
    StructField("size_bytes", LongType(), True),
])

raster_schema = StructType([
    StructField("driver", StringType(), True),
    StructField("width", IntegerType(), True),
    StructField("height", IntegerType(), True),
    StructField("bands_count", IntegerType(), True),
    StructField("dtypes", ArrayType(StringType()), True),
    StructField("indexes", ArrayType(IntegerType()), True),
    StructField("nodata", DoubleType(), True),
    StructField("crs", StringType(), True),
    StructField("transform", ArrayType(DoubleType()), True),
    StructField("tags", MapType(StringType(), StringType()), True),
    StructField("band_tags", MapType(StringType(), MapType(StringType(), StringType())), True),
])

tiff_band_schema = StructType([
    StructField("band_index", IntegerType(), True),
    StructField("width", IntegerType(), True),
    StructField("height", IntegerType(), True),
    StructField("dtype", StringType(), True),
])

tiff_schema = StructType([
    StructField("byte_order", StringType(), True),
    StructField("bigtiff", BooleanType(), True),

    # FIX: bands, not pages
    StructField("bands_count", IntegerType(), True),
    StructField("bands", ArrayType(tiff_band_schema), True),

    StructField("compression", StringType(), True),
    StructField("interleaving", StringType(), True),
    StructField("block_shapes", ArrayType(ArrayType(IntegerType())), True),
])

geotiff_schema = StructType([
    StructField("pixel_scale", ArrayType(DoubleType()), True),
    StructField("tie_points", ArrayType(DoubleType()), True),
    StructField("ascii_params", StringType(), True),
    StructField("double_params", ArrayType(DoubleType()), True),

    StructField("keys", ArrayType(
        StructType([
            StructField("id", IntegerType(), True),
            StructField("name", StringType(), True),
            StructField("location", IntegerType(), True),
            StructField("count", IntegerType(), True),
            StructField("value", StringType(), True),
        ])
    ), True),
])

image_schema = StructType([
    StructField("format", StringType(), True),
    StructField("mode", StringType(), True),
    StructField("width", IntegerType(), True),
    StructField("height", IntegerType(), True),
    StructField("bands", ArrayType(StringType()), True),
])

exif_schema = StructType([
    StructField("raw", MapType(StringType(), StringType()), True)
])

gdal_schema = StructType([
    StructField("driver", StringType(), True),
    StructField("projection", StringType(), True),
    StructField("geotransform", ArrayType(DoubleType()), True),
    StructField("metadata", MapType(StringType(), MapType(StringType(), StringType())), True),
])

root_schema = StructType([
    StructField("file", file_schema, False),
    StructField("raster", raster_schema, False),
    StructField("tiff_structure", tiff_schema, False),
    StructField("geotiff", geotiff_schema, True),
    StructField("image", image_schema, True),
    StructField("exiftool", exif_schema, True),
    StructField("gdal", gdal_schema, True),
])


# ==============================
# 2. EXIFTOOL (RAW EXTRACTION)
# ==============================

def run_exiftool(path):
    cmd = ["exiftool", "-j", "-struct", path]
    out = subprocess.check_output(cmd)
    return json.loads(out)[0]


# ==============================
# 3. TIFF EXTRACTION (RASTERIO)
# ==============================

def extract_tiff(path):
    with rasterio.open(path) as src:

        bands = []
        for i in range(src.count):
            bands.append({
                "band_index": i + 1,
                "width": src.width,
                "height": src.height,
                "dtype": str(src.dtypes[i])
            })

        return {
            "byte_order": src.profile.get("byteorder", "unknown"),
            "bigtiff": src.profile.get("bigtiff", False),
            "bands_count": src.count,
            "bands": bands,
            "compression": str(src.profile.get("compress", "none")),
            "interleaving": str(src.profile.get("interleave", "unknown")),
            "block_shapes": [list(b) for b in src.block_shapes]
        }


# ==============================
# 4. GEOTIFF RAW TAGS
# ==============================

def extract_geotiff_tags(src):
    tags = []

    for k, v in src.tags().items():
        tags.append({
            "id": None,
            "name": k,
            "location": None,
            "count": None,
            "value": str(v)
        })

    return {
        "pixel_scale": list(src.tags(ns="TIFFTAG_MODELPIXELSCALETAG").values()) if src.tags(ns="TIFFTAG_MODELPIXELSCALETAG") else None,
        "tie_points": list(src.tags(ns="TIFFTAG_MODELTIEPOINTTAG").values()) if src.tags(ns="TIFFTAG_MODELTIEPOINTTAG") else None,
        "ascii_params": str(src.tags(ns="TIFFTAG_GEOASCIIPARAMSTAG")) if src.tags(ns="TIFFTAG_GEOASCIIPARAMSTAG") else None,
        "double_params": [],
        "keys": tags
    }


# ==============================
# 5. GDAL (RAW ONLY, NO DERIVATION)
# ==============================

def extract_gdal(path):
    try:
        import rasterio
        with rasterio.open(path) as src:
            return {
                "driver": src.driver,
                "projection": src.crs.to_wkt() if src.crs else None,
                "geotransform": list(src.transform) if src.transform else None,
                "metadata": {
                    k: dict(v) for k, v in src.meta.items() if isinstance(v, dict)
                }
            }
    except Exception:
        return {
            "driver": None,
            "projection": None,
            "geotransform": None,
            "metadata": {}
        }


# ==============================
# 6. PILLOW SNAPSHOT
# ==============================

def extract_pillow(path):
    img = Image.open(path)
    return {
        "format": img.format,
        "mode": img.mode,
        "width": img.width,
        "height": img.height,
        "bands": list(img.getbands())
    }


# ==============================
# 7. MAIN EXTRACTOR
# ==============================

def extract_geotiff(path):

    stat = os.stat(path)

    with rasterio.open(path) as src:

        exif = run_exiftool(path)

        return {
            "file": {
                "path": path,
                "filename": os.path.basename(path),
                "extension": os.path.splitext(path)[1],
                "size_bytes": stat.st_size
            },

            "raster": {
                "driver": src.driver,
                "width": src.width,
                "height": src.height,
                "bands_count": src.count,
                "dtypes": list(src.dtypes),
                "indexes": list(range(1, src.count + 1)),
                "nodata": src.nodata,
                "crs": str(src.crs) if src.crs else None,
                "transform": list(src.transform),
                "tags": dict(src.tags()),
                "band_tags": {
                    str(i): src.tags(i)
                    for i in range(1, src.count + 1)
                }
            },

            "tiff_structure": extract_tiff(path),

            "geotiff": extract_geotiff_tags(src),

            "image": extract_pillow(path),

            "exiftool": {
                "raw": exif
            },

            "gdal": extract_gdal(path)
        }


# ==============================
# 8. SPARK CONVERTER
# ==============================

def to_spark_df(spark, data_list):
    return spark.createDataFrame(data_list, schema=root_schema)


# ==============================
# 9. ENTRY POINT
# ==============================

def run(paths):
    spark = SparkSession.builder.appName("geotiff-extractor").getOrCreate()

    results = []
    for p in paths:
        results.append(extract_geotiff(p))

    df = to_spark_df(spark, results)
    return df


# ==============================
# CLI TEST
# ==============================

if __name__ == "__main__":
    import sys
    df = run([sys.argv[1]])
    df.printSchema()
    df.show(truncate=False,vertical=True)
