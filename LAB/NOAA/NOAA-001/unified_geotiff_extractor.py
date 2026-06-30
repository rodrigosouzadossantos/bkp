#!/usr/bin/env python3

"""
Unified TIFF / GeoTIFF metadata extractor

Features
--------
- No duplicated metadata
- Unified normalized structure
- TIFF + GeoTIFF + EXIF + GDAL + Raster metadata
- Image statistics
- CRS + affine transform
- Pixel <-> geographic info
- JSON output

Dependencies
------------
uv pip install tifffile rasterio pillow numpy

Optional:
sudo apt install exiftool
sudo apt install gdal-bin libgdal-dev python3-gdal

Usage
-----
python unified_geotiff_extractor.py image.tif

Output
------
image.tif.unified.json
"""

import json
import math
import subprocess
import sys
from pathlib import Path

import numpy as np
import rasterio
from PIL import Image
from tifffile import TiffFile


# ============================================================
# HELPERS
# ============================================================

def sanitize(value):

    if isinstance(value, np.ndarray):
        return value.tolist()

    if isinstance(value, np.integer):
        return int(value)

    if isinstance(value, np.floating):
        return float(value)

    if isinstance(value, bytes):
        return value.hex()

    if isinstance(value, (list, tuple)):
        return [sanitize(v) for v in value]

    if isinstance(value, dict):
        return {str(k): sanitize(v) for k, v in value.items()}

    return value


def safe_exiftool(path):

    try:

        result = subprocess.run(
            [
                "exiftool",
                "-j",
                "-struct",
                path,
            ],
            capture_output=True,
            text=True,
            check=True,
        )

        return json.loads(result.stdout)[0]

    except Exception:
        return {}


def safe_gdalinfo(path):

    try:

        result = subprocess.run(
            [
                "gdalinfo",
                "-json",
                path,
            ],
            capture_output=True,
            text=True,
            check=True,
        )

        return json.loads(result.stdout)

    except Exception:
        return {}


# ============================================================
# TIFF TAG DECODER
# ============================================================

TIFF_PHOTOMETRIC = {
    0: "WhiteIsZero",
    1: "BlackIsZero",
    2: "RGB",
    3: "Palette",
    4: "TransparencyMask",
    5: "CMYK",
    6: "YCbCr",
    8: "CIELab",
}

TIFF_COMPRESSION = {
    1: "Uncompressed",
    5: "LZW",
    7: "JPEG",
    8: "Deflate",
    32773: "PackBits",
}

PLANAR_CONFIG = {
    1: "Chunky",
    2: "Planar",
}

ORIENTATION = {
    1: "TopLeft",
}


# ============================================================
# GEO TIFF KEY DECODER
# ============================================================

GEO_KEYS = {
    1024: "GTModelTypeGeoKey",
    1025: "GTRasterTypeGeoKey",
    1026: "GTCitationGeoKey",
    2048: "GeographicTypeGeoKey",
    2049: "GeogCitationGeoKey",
    2050: "GeogGeodeticDatumGeoKey",
    2052: "GeogLinearUnitsGeoKey",
    2054: "GeogAngularUnitsGeoKey",
    2056: "GeogEllipsoidGeoKey",
    2057: "GeogSemiMajorAxisGeoKey",
    2058: "GeogSemiMinorAxisGeoKey",
    2059: "GeogInvFlatteningGeoKey",
    3072: "ProjectedCSTypeGeoKey",
    3073: "PCSCitationGeoKey",
    3074: "ProjectionGeoKey",
    3076: "ProjLinearUnitsGeoKey",
}


def decode_geokeys(raw):

    result = []

    if not raw:
        return result

    for i in range(4, len(raw), 4):

        key_id = raw[i]
        location = raw[i + 1]
        count = raw[i + 2]
        value = raw[i + 3]

        result.append({
            "id": key_id,
            "name": GEO_KEYS.get(key_id, f"UNKNOWN_{key_id}"),
            "location": location,
            "count": count,
            "value": value,
        })

    return result


# ============================================================
# MAIN EXTRACTION
# ============================================================

