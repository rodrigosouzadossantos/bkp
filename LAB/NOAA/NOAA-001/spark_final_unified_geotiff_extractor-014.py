import subprocess
import json
import hashlib
from pyspark.sql import SparkSession
from pyspark.sql.types import (
    StructType, StructField, StringType, LongType, DoubleType,
    ArrayType, MapType, IntegerType
)


# =========================
# SPARK INIT
# =========================
spark = SparkSession.builder.appName("GeoTIFFExtractor").getOrCreate()


# =========================
# SCHEMA (FIXED + SAFE)
# =========================
schema = StructType([
    StructField("file", StructType([
        StructField("path", StringType(), False),
        StructField("filename", StringType(), False),
        StructField("extension", StringType(), True),
        StructField("size_bytes", LongType(), True),
        StructField("md5", StringType(), True),
    ]), True),

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

        StructField("bbox", StructType([
            StructField("upperLeft", ArrayType(DoubleType()), True),
            StructField("lowerLeft", ArrayType(DoubleType()), True),
            StructField("lowerRight", ArrayType(DoubleType()), True),
            StructField("upperRight", ArrayType(DoubleType()), True),
            StructField("center", ArrayType(DoubleType()), True),
        ]), True),

        StructField("center", ArrayType(DoubleType()), True),
        StructField("nodata", DoubleType(), True),
    ]), True),

    StructField("quality", MapType(
        StringType(),
        StructType([
            StructField("min", DoubleType(), True),
            StructField("max", DoubleType(), True),
            StructField("mean", DoubleType(), True),
            StructField("std", DoubleType(), True),
        ])
    ), True),
])


# =========================
# HELPERS
# =========================

def md5_file(path):
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def run_gdalinfo(path):
    out = subprocess.check_output(["gdalinfo", "-json", path])
    return json.loads(out)


def run_exiftool(path):
    try:
        out = subprocess.check_output(["exiftool", "-j", path])
        data = json.loads(out)[0]
        return {k: str(v) for k, v in data.items()}
    except Exception:
        return {}


# =========================
# NORMALIZER (CRITICAL FIX)
# =========================
def build_bbox(g):
    # GDAL bounds if available
    if "cornerCoordinates" in g:
        c = g["cornerCoordinates"]
        return {
            "upperLeft":  c.get("upperLeft"),
            "lowerLeft":  c.get("lowerLeft"),
            "lowerRight": c.get("lowerRight"),
            "upperRight": c.get("upperRight"),
            "center":     c.get("center"),
        }
    return None


def extract_gdal(g):
    return {
        "driver": g.get("driver"),
        "width": g.get("size", [None, None])[0],
        "height": g.get("size", [None, None])[1],
        "bands": len(g.get("bands", [])),
        "dtype": [b.get("type") for b in g.get("bands", [])],
        "crs_wkt": g.get("coordinateSystem", {}).get("wkt"),
        "epsg": g.get("coordinateSystem", {}).get("id", {}).get("authorityCode"),
        "transform": g.get("geoTransform"),
        "bbox": build_bbox(g),
        "center": g.get("cornerCoordinates", {}).get("center"),
        "nodata": None
    }


def extract_quality(g):
    q = {}
    for i, b in enumerate(g.get("bands", []), start=1):
        stats = b.get("statistics", {})
        if stats:
            q[f"band_{i}"] = {
                "min": stats.get("minimum"),
                "max": stats.get("maximum"),
                "mean": stats.get("mean"),
                "std": stats.get("stdDev"),
            }
    return q


# =========================
# MAIN EXTRACTOR
# =========================
def extract_record(path):

    g = run_gdalinfo(path)
    exif = run_exiftool(path)

    record = {
        "file": {
            "path": path,
            "filename": path.split("/")[-1],
            "extension": path.split(".")[-1],
            "size_bytes": None,
            "md5": md5_file(path)
        },

        "exiftool": exif,

        "gdal": extract_gdal(g),

        "quality": extract_quality(g)
    }

    return record


# =========================
# SAFE NORMALIZER (FIX CRASH)
# =========================
def normalize(record):
    g = record.get("gdal", {})

    # ensure bbox is STRUCT, not dict with wrong shape
    bbox = g.get("bbox")
    if isinstance(bbox, dict):
        g["bbox"] = {
            "upperLeft": bbox.get("upperLeft"),
            "lowerLeft": bbox.get("lowerLeft"),
            "lowerRight": bbox.get("lowerRight"),
            "upperRight": bbox.get("upperRight"),
            "center": bbox.get("center"),
        }

    record["gdal"] = g
    return record


# =========================
# RUN
# =========================
if __name__ == "__main__":

    import sys

    path = sys.argv[1]

    record = extract_record(path)
    record = normalize(record)

    df = spark.createDataFrame([record], schema=schema)

    df.printSchema()
    df.show(truncate=False)
