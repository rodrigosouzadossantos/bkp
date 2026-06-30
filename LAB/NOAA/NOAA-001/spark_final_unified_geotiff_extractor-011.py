import os
import json
import hashlib
import subprocess
import numpy as np
from osgeo import gdal, osr
from pyspark.sql import SparkSession
from pyspark.sql.types import *


# =========================================================
# EXIFTOOL (FULL TIFF TRUTH LAYER)
# =========================================================

def run_exiftool(path):
    result = subprocess.run(
        ["exiftool", "-json", "-n", path],
        capture_output=True,
        text=True,
        check=True
    )
    return json.loads(result.stdout)[0]


# =========================================================
# GDAL SPATIAL LAYER
# =========================================================

def extract_epsg(srs):
    if not srs:
        return None
    try:
        srs.AutoIdentifyEPSG()
        code = srs.GetAuthorityCode(None)
        return int(code) if code else None
    except:
        return None


def gdal_extract(path):
    ds = gdal.Open(path)
    gt = ds.GetGeoTransform()
    srs = ds.GetSpatialRef()

    x_min = gt[0]
    y_max = gt[3]
    x_max = x_min + gt[1] * ds.RasterXSize
    y_min = y_max + gt[5] * ds.RasterYSize

    return {
        "driver": ds.GetDriver().ShortName,
        "width": ds.RasterXSize,
        "height": ds.RasterYSize,
        "bands": ds.RasterCount,
        "dtype": [gdal.GetDataTypeName(ds.GetRasterBand(i).DataType)
                  for i in range(1, ds.RasterCount + 1)],
        "crs_wkt": srs.ExportToWkt() if srs else None,
        "epsg": extract_epsg(srs),
        "transform": list(gt),
        "bbox": [x_min, y_min, x_max, y_max],
        "center": [(x_min + x_max)/2, (y_min + y_max)/2],
        "nodata": ds.GetRasterBand(1).GetNoDataValue()
    }


# =========================================================
# FILE METADATA
# =========================================================

def file_meta(path):
    h = hashlib.md5()
    with open(path, "rb") as f:
        for c in iter(lambda: f.read(8192), b""):
            h.update(c)

    return {
        "path": path,
        "filename": os.path.basename(path),
        "extension": os.path.splitext(path)[1],
        "size_bytes": os.path.getsize(path),
        "md5": h.hexdigest()
    }


# =========================================================
# NORMALIZER (EXIFTOOL → FLAT MAP)
# =========================================================

def flatten_exif(exif_dict):
    out = {}

    def walk(prefix, obj):
        if isinstance(obj, dict):
            for k, v in obj.items():
                walk(f"{prefix}{k}.", v)
        elif isinstance(obj, list):
            out[prefix[:-1]] = obj
        else:
            out[prefix[:-1]] = obj

    walk("", exif_dict)
    return out


# =========================================================
# QUALITY (OPTIONAL NUMERIC STATS)
# =========================================================

def raster_stats(path):
    ds = gdal.Open(path)
    arr_stats = {}

    for i in range(1, ds.RasterCount + 1):
        band = ds.GetRasterBand(i)
        arr = band.ReadAsArray()

        arr_stats[f"band_{i}"] = {
            "min": float(np.nanmin(arr)),
            "max": float(np.nanmax(arr)),
            "mean": float(np.nanmean(arr)),
            "std": float(np.nanstd(arr)),
        }

    return arr_stats


# =========================================================
# FINAL MERGE LAYER
# =========================================================

def extract_tiff(path):

    exif = run_exiftool(path)
    gdal_data = gdal_extract(path)

    return {
        "file": file_meta(path),

        "exiftool": flatten_exif(exif),   # FULL LOSSLESS METADATA

        "gdal": gdal_data,                # SPATIAL TRUTH

        "quality": {
            "band_stats": raster_stats(path)
        }
    }


# =========================================================
# SPARK SCHEMA (GENERIC + SAFE FOR ICEBERG)
# =========================================================

ICEBERG_SCHEMA = StructType([

    StructField("file", MapType(StringType(), StringType()), True),
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
        StructField("bbox", ArrayType(DoubleType()), True),
        StructField("center", ArrayType(DoubleType()), True),
        StructField("nodata", DoubleType(), True),
    ])),

    StructField("quality", MapType(StringType(),
        StructType([
            StructField("min", DoubleType()),
            StructField("max", DoubleType()),
            StructField("mean", DoubleType()),
            StructField("std", DoubleType()),
        ])
    ), True),
])


# =========================================================
# SPARK ENTRY
# =========================================================

def run_spark(path):

    spark = SparkSession.builder \
        .appName("Hybrid-ExifTool-GDAL-Iceberg") \
        .getOrCreate()

    data = extract_tiff(path)

    df = spark.createDataFrame([data], schema=ICEBERG_SCHEMA)

    return df


# =========================================================
# MAIN
# =========================================================

if __name__ == "__main__":
    import sys

    df = run_spark(sys.argv[1])
    df.printSchema()
    df.show(truncate=False, vertical=True)
