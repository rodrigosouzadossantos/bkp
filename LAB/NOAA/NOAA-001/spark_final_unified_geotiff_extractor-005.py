import os
import subprocess
import json
import hashlib
from typing import Any, Dict

import rasterio
from rasterio.io import DatasetReader
from PIL import Image


# =======================================================
# SAFE SERIALIZATION (Spark + Iceberg SAFE)
# =======================================================
def safe(obj: Any):
    if isinstance(obj, (str, int, float, bool)) or obj is None:
        return obj

    if isinstance(obj, dict):
        return {str(k): safe(v) for k, v in obj.items()}

    if isinstance(obj, (list, tuple)):
        return [safe(v) for v in obj]

    # IMPORTANT: NEVER pass GDAL/CRS/Affine objects
    return str(obj)


# =======================================================
# FILE METADATA
# =======================================================
def extract_file_info(path: str) -> Dict:
    stat = os.stat(path)

    return {
        "path": path,
        "filename": os.path.basename(path),
        "extension": os.path.splitext(path)[1],
        "size_bytes": stat.st_size,
        "checksum_md5": md5_file(path),
    }


def md5_file(path: str):
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


# =======================================================
# EXIFTOOL (RAW ONLY)
# =======================================================
def extract_exiftool(path: str) -> Dict:
    try:
        result = subprocess.run(
            ["exiftool", "-j", "-a", "-u", "-g1", path],
            capture_output=True,
            text=True,
            check=True,
        )
        return {"raw": json.loads(result.stdout)[0]}
    except Exception as e:
        return {"raw": {"error": str(e)}}


# =======================================================
# PILLOW (IMAGE LEVEL ONLY)
# =======================================================
def extract_pillow(path: str) -> Dict:
    try:
        img = Image.open(path)
        return {
            "format": img.format,
            "mode": img.mode,
            "width": img.size[0],
            "height": img.size[1],
            "info": safe(dict(img.info)),
        }
    except Exception as e:
        return {"error": str(e)}


# =======================================================
# RASTERIO CORE (STRICT PRIMITIVES ONLY)
# =======================================================
def extract_rasterio(ds: DatasetReader) -> Dict:

    # ---- SAFE BOUNDS (FIXED CRASH HERE) ----
    bounds = None
    if ds.bounds:
        bounds = [
            float(ds.bounds.left),
            float(ds.bounds.bottom),
            float(ds.bounds.right),
            float(ds.bounds.top),
        ]

    return {
        "driver": ds.driver,
        "width": ds.width,
        "height": ds.height,
        "count": ds.count,
        "dtypes": list(ds.dtypes),
        "indexes": list(ds.indexes),
        "nodata": float(ds.nodata) if ds.nodata is not None else None,

        # CRS SAFE STRING ONLY
        "crs": str(ds.crs) if ds.crs else None,

        # NEVER PASS Affine OBJECT
        "transform": list(ds.transform) if ds.transform else None,

        "bounds": bounds,
        "res": list(ds.res),

        # SAFE METADATA
        "metadata": safe(ds.meta),
        "tags": safe(ds.tags()),
        "band_tags": safe(
            {i: ds.tags(i) for i in range(1, ds.count + 1)}
        ),
    }


# =======================================================
# TIFF STRUCTURE (RAW BAND INFO ONLY)
# =======================================================
def extract_tiff_structure(ds: DatasetReader) -> Dict:

    pages = []

    for i in range(ds.count):
        try:
            band = ds.read(i + 1, masked=False)
            pages.append({
                "band_index": i + 1,
                "shape": list(band.shape),
                "dtype": str(band.dtype),
            })
        except Exception:
            pages.append({
                "band_index": i + 1,
                "error": "read_failed"
            })

    return {
        "pages_count": ds.count,
        "pages": pages,
        "is_tiled": getattr(ds, "is_tiled", None),
        "block_shapes": safe(getattr(ds, "block_shapes", None)),
        "compression": str(getattr(ds, "compression", None)),
        "interleaving": getattr(ds, "interleaving", None),
    }


# =======================================================
# GCP / RPC (RAW ONLY)
# =======================================================
def extract_geospatial_extended(ds: DatasetReader) -> Dict:
    out = {
        "gcps": None,
        "rpcs": None,
    }

    try:
        gcps, crs = ds.get_gcps()
        out["gcps"] = {
            "crs": str(crs) if crs else None,
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
        out["gcps"] = None

    try:
        out["rpcs"] = safe(ds.rpcs)
    except Exception:
        out["rpcs"] = None

    return out


# =======================================================
# OVERVIEWS
# =======================================================
def extract_overviews(ds: DatasetReader) -> Dict:
    try:
        return {
            str(i): ds.overviews(i)
            for i in range(1, ds.count + 1)
            if ds.overviews(i)
        }
    except Exception:
        return None


# =======================================================
# MAIN EXTRACTOR
# =======================================================
def extract_tiff(path: str) -> Dict:

    output = {
        "file": extract_file_info(path),
    }

    with rasterio.open(path) as ds:
        output["raster"] = extract_rasterio(ds)
        output["tiff_structure"] = extract_tiff_structure(ds)
        output["geospatial_extended"] = extract_geospatial_extended(ds)
        output["overviews"] = extract_overviews(ds)

    output["image"] = extract_pillow(path)
    output["exiftool"] = extract_exiftool(path)

    return safe(output)


# =======================================================
# SPARK ENTRY (NO JSON SERIALIZATION HACKS)
# =======================================================
def run_spark(path: str):

    from pyspark.sql import SparkSession

    spark = SparkSession.builder \
        .appName("GeoTIFF-Iceberg-Extractor") \
        .getOrCreate()

    data = extract_tiff(path)

    # IMPORTANT: direct Row ingestion (NO json.dumps)
    df = spark.createDataFrame([data])

    return df


# =======================================================
# CLI
# =======================================================
if __name__ == "__main__":
    import sys

    path = sys.argv[1]

    df = run_spark(path)

    df.printSchema()
    df.show(truncate=False)
