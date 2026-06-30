import os
import json
import subprocess
from typing import Any, Dict

import rasterio
from rasterio.io import DatasetReader
from PIL import Image


# -------------------------------------------------------
# SAFE JSON SERIALIZER
# -------------------------------------------------------
def safe(obj: Any):
    """Ensure everything becomes Spark/JSON compatible"""
    if isinstance(obj, (str, int, float, bool)) or obj is None:
        return obj
    if isinstance(obj, dict):
        return {k: safe(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [safe(v) for v in obj]
    if hasattr(obj, "__dict__"):
        return str(obj)
    return str(obj)


# -------------------------------------------------------
# FILE METADATA
# -------------------------------------------------------
def extract_file_info(path: str) -> Dict:
    stat = os.stat(path)
    return {
        "path": path,
        "filename": os.path.basename(path),
        "extension": os.path.splitext(path)[1],
        "size_bytes": stat.st_size,
    }


# -------------------------------------------------------
# EXIFTOOL RAW DUMP (NO FILTERING)
# -------------------------------------------------------
def extract_exiftool(path: str) -> Dict:
    try:
        result = subprocess.run(
            ["exiftool", "-j", "-a", "-u", "-g1", path],
            capture_output=True,
            text=True,
            check=True,
        )
        return json.loads(result.stdout)[0]
    except Exception as e:
        return {"error": str(e)}


# -------------------------------------------------------
# PILLOW (IMAGE STRUCTURE ONLY)
# -------------------------------------------------------
def extract_pillow(path: str) -> Dict:
    try:
        img = Image.open(path)
        return {
            "format": img.format,
            "mode": img.mode,
            "size": img.size,
            "info": dict(img.info),
        }
    except Exception as e:
        return {"error": str(e)}


# -------------------------------------------------------
# RASTERIO CORE (NO DERIVED MATH)
# -------------------------------------------------------
def extract_rasterio(ds: DatasetReader) -> Dict:
    return {
        "driver": ds.driver,
        "width": ds.width,
        "height": ds.height,
        "count": ds.count,
        "dtypes": list(ds.dtypes),
        "indexes": list(ds.indexes),
        "nodata": ds.nodata,
        "crs": str(ds.crs) if ds.crs else None,
        "transform": list(ds.transform) if ds.transform else None,
        "bounds": tuple(ds.bounds) if ds.bounds else None,
        "res": ds.res,
        "metadata": safe(ds.meta),
        "tags": safe(ds.tags()),
        "band_tags": safe({i: ds.tags(i) for i in range(1, ds.count + 1)}),
    }


# -------------------------------------------------------
# TIFF LOW LEVEL STRUCTURE (RAW ACCESS ONLY)
# -------------------------------------------------------
def extract_tiff_structure(ds: DatasetReader) -> Dict:
    pages = []

    for i in range(ds.count):
        try:
            band = ds.read(i + 1, masked=False)
            pages.append(
                {
                    "band_index": i + 1,
                    "shape": list(band.shape),
                    "dtype": str(band.dtype),
                }
            )
        except Exception:
            pages.append(
                {
                    "band_index": i + 1,
                    "error": "could_not_read_band",
                }
            )

    return {
        "pages_count": ds.count,
        "pages": pages,
        "is_tiled": getattr(ds, "is_tiled", None),
        "block_shapes": getattr(ds, "block_shapes", None),
        "compression": str(getattr(ds, "compression", None)),
        "interleaving": getattr(ds, "interleaving", None),
    }


# -------------------------------------------------------
# GCP / RPC (RAW ONLY, NO INTERPRETATION)
# -------------------------------------------------------
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


# -------------------------------------------------------
# OVERVIEWS (PYRAMIDS)
# -------------------------------------------------------
def extract_overviews(ds: DatasetReader) -> Dict:
    try:
        return {
            str(i): ds.overviews(i)
            for i in range(1, ds.count + 1)
            if ds.overviews(i)
        }
    except Exception:
        return None


# -------------------------------------------------------
# MAIN PIPELINE
# -------------------------------------------------------
def extract_tiff(path: str) -> Dict:
    output = {
        "file": extract_file_info(path),
    }

    # Rasterio core
    with rasterio.open(path) as ds:
        output["raster"] = extract_rasterio(ds)
        output["tiff_structure"] = extract_tiff_structure(ds)
        output["geospatial_extended"] = extract_geospatial_extended(ds)
        output["overviews"] = extract_overviews(ds)

    # Pillow (image-level metadata)
    output["image"] = extract_pillow(path)

    # EXIFTool (full raw metadata dump)
    output["exiftool"] = extract_exiftool(path)

    return safe(output)


# -------------------------------------------------------
# CLI ENTRYPOINT
# -------------------------------------------------------
if __name__ == "__main__":
    import sys

    path = sys.argv[1]
    data = extract_tiff(path)

    print(json.dumps(data, indent=2))
