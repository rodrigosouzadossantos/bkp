from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any

from osgeo import gdal, osr

gdal.UseExceptions()


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class CornerCoordinate:
    pixel_x: float
    pixel_y: float
    projected_x: float
    projected_y: float
    longitude: float
    latitude: float


# =============================================================================
# UTILS
# =============================================================================

def to_dms(value: float, is_latitude: bool) -> str:
    """Convert decimal degrees to DMS format."""
    abs_value = abs(value)

    degrees = int(abs_value)
    minutes = int((abs_value - degrees) * 60)
    seconds = round((abs_value - degrees - minutes / 60) * 3600, 2)

    direction = (
        ("N" if value >= 0 else "S")
        if is_latitude
        else ("E" if value >= 0 else "W")
    )

    return f"{degrees}°{minutes}'{seconds}\"{direction}"


def print_section(title: str) -> None:
    print("\n" + "=" * 80)
    print(title)
    print("=" * 80)


def print_dict(data: dict[str, Any], indent: int = 0) -> None:
    """Pretty-print nested dictionaries."""
    prefix = " " * indent

    for key, value in data.items():
        if isinstance(value, dict):
            print(f"{prefix}{key}:")
            print_dict(value, indent + 2)
        else:
            print(f"{prefix}{key}: {value}")


# =============================================================================
# GDAL HELPERS
# =============================================================================

def open_dataset(path: str) -> gdal.Dataset:
    dataset = gdal.Open(path)

    if dataset is None:
        raise FileNotFoundError(f"Unable to open dataset: {path}")

    return dataset


def build_spatial_reference(dataset: gdal.Dataset) -> osr.SpatialReference | None:
    projection = dataset.GetProjection()

    if not projection:
        return None

    srs = osr.SpatialReference()
    srs.ImportFromWkt(projection)

    return srs


def create_coordinate_transform(
    source_srs: osr.SpatialReference,
) -> osr.CoordinateTransformation:
    target_srs = osr.SpatialReference()
    target_srs.ImportFromEPSG(4326)

    # Ensure lon/lat order
    target_srs.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)

    return osr.CoordinateTransformation(source_srs, target_srs)


# =============================================================================
# METADATA EXTRACTION
# =============================================================================

def extract_metadata(dataset: gdal.Dataset) -> dict[str, dict[str, str]]:
    metadata = {}

    for domain in dataset.GetMetadataDomainList() or []:
        metadata[domain] = dataset.GetMetadata(domain)

    return metadata


def extract_geotransform(dataset: gdal.Dataset) -> dict[str, Any]:
    gt = dataset.GetGeoTransform()

    if not gt:
        return {}

    return {
        "origin": {
            "x": gt[0],
            "y": gt[3],
        },
        "pixel_size": {
            "width": gt[1],
            "height": gt[5],
        },
        "rotation": {
            "x": gt[2],
            "y": gt[4],
        },
    }


def extract_projection_info(srs: osr.SpatialReference) -> dict[str, Any]:
    return {
        "identifiers": {
            "projected_cs": srs.GetAttrValue("PROJCS"),
            "geographic_cs": srs.GetAttrValue("GEOGCS"),
            "datum": srs.GetAttrValue("DATUM"),
            "projection": srs.GetAttrValue("PROJECTION"),
            "epsg": srs.GetAuthorityCode(None),
        },
        "prime_meridian": {
            "name": srs.GetAttrValue("PRIMEM"),
            "offset": srs.GetAttrValue("PRIMEM", 1),
        },
        "angular_units": {
            "name": srs.GetAttrValue("GEOGCS|UNIT"),
            "radians_per_unit": srs.GetAngularUnits(),
        },
        "linear_units": {
            "name": srs.GetLinearUnitsName(),
            "meters_per_unit": srs.GetLinearUnits(),
        },
        "spheroid": {
            "name": srs.GetAttrValue("SPHEROID"),
            "semi_major_axis": srs.GetSemiMajor(),
            "inverse_flattening": srs.GetInvFlattening(),
        },
        "projection_parameters": {
            "latitude_of_origin": srs.GetProjParm(
                osr.SRS_PP_LATITUDE_OF_ORIGIN
            ),
            "central_meridian": srs.GetProjParm(
                osr.SRS_PP_CENTRAL_MERIDIAN
            ),
            "scale_factor": srs.GetProjParm(
                osr.SRS_PP_SCALE_FACTOR
            ),
            "false_easting": srs.GetProjParm(
                osr.SRS_PP_FALSE_EASTING
            ),
            "false_northing": srs.GetProjParm(
                osr.SRS_PP_FALSE_NORTHING
            ),
        },
    }


