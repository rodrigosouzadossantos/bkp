import os
import hashlib
import numpy as np

from osgeo import gdal, osr
from pyspark.sql import SparkSession
from pyspark.sql.types import *

try:
    import tifffile
except ImportError:
    tifffile = None


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
        StructField("rows_per_strip", IntegerType(), True),
        StructField("tile_width", IntegerType(), True),
        StructField("tile_length", IntegerType(), True),
        StructField("predictor", IntegerType(), True),
        StructField("bits_per_sample", ArrayType(IntegerType()), True),
        StructField("samples_per_pixel", IntegerType(), True),
        StructField("sample_format", ArrayType(StringType()), True),
        StructField("orientation", StringType(), True),
        StructField("byte_order", StringType(), True),
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
        StructField("band_stats", MapType(
            StringType(),
            StructType([
                StructField("min", DoubleType(), True),
                StructField("max", DoubleType(), True),
                StructField("mean", DoubleType(), True),
                StructField("std", DoubleType(), True),
                StructField("valid_pixels", LongType(), True),
                StructField("nodata_pixels", LongType(), True),
                StructField("valid_percent", DoubleType(), True),
            ])
        ))
    ])),

    StructField("sidecars", MapType(StringType(), BooleanType()), True),

    StructField("overviews", MapType(StringType(), IntegerType()), True),

    StructField("masks", MapType(StringType(), StringType()), True),
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
    if not md:
        return {}

    return {
        str(k): str(v)
        for k, v in md.items()
    }


def safe_int(v):
    try:
        return int(v)
    except:
        return None


def safe_float(v):
    try:
        return float(v)
    except:
        return None


# =========================================================
# EPSG
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
        code = srs.GetAttrValue("AUTHORITY", 1)

        if code:
            return int(code)

    except:
        pass

    return None


# =========================================================
# GDAL DOMAINS
# =========================================================

def extract_gdal(ds):

    return {
        "default": flatten(ds.GetMetadata()),
        "image_structure": flatten(ds.GetMetadata("IMAGE_STRUCTURE")),
        "rpc": flatten(ds.GetMetadata("RPC")),
        "exif": flatten(ds.GetMetadata("EXIF")),
    }


# =========================================================
# TIFF IFD EXTRACTION
# =========================================================

TIFF_COMPRESSION = {
    1: "Uncompressed",
    5: "LZW",
    7: "JPEG",
    8: "Deflate",
    32946: "Deflate",
}

TIFF_PHOTOMETRIC = {
    0: "WhiteIsZero",
    1: "BlackIsZero",
    2: "RGB",
    3: "Palette",
    4: "TransparencyMask",
}

TIFF_PLANAR = {
    1: "Chunky",
    2: "Planar",
}

TIFF_ORIENTATION = {
    1: "TopLeft",
    2: "TopRight",
    3: "BottomRight",
    4: "BottomLeft",
    5: "LeftTop",
    6: "RightTop",
    7: "RightBottom",
    8: "LeftBottom",
}

SAMPLE_FORMAT = {
    1: "Unsigned",
    2: "Signed",
    3: "Float",
    4: "Undefined",
}


def extract_ifd(path):

    if tifffile is None:
        return {
            "compression": None,
            "photometric": None,
            "planar_config": None,
            "rows_per_strip": None,
            "tile_width": None,
            "tile_length": None,
            "predictor": None,
            "bits_per_sample": None,
            "samples_per_pixel": None,
            "sample_format": None,
            "orientation": None,
            "byte_order": None,
        }

    with tifffile.TiffFile(path) as tif:

        page = tif.pages[0]
        tags = page.tags

        compression = tags.get("Compression")
        photometric = tags.get("PhotometricInterpretation")
        planar = tags.get("PlanarConfiguration")
        orientation = tags.get("Orientation")
        predictor = tags.get("Predictor")
        rows_per_strip = tags.get("RowsPerStrip")
        tile_width = tags.get("TileWidth")
        tile_length = tags.get("TileLength")
        bits_per_sample = tags.get("BitsPerSample")
        samples_per_pixel = tags.get("SamplesPerPixel")
        sample_format = tags.get("SampleFormat")

        sample_formats = None

        if sample_format:
            vals = sample_format.value

            if not isinstance(vals, tuple):
                vals = (vals,)

            sample_formats = [
                SAMPLE_FORMAT.get(v, str(v))
                for v in vals
            ]

        return {
            "compression": TIFF_COMPRESSION.get(
                compression.value if compression else None,
                str(compression.value) if compression else None
            ),

            "photometric": TIFF_PHOTOMETRIC.get(
                photometric.value if photometric else None,
                str(photometric.value) if photometric else None
            ),

            "planar_config": TIFF_PLANAR.get(
                planar.value if planar else None,
                str(planar.value) if planar else None
            ),

            "rows_per_strip": safe_int(
                rows_per_strip.value if rows_per_strip else None
            ),

            "tile_width": safe_int(
                tile_width.value if tile_width else None
            ),

            "tile_length": safe_int(
                tile_length.value if tile_length else None
            ),

            "predictor": safe_int(
                predictor.value if predictor else None
            ),

            "bits_per_sample":
                list(bits_per_sample.value)
                if bits_per_sample and isinstance(bits_per_sample.value, tuple)
                else (
                    [safe_int(bits_per_sample.value)]
                    if bits_per_sample
                    else None
                ),

            "samples_per_pixel": safe_int(
                samples_per_pixel.value if samples_per_pixel else None
            ),

            "sample_format": sample_formats,

            "orientation": TIFF_ORIENTATION.get(
                orientation.value if orientation else None,
                str(orientation.value) if orientation else None
            ),

            "byte_order": tif.byteorder,
        }


