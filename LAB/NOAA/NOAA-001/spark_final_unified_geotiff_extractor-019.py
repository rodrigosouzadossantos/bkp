import hashlib
from pathlib import Path

import numpy as np
import rasterio
from rasterio.enums import Resampling
import tifffile as tiff


# -----------------------------
# SAFE HELPERS
# -----------------------------

def safe_md5(path, chunk_size=1024 * 1024):
    h = hashlib.md5()
    with open(path, "rb") as f:
        while chunk := f.read(chunk_size):
            h.update(chunk)
    return h.hexdigest()


def safe_crs_wkt(crs):
    """
    FIX:
    rasterio 1.4.4 does NOT support to_wkt(pretty=True)
    """
    if not crs:
        return None
    try:
        return crs.to_wkt()
    except Exception:
        return str(crs)


def enum_name(x):
    try:
        return x.name if hasattr(x, "name") else str(x)
    except Exception:
        return None


def safe_get(obj, attr, default=None):
    try:
        return getattr(obj, attr, default)
    except Exception:
        return default


# -----------------------------
# TIFF IFD EXTRACTION (FIXED)
# -----------------------------

def extract_tiff_ifd(path):
    with tiff.TiffFile(path) as tif:
        page = tif.pages[0]

        tags = page.tags

        def tag_value(name):
            try:
                return tags[name].value
            except Exception:
                return None

        # FIX: orientation is NOT a direct attribute on TiffPage
        orientation = tag_value("Orientation")

        # FIX: robust sample format handling
        sample_format = tag_value("SampleFormat")
        if isinstance(sample_format, (list, tuple, np.ndarray)):
            sample_format = [enum_name(x) for x in sample_format]
        else:
            sample_format = enum_name(sample_format)

        return {
            "compression": enum_name(tag_value("Compression")),
            "photometric": enum_name(tag_value("PhotometricInterpretation")),
            "planar_config": enum_name(tag_value("PlanarConfiguration")),
            "rows_per_strip": tag_value("RowsPerStrip"),
            "tile_width": tag_value("TileWidth"),
            "tile_length": tag_value("TileLength"),
            "predictor": tag_value("Predictor"),
            "bits_per_sample": tag_value("BitsPerSample"),
            "samples_per_pixel": tag_value("SamplesPerPixel"),
            "sample_format": sample_format,
            "orientation": enum_name(orientation),
            "byte_order": tif.byteorder,
        }


# -----------------------------
# MAIN EXTRACTION
# -----------------------------

def extract_geotiff_metadata(path):
    path = str(path)
    p = Path(path)

    # FILE INFO
    file_info = {
        "path": path,
        "filename": p.name,
        "extension": p.suffix,
        "size_bytes": p.stat().st_size,
        "checksum_md5": safe_md5(path),
    }

    # RASTER + CRS (rasterio)
    with rasterio.open(path) as ds:
        crs = ds.crs

        raster_info = {
            "driver": ds.driver,
            "width": ds.width,
            "height": ds.height,
            "bands_count": ds.count,
            "dtypes": [str(dtype) for dtype in ds.dtypes],
            "crs_wkt": safe_crs_wkt(crs),  # FIXED HERE
            "epsg": crs.to_epsg() if crs else None,
            "transform": list(ds.transform),
            "nodata": ds.nodata,
            "metadata": ds.tags(),
        }

        arr = ds.read(
            indexes=[1, 2, 3],
            out_dtype="float32",
            resampling=Resampling.nearest,
        )

        # spatial bbox
        bounds = ds.bounds
        spatial = {
            "bbox": [bounds.left, bounds.bottom, bounds.right, bounds.top],
            "center": [(bounds.left + bounds.right) / 2,
                       (bounds.top + bounds.bottom) / 2],
        }

    # TIFF IFD (FIXED)
    tiff_ifd = extract_tiff_ifd(path)

    # GEO + GDAL sidecar-ish info
    geotiff_info = {}
    gdal_info = {}

    try:
        with rasterio.open(path) as ds:
            geotiff_info = {
                "model_pixel_scale": list(ds.transform)[1:4],
                "model_tiepoint": [0, 0, 0, ds.transform[2], ds.transform[5], 0],
                "geo_keys": dict(ds.tags(ns="GEOTIFF")) if ds.tags(ns="GEOTIFF") else {},
            }
    except Exception:
        pass

    try:
        with rasterio.open(path) as ds:
            gdal_info = {
                "default": ds.tags(),
                "image_structure": ds.tags(ns="IMAGE_STRUCTURE"),
                "rpc": ds.tags(ns="RPC"),
                "exif": ds.tags(ns="EXIF"),
            }
    except Exception:
        pass

    # QUALITY STATS
    quality = {}
    try:
        bands = {}
        for i in range(arr.shape[0]):
            band = arr[i]
            valid = band[band != 0]  # simple nodata assumption

            bands[f"band_{i+1}"] = {
                "min": float(np.min(valid)) if valid.size else None,
                "max": float(np.max(valid)) if valid.size else None,
                "mean": float(np.mean(valid)) if valid.size else None,
                "std": float(np.std(valid)) if valid.size else None,
            }

        quality = {"band_stats": bands}
    except Exception:
        quality = {}

    return {
        "file": file_info,
        "raster": raster_info,
        "tiff_ifd": tiff_ifd,
        "geotiff": geotiff_info,
        "gdal": gdal_info,
        "spatial": spatial,
        "quality": quality,
    }


# -----------------------------
# ENTRYPOINT
# -----------------------------

def main():
    import sys

    if len(sys.argv) < 2:
        print("Usage: python script.py <file.tif>")
        return

    path = sys.argv[1]
    result = extract_geotiff_metadata(path)

    # Spark-style schema preview replacement
    import pprint
    pprint.pprint(result)


if __name__ == "__main__":
    main()