def extract_band_info(dataset: gdal.Dataset) -> list[dict[str, Any]]:
    bands = []

    for index in range(1, dataset.RasterCount + 1):
        band = dataset.GetRasterBand(index)

        stats = band.GetStatistics(True, True)

        bands.append({
            "index": index,
            "description": band.GetDescription(),
            "data_type": gdal.GetDataTypeName(band.DataType),
            "color_interpretation": (
                gdal.GetColorInterpretationName(
                    band.GetColorInterpretation()
                )
            ),
            "nodata": band.GetNoDataValue(),
            "statistics": {
                "min": stats[0] if stats else None,
                "max": stats[1] if stats else None,
                "mean": stats[2] if stats else None,
                "stddev": stats[3] if stats else None,
            },
            "scale": band.GetScale(),
            "offset": band.GetOffset(),
            "unit_type": band.GetUnitType(),
            "metadata": band.GetMetadata(),
            "category_names": band.GetCategoryNames(),
        })

    return bands


# =============================================================================
# CORNER EXTRACTION
# =============================================================================

def pixel_to_world(
    gt: tuple[float, ...],
    px: float,
    py: float,
) -> tuple[float, float]:
    x = gt[0] + px * gt[1] + py * gt[2]
    y = gt[3] + px * gt[4] + py * gt[5]

    return x, y


def get_corner_coordinates(
    dataset: gdal.Dataset,
) -> dict[str, CornerCoordinate]:
    gt = dataset.GetGeoTransform()

    source_srs = build_spatial_reference(dataset)

    if source_srs is None:
        raise ValueError("Dataset has no projection.")

    transform = create_coordinate_transform(source_srs)

    width = dataset.RasterXSize
    height = dataset.RasterYSize

    corners = {
        "upper_left": (0, 0),
        "lower_left": (0, height),
        "upper_right": (width, 0),
        "lower_right": (width, height),
        "center": (width / 2, height / 2),
    }

    results = {}

    for name, (px, py) in corners.items():
        x, y = pixel_to_world(gt, px, py)

        lon, lat, _ = transform.TransformPoint(x, y)

        results[name] = CornerCoordinate(
            pixel_x=px,
            pixel_y=py,
            projected_x=x,
            projected_y=y,
            longitude=lon,
            latitude=lat,
        )

    return results


# =============================================================================
# MAIN EXTRACTION
# =============================================================================

def extract_dataset_info(path: str) -> dict[str, Any]:
    dataset = open_dataset(path)

    info = {
        "file": path,
        "raster_size": {
            "width": dataset.RasterXSize,
            "height": dataset.RasterYSize,
            "bands": dataset.RasterCount,
        },
        "metadata": extract_metadata(dataset),
        "geotransform": extract_geotransform(dataset),
        "bands": extract_band_info(dataset),
    }

    srs = build_spatial_reference(dataset)

    if srs:
        info["projection"] = extract_projection_info(srs)

    info["corners"] = {
        key: asdict(value)
        for key, value in get_corner_coordinates(dataset).items()
    }

    return info


# =============================================================================
# DISPLAY
# =============================================================================

def print_corner_info(corners: dict[str, dict[str, Any]]) -> None:
    for name, corner in corners.items():
        lon_dms = to_dms(corner["longitude"], is_latitude=False)
        lat_dms = to_dms(corner["latitude"], is_latitude=True)

        print(
            f"{name:12} "
            f"({corner['projected_x']:.3f}, {corner['projected_y']:.3f}) "
            f"({lon_dms}, {lat_dms})"
        )


# =============================================================================
# ENTRYPOINT
# =============================================================================

if __name__ == "__main__":
    FILE_PATH = "FT_20240415_001838_3_BC0030VB0082.tif"

    dataset_info = extract_dataset_info(FILE_PATH)

    print_section("RASTER INFO")
    print_dict({
        "file": dataset_info["file"],
        "raster_size": dataset_info["raster_size"],
    })

    print_section("METADATA")
    print_dict(dataset_info["metadata"])

    print_section("PROJECTION")
    print_dict(dataset_info.get("projection", {}))

    print_section("GEOTRANSFORM")
    print_dict(dataset_info["geotransform"])

    print_section("CORNERS")
    print_corner_info(dataset_info["corners"])

    print_section("BANDS")

    for band in dataset_info["bands"]:
        print(f"\nBand {band['index']}")
        print_dict(band, indent=2)
