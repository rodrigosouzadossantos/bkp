import os
import hashlib
import numpy as np
from osgeo import gdal, osr
from pyspark.sql import SparkSession
from pyspark.sql.types import *


# =========================================================
# SAFETY: ENABLE GDAL EXCEPTIONS
# =========================================================
gdal.UseExceptions()


# =========================================================
# SCHEMA (CLEAN + GDAL ACCURATE)
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
        StructField("crs_wkt", StringType(), True),
        StructField("epsg", IntegerType(), True),
        StructField("transform", ArrayType(DoubleType()), True),
        StructField("nodata", DoubleType(), True),
        StructField("metadata", MapType(StringType(), StringType()), True),
    ])),

    StructField("tiff_ifd", StructType([
        StructField("compression", StringType(), True),
        StructField("photometric", StringType(), True),
        StructField("planar_config", StringType(), True),
        StructField("rows_per_strip", StringType(), True),
        StructField("tile_width", StringType(), True),
        StructField("tile_length", StringType(), True),
        StructField("predictor", StringType(), True),
    ])),

    StructField("geotiff", StructType([
        StructField("model_pixel_scale", ArrayType(DoubleType()), True),
        StructField("model_tiepoint", ArrayType(DoubleType()), True),
        StructField("geo_keys", MapType(StringType(), StringType()), True),
    ])),

    StructField("gdal", StructType([
        StructField("default", MapType(StringType(), StringType()), True),
        StructField("image_structure", MapType(StringType(), StringType()), True),
        StructField("rpc", MapType(StringType(), StringType()), True),
        StructField("exif", MapType(StringType(), StringType()), True),
    ])),

    StructField("spatial", StructType([
        StructField("bbox", ArrayType(DoubleType()), True),
        StructField("center", ArrayType(DoubleType()), True),
    ])),

    StructField("gcps", StructType([
        StructField("count", IntegerType(), True),
        StructField("points", ArrayType(MapType(StringType(), StringType())), True),
    ])),

    StructField("quality", StructType([
        StructField("band_stats", MapType(StringType(), StructType([
            StructField("min", DoubleType(), True),
            StructField("max", DoubleType(), True),
            StructField("mean", DoubleType(), True),
            StructField("std", DoubleType(), True),
        ])))
    ])),
])


# =========================================================
# HELPERS
# =========================================================

def md5_file(path):
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def flatten(md):
    return {str(k): str(v) for k, v in (md or {}).items()}


# =========================================================
# EPSG FIX (CORRECT GDAL WAY)
# =========================================================

def extract_epsg(srs):
    if not srs:
        return None

    try:
        srs.AutoIdentifyEPSG()
        code = srs.GetAuthorityCode(None)
        if code:
            return int(code)
    except:
        pass

    try:
        return int(srs.GetAttrValue("AUTHORITY", 1))
    except:
        return None


# =========================================================
# GDAL DOMAIN EXTRACTION
# =========================================================

def extract_gdal(ds):
    return {
        "default": flatten(ds.GetMetadata()),
        "image_structure": flatten(ds.GetMetadata("IMAGE_STRUCTURE")),
        "rpc": flatten(ds.GetMetadata("RPC")),
        "exif": flatten(ds.GetMetadata("EXIF")),
    }


# =========================================================
# TIFF IFD (SAFE, GDAL LIMITED)
# =========================================================

def extract_ifd(ds):
    md = ds.GetMetadata("TIFF") or {}

    return {
        "compression": md.get("COMPRESSION"),
        "photometric": md.get("PHOTOMETRIC"),
        "planar_config": md.get("PLANARCONFIG"),
        "rows_per_strip": md.get("ROWSPERSTRIP"),
        "tile_width": md.get("TILEWIDTH"),
        "tile_length": md.get("TILELENGTH"),
        "predictor": md.get("PREDICTOR"),
    }


# =========================================================
# GEOTIFF
# =========================================================

def extract_geotiff(ds):
    md = ds.GetMetadata("GEOTIFF") or {}

    return {
        "model_pixel_scale": [float(x) for x in md.get("MODELPIXELSCALETAG", "").split()] if md.get("MODELPIXELSCALETAG") else [],
        "model_tiepoint": [float(x) for x in md.get("MODELTIEPOINTTAG", "").split()] if md.get("MODELTIEPOINTTAG") else [],
        "geo_keys": flatten(md),
    }


# =========================================================
# GCP
# =========================================================

def extract_gcps(ds):
    gcps = ds.GetGCPs()

    return {
        "count": len(gcps),
        "points": [
            {
                "row": g.GCPRow,
                "col": g.GCPCol,
                "x": g.GCPX,
                "y": g.GCPY,
                "z": g.GCPZ,
            }
            for g in gcps
        ]
    }


# =========================================================
# MAIN EXTRACTOR
# =========================================================

def extract_tiff(path):

    ds = gdal.Open(path)

    gt = ds.GetGeoTransform()
    srs = ds.GetSpatialRef()

    band_stats = {}

    for i in range(1, ds.RasterCount + 1):
        band = ds.GetRasterBand(i)
        arr = band.ReadAsArray()

        band_stats[f"band_{i}"] = {
            "min": float(np.nanmin(arr)),
            "max": float(np.nanmax(arr)),
            "mean": float(np.nanmean(arr)),
            "std": float(np.nanstd(arr)),
        }

    x_min = gt[0]
    y_max = gt[3]
    x_max = x_min + gt[1] * ds.RasterXSize
    y_min = y_max + gt[5] * ds.RasterYSize

    return {
        "file": {
            "path": path,
            "filename": os.path.basename(path),
            "extension": os.path.splitext(path)[1],
            "size_bytes": os.path.getsize(path),
            "checksum_md5": md5_file(path),
        },

        "raster": {
            "driver": ds.GetDriver().ShortName,
            "width": ds.RasterXSize,
            "height": ds.RasterYSize,
            "bands_count": ds.RasterCount,
            "dtypes": [
                gdal.GetDataTypeName(ds.GetRasterBand(i).DataType)
                for i in range(1, ds.RasterCount + 1)
            ],
            "crs_wkt": srs.ExportToWkt() if srs else None,
            "epsg": extract_epsg(srs),
            "transform": list(gt),
            "nodata": ds.GetRasterBand(1).GetNoDataValue(),
            "metadata": flatten(ds.GetMetadata()),
        },

        "tiff_ifd": extract_ifd(ds),

        "geotiff": extract_geotiff(ds),

        "gdal": extract_gdal(ds),

        "spatial": {
            "bbox": [x_min, y_min, x_max, y_max],
            "center": [(x_min + x_max) / 2, (y_min + y_max) / 2],
        },

        "gcps": extract_gcps(ds),

        "quality": {
            "band_stats": band_stats
        }
    }


# =========================================================
# SPARK ENTRY
# =========================================================

def run_spark(path):

    spark = SparkSession.builder \
        .appName("GeoTIFF-GDAL-Iceberg-Fixed") \
        .getOrCreate()

    data = extract_tiff(path)

    return spark.createDataFrame([data], schema=ICEBERG_SCHEMA)


# =========================================================
# ENTRY
# =========================================================

if __name__ == "__main__":
    import sys

    df = run_spark(sys.argv[1])
    df.printSchema()
    df.show(truncate=False, vertical=True)
