from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any

from osgeo import gdal, osr

gdal.UseExceptions()


# =============================================================================
# DATA MODELS
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
# MAIN CLASS
# =============================================================================

class RasterInspector:
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.dataset = self._open_dataset()

        self.geotransform = self.dataset.GetGeoTransform()
        self.srs = self._build_spatial_reference()

    # =========================================================================
    # INITIALIZATION
    # =========================================================================

    def _open_dataset(self) -> gdal.Dataset:
        dataset = gdal.Open(self.file_path)

        if dataset is None:
            raise FileNotFoundError(
                f"Unable to open dataset: {self.file_path}"
            )

        return dataset

    def _build_spatial_reference(
        self,
    ) -> osr.SpatialReference | None:
        projection = self.dataset.GetProjection()

        if not projection:
            return None

        srs = osr.SpatialReference()
        srs.ImportFromWkt(projection)

        return srs

    # =========================================================================
    # PUBLIC API
    # =========================================================================

    def inspect(self) -> dict[str, Any]:
        info = {
            "file": self.file_path,
            "raster_size": self.get_raster_size(),
            "metadata": self.get_metadata(),
            "geotransform": self.get_geotransform_info(),
            "bands": self.get_band_info(),
        }

        if self.srs:
            info["projection"] = self.get_projection_info()

        info["corners"] = {
            key: asdict(value)
            for key, value in self.get_corner_coordinates().items()
        }

        return info

    # =========================================================================
    # METADATA
    # =========================================================================

    def get_metadata(self) -> dict[str, dict[str, str]]:
        metadata = {}

        for domain in self.dataset.GetMetadataDomainList() or []:
            metadata[domain] = self.dataset.GetMetadata(domain)

        return metadata

    # =========================================================================
    # RASTER
    # =========================================================================

    def get_raster_size(self) -> dict[str, int]:
        return {
            "width": self.dataset.RasterXSize,
            "height": self.dataset.RasterYSize,
            "bands": self.dataset.RasterCount,
        }

    def get_geotransform_info(self) -> dict[str, Any]:
        gt = self.geotransform

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

    # =========================================================================
    # PROJECTION
    # =========================================================================

    def get_projection_info(self) -> dict[str, Any]:
        if self.srs is None:
            return {}

        srs = self.srs

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

    # =========================================================================
    # BANDS
    # =========================================================================

    def get_band_info(self) -> list[dict[str, Any]]:
        bands = []

        for index in range(1, self.dataset.RasterCount + 1):
            band = self.dataset.GetRasterBand(index)

            stats = band.GetStatistics(True, True)

            bands.append({
                "index": index,
                "description": band.GetDescription(),
                "data_type": gdal.GetDataTypeName(
                    band.DataType
                ),
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

    # =========================================================================
    # COORDINATES
    # =========================================================================

    def _create_coordinate_transform(
        self,
    ) -> osr.CoordinateTransformation:
        if self.srs is None:
            raise ValueError("Dataset has no spatial reference.")

        target_srs = osr.SpatialReference()
        target_srs.ImportFromEPSG(4326)

        # Ensure lon/lat order
        target_srs.SetAxisMappingStrategy(
            osr.OAMS_TRADITIONAL_GIS_ORDER
        )

        return osr.CoordinateTransformation(
            self.srs,
            target_srs,
        )

    def pixel_to_world(
        self,
        pixel_x: float,
        pixel_y: float,
    ) -> tuple[float, float]:
        gt = self.geotransform

        x = gt[0] + pixel_x * gt[1] + pixel_y * gt[2]
        y = gt[3] + pixel_x * gt[4] + pixel_y * gt[5]

        return x, y

    def get_corner_coordinates(
        self,
    ) -> dict[str, CornerCoordinate]:
        transform = self._create_coordinate_transform()

        width = self.dataset.RasterXSize
        height = self.dataset.RasterYSize

        corners = {
            "upper_left": (0, 0),
            "lower_left": (0, height),
            "upper_right": (width, 0),
            "lower_right": (width, height),
            "center": (width / 2, height / 2),
        }

        results = {}

        for name, (px, py) in corners.items():
            x, y = self.pixel_to_world(px, py)

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

    # =========================================================================
    # DISPLAY HELPERS
    # =========================================================================

    @staticmethod
    def to_dms(
        value: float,
        is_latitude: bool,
    ) -> str:
        abs_value = abs(value)

        degrees = int(abs_value)
        minutes = int((abs_value - degrees) * 60)
        seconds = round(
            (abs_value - degrees - minutes / 60) * 3600,
            2,
        )

        direction = (
            ("N" if value >= 0 else "S")
            if is_latitude
            else ("E" if value >= 0 else "W")
        )

        return (
            f"{degrees}°{minutes}'{seconds}\"{direction}"
        )

    @staticmethod
    def print_section(title: str) -> None:
        print("\n" + "=" * 80)
        print(title)
        print("=" * 80)

    @staticmethod
    def print_dict(
        data: dict[str, Any],
        indent: int = 0,
    ) -> None:
        prefix = " " * indent

        for key, value in data.items():
            if isinstance(value, dict):
                print(f"{prefix}{key}:")
                RasterInspector.print_dict(
                    value,
                    indent + 2,
                )
            else:
                print(f"{prefix}{key}: {value}")

    def print_summary(self) -> None:
        info = self.inspect()

        self.print_section("RASTER INFO")
        self.print_dict({
            "file": info["file"],
            "raster_size": info["raster_size"],
        })

        self.print_section("METADATA")
        self.print_dict(info["metadata"])

        self.print_section("PROJECTION")
        self.print_dict(info.get("projection", {}))

        self.print_section("GEOTRANSFORM")
        self.print_dict(info["geotransform"])

        self.print_section("CORNERS")

        for name, corner in info["corners"].items():
            lon_dms = self.to_dms(
                corner["longitude"],
                is_latitude=False,
            )

            lat_dms = self.to_dms(
                corner["latitude"],
                is_latitude=True,
            )

            print(
                f"{name:12} "
                f"({corner['projected_x']:.3f}, "
                f"{corner['projected_y']:.3f}) "
                f"({lon_dms}, {lat_dms})"
            )

        self.print_section("BANDS")

        for band in info["bands"]:
            print(f"\nBand {band['index']}")
            self.print_dict(band, indent=2)


# =============================================================================
# EXAMPLE USAGE
# =============================================================================

if __name__ == "__main__":
    inspector = RasterInspector(
        "FT_20240415_001838_3_BC0030VB0082.tif"
    )

    inspector.print_summary()

    # Full structured output
    data = inspector.inspect()
