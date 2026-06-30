import os
import hashlib
import numpy as np
import tifffile

from osgeo import gdal, osr
from pyspark.sql import SparkSession
from pyspark.sql.types import *


# =========================================================
# GDAL SAFETY
# =========================================================

gdal.UseExceptions()


# =========================================================
# SCHEMA
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
        StructField("bits_per_sample", StringType(), True),
        StructField("samples_per_pixel", StringType(), True),
        StructField("sample_format", StringType(), True),
        StructField("orientation", StringType(), True),
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


def safe_tag(tags, name):

    try:
        value = tags[name].value

        if isinstance(value, bytes):
            return value.decode(errors="ignore")

        return str(value)

    except:
        return None


def safe_array(tags, name):

    try:
        return [float(x) for x in tags[name].value]
    except:
        return []


# =========================================================
# EPSG EXTRACTION
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
# GDAL METADATA
# =========================================================

def extract_gdal(ds):

    return {
        "default": flatten(ds.GetMetadata()),
        "image_structure": flatten(ds.GetMetadata("IMAGE_STRUCTURE")),
        "rpc": flatten(ds.GetMetadata("RPC")),
        "exif": flatten(ds.GetMetadata("EXIF")),
    }


# =========================================================
# TIFF IFD EXTRACTION (TIFFFILE)
# =========================================================

def extract_ifd(path):

    with tifffile.TiffFile(path) as tif:

        page = tif.pages[0]
        tags = page.tags

        return {
            "compression": safe_tag(tags, "Compression"),
            "photometric": safe_tag(tags, "PhotometricInterpretation"),
            "planar_config": safe_tag(tags, "PlanarConfiguration"),
            "rows_per_strip": safe_tag(tags, "RowsPerStrip"),
            "tile_width": safe_tag(tags, "TileWidth"),
            "tile_length": safe_tag(tags, "TileLength"),
            "predictor": safe_tag(tags, "Predictor"),
            "bits_per_sample": safe_tag(tags, "BitsPerSample"),
            "samples_per_pixel": safe_tag(tags, "SamplesPerPixel"),
            "sample_format": safe_tag(tags, "SampleFormat"),
            "orientation": safe_tag(tags, "Orientation"),
        }


# =========================================================
# GEOTIFF EXTRACTION (TIFFFILE)
# =========================================================

def extract_geotiff(path):

    with tifffile.TiffFile(path) as tif:

        page = tif.pages[0]
        tags = page.tags

        geo_keys = {}

        try:

            gt = tif.geotiff_metadata or {}

            for k, v in gt.items():
                geo_keys[str(k)] = str(v)

        except:
            pass

        return {
            "model_pixel_scale": safe_array(tags, "ModelPixelScaleTag"),
            "model_tiepoint": safe_array(tags, "ModelTiepointTag"),
            "geo_keys": geo_keys,
        }


# =========================================================
# GCP EXTRACTION
# =========================================================

def extract_gcps(ds):

    gcps = ds.GetGCPs()

    return {
        "count": len(gcps),

        "points": [
            {
                "row": str(g.GCPRow),
                "col": str(g.GCPCol),
                "x": str(g.GCPX),
                "y": str(g.GCPY),
                "z": str(g.GCPZ),
            }
            for g in gcps
        ]
    }


# =========================================================
# SAFE BBOX
# =========================================================

def compute_bbox(gt, width, height):

    corners = []

    for px, py in [
        (0, 0),
        (width, 0),
        (0, height),
        (width, height),
    ]:

        x = gt[0] + px * gt[1] + py * gt[2]
        y = gt[3] + px * gt[4] + py * gt[5]

        corners.append((x, y))

    xs = [c[0] for c in corners]
    ys = [c[1] for c in corners]

    return [
        min(xs),
        min(ys),
        max(xs),
        max(ys),
    ]


# =========================================================
# BAND STATISTICS (FAST + SCALABLE)
# =========================================================

def extract_band_stats(ds):

    stats = {}

    for i in range(1, ds.RasterCount + 1):

        band = ds.GetRasterBand(i)

        try:
            s = band.GetStatistics(True, True)

            stats[f"band_{i}"] = {
                "min": float(s[0]),
                "max": float(s[1]),
                "mean": float(s[2]),
                "std": float(s[3]),
            }

        except:

            arr = band.ReadAsArray()

            stats[f"band_{i}"] = {
                "min": float(np.nanmin(arr)),
                "max": float(np.nanmax(arr)),
                "mean": float(np.nanmean(arr)),
                "std": float(np.nanstd(arr)),
            }

    return stats


# =========================================================
# MAIN EXTRACTOR
# =========================================================

def extract_tiff(path):

    ds = gdal.Open(path)

    if ds is None:
        raise RuntimeError(f"Could not open file: {path}")

    gt = ds.GetGeoTransform()
    srs = ds.GetSpatialRef()

    bbox = compute_bbox(
        gt,
        ds.RasterXSize,
        ds.RasterYSize
    )

    center = [
        (bbox[0] + bbox[2]) / 2,
        (bbox[1] + bbox[3]) / 2,
    ]

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
                gdal.GetDataTypeName(
                    ds.GetRasterBand(i).DataType
                )
                for i in range(1, ds.RasterCount + 1)
            ],

            "crs_wkt": srs.ExportToWkt() if srs else None,

            "epsg": extract_epsg(srs),

            "transform": list(gt),

            "nodata": ds.GetRasterBand(1).GetNoDataValue(),

            "metadata": flatten(ds.GetMetadata()),
        },

        "tiff_ifd": extract_ifd(path),

        "geotiff": extract_geotiff(path),

        "gdal": extract_gdal(ds),

        "spatial": {
            "bbox": bbox,
            "center": center,
        },

        "gcps": extract_gcps(ds),

        "quality": {
            "band_stats": extract_band_stats(ds)
        }
    }


# =========================================================
# SPARK ENTRY
# =========================================================

def run_spark(path):

    spark = (
        SparkSession.builder
        .appName("GeoTIFF-GDAL-TIFFFILE-Iceberg")
        .getOrCreate()
    )

    data = extract_tiff(path)

    return spark.createDataFrame(
        [data],
        schema=ICEBERG_SCHEMA
    )


# =========================================================
# ENTRY
# =========================================================

if __name__ == "__main__":

    import sys

    if len(sys.argv) < 2:
        raise RuntimeError(
            "Usage: python extractor.py <file.tif>"
        )

    df = run_spark(sys.argv[1])

    df.printSchema()

    df.show(
        truncate=False,
        vertical=True
    )