# =========================================================
# GEOTIFF
# =========================================================

def extract_geotiff(path):

    if tifffile is None:
        return {
            "model_pixel_scale": [],
            "model_tiepoint": [],
            "geo_keys": {},
        }

    with tifffile.TiffFile(path) as tif:

        page = tif.pages[0]
        tags = page.tags

        pixel_scale = []
        tiepoint = []

        if "ModelPixelScaleTag" in tags:
            pixel_scale = [
                float(x)
                for x in tags["ModelPixelScaleTag"].value
            ]

        if "ModelTiepointTag" in tags:
            tiepoint = [
                float(x)
                for x in tags["ModelTiepointTag"].value
            ]

        geo_keys = {}

        if hasattr(page, "geotiff_tags") and page.geotiff_tags:
            geo_keys = {
                str(k): str(v)
                for k, v in page.geotiff_tags.items()
            }

        return {
            "model_pixel_scale": pixel_scale,
            "model_tiepoint": tiepoint,
            "geo_keys": geo_keys,
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
# QUALITY
# =========================================================

def compute_band_stats(band):

    arr = band.ReadAsArray()

    nodata = band.GetNoDataValue()

    if nodata is not None:
        valid = arr[arr != nodata]
    else:
        valid = arr.flatten()

    if valid.size == 0:
        return {
            "min": None,
            "max": None,
            "mean": None,
            "std": None,
            "valid_pixels": 0,
            "nodata_pixels": int(arr.size),
            "valid_percent": 0.0,
        }

    return {
        "min": float(np.min(valid)),
        "max": float(np.max(valid)),
        "mean": float(np.mean(valid)),
        "std": float(np.std(valid)),
        "valid_pixels": int(valid.size),
        "nodata_pixels": int(arr.size - valid.size),
        "valid_percent": float((valid.size / arr.size) * 100.0),
    }


# =========================================================
# SIDECARS
# =========================================================

def extract_sidecars(path):

    return {
        "worldfile_exists": any([
            os.path.exists(path + ext)
            for ext in [".tfw", ".wld"]
        ]),

        "aux_xml_exists": os.path.exists(path + ".aux.xml"),

        "ovr_exists": os.path.exists(path + ".ovr"),
    }


# =========================================================
# OVERVIEWS
# =========================================================

def extract_overviews(ds):

    out = {}

    for i in range(1, ds.RasterCount + 1):

        band = ds.GetRasterBand(i)

        out[f"band_{i}"] = band.GetOverviewCount()

    return out


# =========================================================
# MASKS
# =========================================================

MASK_FLAGS = {
    gdal.GMF_ALL_VALID: "ALL_VALID",
    gdal.GMF_PER_DATASET: "PER_DATASET",
    gdal.GMF_ALPHA: "ALPHA",
    gdal.GMF_NODATA: "NODATA",
}


def extract_masks(ds):

    out = {}

    for i in range(1, ds.RasterCount + 1):

        band = ds.GetRasterBand(i)

        flags = band.GetMaskFlags()

        names = []

        for k, v in MASK_FLAGS.items():
            if flags & k:
                names.append(v)

        out[f"band_{i}"] = "|".join(names) if names else "NONE"

    return out


# =========================================================
# MAIN
# =========================================================

def extract_tiff(path):

    ds = gdal.Open(path)

    if ds is None:
        raise RuntimeError(f"Cannot open TIFF: {path}")

    gt = ds.GetGeoTransform()
    srs = ds.GetSpatialRef()

    x_min = gt[0]
    y_max = gt[3]

    x_max = x_min + (gt[1] * ds.RasterXSize)
    y_min = y_max + (gt[5] * ds.RasterYSize)

    band_stats = {}

    for i in range(1, ds.RasterCount + 1):

        band = ds.GetRasterBand(i)

        band_stats[f"band_{i}"] = compute_band_stats(band)

    result = {

        "file": {
            "path": path,
            "filename": os.path.basename(path),
            "extension": os.path.splitext(path)[1].lower(),
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

            "crs_wkt": srs.ExportToPrettyWkt() if srs else None,

            "epsg": extract_epsg(srs),

            "transform": [float(x) for x in gt],

            "nodata": safe_float(
                ds.GetRasterBand(1).GetNoDataValue()
            ),

            "metadata": flatten(ds.GetMetadata()),
        },

        "tiff_ifd": extract_ifd(path),

        "geotiff": extract_geotiff(path),

        "gdal": extract_gdal(ds),

        "spatial": {
            "bbox": [
                float(x_min),
                float(y_min),
                float(x_max),
                float(y_max),
            ],

            "center": [
                float((x_min + x_max) / 2),
                float((y_min + y_max) / 2),
            ],
        },

        "gcps": extract_gcps(ds),

        "quality": {
            "band_stats": band_stats
        },

        "sidecars": extract_sidecars(path),

        "overviews": extract_overviews(ds),

        "masks": extract_masks(ds),
    }

    ds = None

    return result


# =========================================================
# SPARK
# =========================================================

def run_spark(path):

    spark = (
        SparkSession.builder
        .appName("GeoTIFF-Unified-Extractor")
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

    if len(sys.argv) != 2:
        raise SystemExit(
            "Usage: python extractor.py <file.tif>"
        )

    df = run_spark(sys.argv[1])

    df.printSchema()

    df.show(
        truncate=False,
        vertical=True
    )
