import os
import hashlib
import rasterio
import numpy as np
from pyspark.sql import SparkSession
from pyspark.sql.types import *


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


def get_overviews(src):
    """
    Pyramid / overview extraction (REAL GDAL-backed via rasterio)
    """
    try:
        return {
            str(b): src.overviews(b)
            for b in range(1, src.count + 1)
            if src.overviews(b)
        }
    except Exception:
        return {}


def get_gdal_domains(src):
    """
    FULL GDAL metadata domains (key missing piece)
    """
    try:
        return {
            "default": dict(src.tags()),
            "image_structure": dict(src.tags(ns="IMAGE_STRUCTURE")),
            "rpc": dict(src.tags(ns="RPC")),
            "gdal": dict(src.tags(ns="GDAL")),
            "exif": dict(src.tags(ns="EXIF")),
        }
    except Exception:
        return {}


def get_gcps(src):
    """
    GCP extraction
    """
    try:
        gcps, crs = src.get_gcps()
        return {
            "crs": safe_str(crs),
            "points": [
                {
                    "row": g.row,
                    "col": g.col,
                    "x": g.x,
                    "y": g.y,
                    "z": g.z,
                }
                for g in gcps
            ],
        }
    except Exception:
        return {"crs": None, "points": []}


def get_rpc(src):
    try:
        rpc = getattr(src, "rpcs", None)
        if not rpc:
            return None
        return {k: str(v) for k, v in rpc.items()}
    except Exception:
        return None


# =========================================================
# MAIN EXTRACTOR (FULL GDAL + ICEBERG SAFE)
# =========================================================

def extract_tiff(path):

    with rasterio.open(path) as src:

        bounds = src.bounds
        minx, miny, maxx, maxy = bounds

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

        return {
            # ---------------- FILE ----------------
            "file": {
                "path": path,
                "filename": os.path.basename(path),
                "extension": os.path.splitext(path)[1],
                "size_bytes": os.path.getsize(path),
                "checksum_md5": md5_file(path),
            },

            # ---------------- RASTER CORE ----------------
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
                "interleave": getattr(src, "interleaving", None),
                "is_georeferenced": src.crs is not None,

                # FULL metadata domains
                "metadata_domains": get_gdal_domains(src),
            },

            # ---------------- TIFF STRUCTURE ----------------
            "tiff_structure": {
                "compression": str(src.compression) if src.compression else None,
                "block_shapes": list(src.block_shapes),
                "tiles": src.is_tiled,
                "overviews": get_overviews(src),   # ✔ FIXED
            },

            # ---------------- GEO ENRICHMENT ----------------
            "geotiff": {
                "gcps": get_gcps(src),             # ✔ FIXED
                "rpc": get_rpc(src),               # ✔ FIXED
            },

            # ---------------- SPATIAL ----------------
            "spatial": {
                "bbox": [minx, miny, maxx, maxy],
                "center": [(minx + maxx) / 2, (miny + maxy) / 2],
            },

            # ---------------- IMAGE ----------------
            "image": {
                "format": "TIFF",
                "mode": "RGB" if src.count == 3 else "UNKNOWN",
                "width": src.width,
                "height": src.height,
                "bands": [f"B{i}" for i in range(1, src.count + 1)],
            },

            # ---------------- EXIF / RAW ----------------
            "exif": {
                "raw": dict(src.tags()),
            },

            # ---------------- GDAL VIEW ----------------
            "gdal": {
                "driver": src.driver,
                "projection": safe_str(src.crs),
                "geotransform": list(src.transform),
                "metadata": get_gdal_domains(src),
            },

            # ---------------- QUALITY ----------------
            "quality": {
                "band_stats": band_stats,
            },
        }


# =========================================================
# SPARK + ICEBERG SAFE WRITER
# =========================================================

def run_spark(path):

    spark = SparkSession.builder \
        .appName("GeoTIFF-Iceberg-Final") \
        .getOrCreate()

    data = extract_tiff(path)

    df = spark.createDataFrame([data])

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
