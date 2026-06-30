#!/usr/bin/env python3
"""
Full TIFF / GeoTIFF metadata extractor

Extracts:
- TIFF tags
- EXIF metadata
- GeoTIFF metadata
- GDAL metadata
- Raster metadata
- Image statistics
- CRS / bounds / transform
- Raw TIFF structure

Dependencies:

pip install tifffile rasterio pillow numpy pyexiftool

Optional:
pip install GDAL

System dependency:
sudo apt install exiftool

Usage:
python extract_tiff_metadata.py image.tif

Output:
image.tif.metadata.json
"""

import json
import math
import subprocess
import sys
from pathlib import Path
from pprint import pprint

import numpy as np
import rasterio
from PIL import Image
from PIL.TiffTags import TAGS
from tifffile import TiffFile

# ------------------------------------------------------------
# Helpers
# ------------------------------------------------------------

def sanitize(value):
    """
    Convert non-serializable objects into JSON-safe values.
    """
    try:
        json.dumps(value)
        return value
    except Exception:
        pass

    if isinstance(value, bytes):
        return value.hex()

    if isinstance(value, np.ndarray):
        return value.tolist()

    if isinstance(value, (np.integer,)):
        return int(value)

    if isinstance(value, (np.floating,)):
        return float(value)

    if isinstance(value, (tuple, list)):
        return [sanitize(v) for v in value]

    if isinstance(value, dict):
        return {str(k): sanitize(v) for k, v in value.items()}

    return str(value)


# ------------------------------------------------------------
# Basic file info
# ------------------------------------------------------------

def extract_file_info(path):
    p = Path(path)

    stat = p.stat()

    return {
        "path": str(p.resolve()),
        "filename": p.name,
        "size_bytes": stat.st_size,
    }


# ------------------------------------------------------------
# TIFF TAGS (LOW LEVEL)
# ------------------------------------------------------------

def extract_tiff_tags(path):
    result = {}

    with TiffFile(path) as tif:
        result["is_bigtiff"] = tif.is_bigtiff
        result["byteorder"] = tif.byteorder
        result["pages_count"] = len(tif.pages)

        pages = []

        for idx, page in enumerate(tif.pages):

            page_info = {
                "page_index": idx,
                "shape": sanitize(page.shape),
                "dtype": str(page.dtype),
                "photometric": str(page.photometric),
                "compression": str(page.compression),
                "tags": {},
            }

            for tag in page.tags.values():

                page_info["tags"][tag.name] = {
                    "code": tag.code,
                    "dtype": str(tag.dtype),
                    "count": tag.count,
                    "value": sanitize(tag.value),
                }

            pages.append(page_info)

        result["pages"] = pages

    return result


# ------------------------------------------------------------
# PIL / Pillow metadata
# ------------------------------------------------------------

def extract_pillow(path):

    img = Image.open(path)

    result = {
        "format": img.format,
        "mode": img.mode,
        "size": img.size,
        "width": img.width,
        "height": img.height,
        "bands": img.getbands(),
        "info": sanitize(img.info),
        "tags": {},
    }

    if hasattr(img, "tag_v2"):
        for tag_id, value in img.tag_v2.items():
            tag_name = TAGS.get(tag_id, f"TAG_{tag_id}")
            result["tags"][tag_name] = sanitize(value)

    return result


# ------------------------------------------------------------
# Rasterio / GeoTIFF metadata
# ------------------------------------------------------------

def extract_rasterio(path):

    with rasterio.open(path) as src:

        result = {
            "driver": src.driver,
            "width": src.width,
            "height": src.height,
            "count": src.count,
            "dtypes": src.dtypes,
            "indexes": src.indexes,
            "descriptions": src.descriptions,
            "colorinterp": [str(x) for x in src.colorinterp],
            "bounds": sanitize(src.bounds),
            "transform": str(src.transform),
            "crs": str(src.crs),
            "res": src.res,
            "nodata": src.nodata,
            "meta": sanitize(src.meta),
            "tags": sanitize(src.tags()),
            "band_tags": {},
            "statistics": {},
        }

        # Band tags
        for band in src.indexes:
            result["band_tags"][band] = sanitize(src.tags(band))

        # Statistics
        for band in src.indexes:

            data = src.read(band)

            stats = {
                "min": float(np.min(data)),
                "max": float(np.max(data)),
                "mean": float(np.mean(data)),
                "std": float(np.std(data)),
                "median": float(np.median(data)),
                "shape": list(data.shape),
            }

            result["statistics"][f"band_{band}"] = stats

    return result


# ------------------------------------------------------------
# EXIFTOOL
# ------------------------------------------------------------

def extract_exiftool(path):

    try:

        cmd = [
            "exiftool",
            "-j",
            "-struct",
            str(path),
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True,
        )

        data = json.loads(result.stdout)

        if data:
            return sanitize(data[0])

        return {}

    except Exception as e:
        return {
            "error": str(e)
        }


# ------------------------------------------------------------
# GDAL metadata
# ------------------------------------------------------------

def extract_gdal(path):

    try:
        from osgeo import gdal

        ds = gdal.Open(path)

        if ds is None:
            return {
                "error": "Could not open dataset"
            }

        result = {
            "description": ds.GetDescription(),
            "driver": ds.GetDriver().ShortName,
            "size": {
                "width": ds.RasterXSize,
                "height": ds.RasterYSize,
                "bands": ds.RasterCount,
            },
            "projection": ds.GetProjection(),
            "geotransform": sanitize(ds.GetGeoTransform()),
            "metadata": sanitize(ds.GetMetadata()),
            "metadata_domains": {},
        }

        # Metadata domains
        for domain in ds.GetMetadataDomainList() or []:
            result["metadata_domains"][domain] = sanitize(
                ds.GetMetadata(domain)
            )

        # Bands
        bands = {}

        for i in range(1, ds.RasterCount + 1):

            band = ds.GetRasterBand(i)

            bands[i] = {
                "datatype": gdal.GetDataTypeName(band.DataType),
                "nodata": band.GetNoDataValue(),
                "scale": band.GetScale(),
                "offset": band.GetOffset(),
                "unit_type": band.GetUnitType(),
                "metadata": sanitize(band.GetMetadata()),
            }

        result["bands"] = bands

        return result

    except Exception as e:
        return {
            "error": str(e)
        }


# ------------------------------------------------------------
# MAIN
# ------------------------------------------------------------

def main():

    if len(sys.argv) != 2:
        print("Usage:")
        print("python extract_tiff_metadata.py image.tif")
        sys.exit(1)

    path = sys.argv[1]

    result = {
        "file_info": extract_file_info(path),
        "tiff": extract_tiff_tags(path),
        "pillow": extract_pillow(path),
        "rasterio": extract_rasterio(path),
        "exiftool": extract_exiftool(path),
        "gdal": extract_gdal(path),
    }

    output_path = f"{path}.metadata.json"

    with open(output_path, "w") as f:
        json.dump(
            sanitize(result),
            f,
            indent=2,
            ensure_ascii=False,
        )

    print("\n========================================")
    print("METADATA EXTRACTION COMPLETE")
    print("========================================")
    print(f"Input : {path}")
    print(f"Output: {output_path}")
    print("========================================\n")

    pprint(result["rasterio"])


if __name__ == "__main__":
    main()