def extract(path):

    path = str(path)

    result = {}

    # ========================================================
    # FILE
    # ========================================================

    p = Path(path)
    stat = p.stat()

    result["file"] = {
        "path": str(p.resolve()),
        "filename": p.name,
        "extension": p.suffix,
        "size_bytes": stat.st_size,
        "size_mb": round(stat.st_size / 1024 / 1024, 3),
    }

    # ========================================================
    # TIFF
    # ========================================================

    with TiffFile(path) as tif:

        page = tif.pages[0]

        tags = page.tags

        result["tiff"] = {
            "byte_order": "little-endian" if tif.byteorder == "<" else "big-endian",
            "bigtiff": tif.is_bigtiff,
            "pages": len(tif.pages),
            "dtype": str(page.dtype),
            "shape": sanitize(page.shape),
            "compression": TIFF_COMPRESSION.get(
                tags["Compression"].value,
                tags["Compression"].value,
            ),
            "photometric": TIFF_PHOTOMETRIC.get(
                tags["PhotometricInterpretation"].value,
                tags["PhotometricInterpretation"].value,
            ),
            "planar_configuration": PLANAR_CONFIG.get(
                tags["PlanarConfiguration"].value,
                tags["PlanarConfiguration"].value,
            ),
            "orientation": ORIENTATION.get(
                tags["Orientation"].value,
                tags["Orientation"].value,
            ),
            "bits_per_sample": sanitize(
                tags["BitsPerSample"].value
            ),
            "samples_per_pixel": tags["SamplesPerPixel"].value,
            "rows_per_strip": tags["RowsPerStrip"].value,
            "strips": len(tags["StripOffsets"].value),
        }

        # GEO TIFF TAGS

        geo = {}

        if "ModelPixelScaleTag" in tags:
            geo["pixel_scale"] = sanitize(
                tags["ModelPixelScaleTag"].value
            )

        if "ModelTiepointTag" in tags:
            geo["tie_points"] = sanitize(
                tags["ModelTiepointTag"].value
            )

        if "GeoAsciiParamsTag" in tags:
            geo["ascii_params"] = tags["GeoAsciiParamsTag"].value

        if "GeoDoubleParamsTag" in tags:
            geo["double_params"] = sanitize(
                tags["GeoDoubleParamsTag"].value
            )

        if "GeoKeyDirectoryTag" in tags:
            geo["keys"] = decode_geokeys(
                tags["GeoKeyDirectoryTag"].value
            )

        result["geotiff_tags"] = geo

    # ========================================================
    # PILLOW
    # ========================================================

    img = Image.open(path)

    result["image"] = {
        "format": img.format,
        "mode": img.mode,
        "width": img.width,
        "height": img.height,
        "bands": list(img.getbands()),
    }

    # ========================================================
    # RASTERIO
    # ========================================================

    with rasterio.open(path) as src:

        transform = src.transform

        width_m = src.width * src.res[0]
        height_m = src.height * src.res[1]

        raster = {
            "driver": src.driver,
            "count": src.count,
            "dtypes": list(src.dtypes),
            "crs": str(src.crs),
            "epsg": src.crs.to_epsg() if src.crs else None,
            "resolution": sanitize(src.res),
            "nodata": src.nodata,
            "bounds": sanitize(src.bounds),
            "transform": {
                "a": transform.a,
                "b": transform.b,
                "c": transform.c,
                "d": transform.d,
                "e": transform.e,
                "f": transform.f,
            },
            "extent_meters": {
                "width": width_m,
                "height": height_m,
            },
            "metadata": sanitize(src.tags()),
        }

        # BAND STATISTICS

        stats = {}

        for band in src.indexes:

            data = src.read(band)

            stats[f"band_{band}"] = {
                "min": float(np.min(data)),
                "max": float(np.max(data)),
                "mean": float(np.mean(data)),
                "std": float(np.std(data)),
                "median": float(np.median(data)),
            }

        raster["statistics"] = stats

        result["raster"] = raster

    # ========================================================
    # EXIFTOOL
    # ========================================================

    exif = safe_exiftool(path)

    if exif:

        result["exif"] = {
            "mime_type": exif.get("MIMEType"),
            "megapixels": exif.get("Megapixels"),
            "geo_tiff_version": exif.get("GeoTiffVersion"),
            "projection": exif.get("Projection"),
            "citation": exif.get("PCSCitation"),
        }

    # ========================================================
    # GDALINFO
    # ========================================================

    gdal = safe_gdalinfo(path)

    if gdal:

        result["gdal"] = {
            "driver": gdal.get("driverShortName"),
            "files": gdal.get("files"),
            "corner_coordinates": gdal.get("cornerCoordinates"),
            "metadata": gdal.get("metadata"),
        }

    return sanitize(result)


# ============================================================
# MAIN
# ============================================================

def main():

    if len(sys.argv) != 2:

        print("\nUsage:")
        print("python unified_geotiff_extractor.py image.tif\n")
        sys.exit(1)

    path = sys.argv[1]

    result = extract(path)

    output = f"{path}.unified.json"

    with open(output, "w") as f:

        json.dump(
            result,
            f,
            indent=2,
            ensure_ascii=False,
        )

    print("\n====================================")
    print("UNIFIED EXTRACTION COMPLETE")
    print("====================================")
    print(f"Input : {path}")
    print(f"Output: {output}")
    print("====================================\n")


if __name__ == "__main__":
    main()
