from __future__ import annotations

import time
from dataclasses import asdict, dataclass
from typing import Any

from osgeo import gdal, osr
from pyspark.sql import DataFrame, Row, SparkSession
from pyspark.sql.types import (
    ArrayType,
    DoubleType,
    IntegerType,
    LongType,
    StringType,
    StructField,
    StructType,
)

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
    """
    Inspect GDAL raster datasets and return structured Spark DataFrames.
    """

    def __init__(
        self,
        spark: SparkSession,
        file_path: str,
    ):
        self.spark = spark
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
    # SCHEMA
    # =========================================================================

    @property
    def schema(self) -> StructType:
        return StructType([
            StructField("file_path", StringType(), False),

            StructField(
                "raster_size",
                StructType([
                    StructField("width", IntegerType()),
                    StructField("height", IntegerType()),
                    StructField("bands", IntegerType()),
                ]),
            ),

            StructField(
                "metadata",
                StructType([
                    StructField(
                        "domains",
                        ArrayType(
                            StructType([
                                StructField("domain", StringType()),
                                StructField(
                                    "entries",
                                    ArrayType(
                                        StructType([
                                            StructField("key", StringType()),
                                            StructField("value", StringType()),
                                        ])
                                    ),
                                ),
                            ])
                        ),
                    ),
                ]),
            ),

            StructField(
                "geotransform",
                StructType([
                    StructField(
                        "origin",
                        StructType([
                            StructField("x", DoubleType()),
                            StructField("y", DoubleType()),
                        ]),
                    ),
                    StructField(
                        "pixel_size",
                        StructType([
                            StructField("width", DoubleType()),
                            StructField("height", DoubleType()),
                        ]),
                    ),
                    StructField(
                        "rotation",
                        StructType([
                            StructField("x", DoubleType()),
                            StructField("y", DoubleType()),
                        ]),
                    ),
                ]),
            ),

            StructField(
                "projection",
                StructType([
                    StructField("projected_cs", StringType()),
                    StructField("geographic_cs", StringType()),
                    StructField("datum", StringType()),
                    StructField("projection", StringType()),
                    StructField("epsg", StringType()),
                ]),
            ),

            StructField(
                "corners",
                ArrayType(
                    StructType([
                        StructField("name", StringType()),
                        StructField("pixel_x", DoubleType()),
                        StructField("pixel_y", DoubleType()),
                        StructField("projected_x", DoubleType()),
                        StructField("projected_y", DoubleType()),
                        StructField("longitude", DoubleType()),
                        StructField("latitude", DoubleType()),
                    ])
                ),
            ),

            StructField(
                "bands",
                ArrayType(
                    StructType([
                        StructField("index", IntegerType()),
                        StructField("description", StringType()),
                        StructField("data_type", StringType()),
                        StructField("color_interpretation", StringType()),
                        StructField("nodata", DoubleType()),
                        StructField("min", DoubleType()),
                        StructField("max", DoubleType()),
                        StructField("mean", DoubleType()),
                        StructField("stddev", DoubleType()),
                    ])
                ),
            ),

            StructField("ingestion_timestamp", LongType()),
        ])

    # =========================================================================
    # PUBLIC API
    # =========================================================================

    def inspect(self) -> dict[str, Any]:
        return {
            "file_path": self.file_path,
            "raster_size": self.get_raster_size(),
            "metadata": self.get_metadata(),
            "geotransform": self.get_geotransform_info(),
            "projection": self.get_projection_info(),
            "corners": self.get_corner_coordinates_as_rows(),
            "bands": self.get_band_info(),
            "ingestion_timestamp": int(time.time()),
        }

    def to_spark_df(self) -> DataFrame:
        data = [self.inspect()]

        return self.spark.createDataFrame(
            data=data,
            schema=self.schema,
        )

    # =========================================================================
    # METADATA
    # =========================================================================

    def get_metadata(self) -> dict[str, Any]:
        domains = []

        for domain in self.dataset.GetMetadataDomainList() or []:
            metadata = self.dataset.GetMetadata(domain)

            entries = []

            for key, value in metadata.items():
                entries.append({
                    "key": str(key),
                    "value": str(value),
                })

            domains.append({
                "domain": str(domain),
                "entries": entries,
            })

        return {
            "domains": domains,
        }

    # =========================================================================
    # RASTER
    # =========================================================================

    def get_raster_size(self) -> dict[str, int]:
        return {
            "width": int(self.dataset.RasterXSize),
            "height": int(self.dataset.RasterYSize),
            "bands": int(self.dataset.RasterCount),
        }

    def get_geotransform_info(self) -> dict[str, Any]:
        gt = self.geotransform

        return {
            "origin": {
                "x": float(gt[0]),
                "y": float(gt[3]),
            },
            "pixel_size": {
                "width": float(gt[1]),
                "height": float(gt[5]),
            },
            "rotation": {
                "x": float(gt[2]),
                "y": float(gt[4]),
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
            "projected_cs": self._safe_str(
                srs.GetAttrValue("PROJCS")
            ),
            "geographic_cs": self._safe_str(
                srs.GetAttrValue("GEOGCS")
            ),
            "datum": self._safe_str(
                srs.GetAttrValue("DATUM")
            ),
            "projection": self._safe_str(
                srs.GetAttrValue("PROJECTION")
            ),
            "epsg": self._safe_str(
                srs.GetAuthorityCode(None)
            ),
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
                "index": int(index),
                "description": self._safe_str(
                    band.GetDescription()
                ),
                "data_type": str(
                    gdal.GetDataTypeName(band.DataType)
                ),
                "color_interpretation": str(
                    gdal.GetColorInterpretationName(
                        band.GetColorInterpretation()
                    )
                ),
                "nodata": self._safe_float(
                    band.GetNoDataValue()
                ),
                "min": self._safe_float(
                    stats[0] if stats else None
                ),
                "max": self._safe_float(
                    stats[1] if stats else None
                ),
                "mean": self._safe_float(
                    stats[2] if stats else None
                ),
                "stddev": self._safe_float(
                    stats[3] if stats else None
                ),
            })

        return bands

    # =========================================================================
    # COORDINATES
    # =========================================================================

    def _create_coordinate_transform(
        self,
    ) -> osr.CoordinateTransformation:
        if self.srs is None:
            raise ValueError(
                "Dataset has no spatial reference."
            )

        target_srs = osr.SpatialReference()
        target_srs.ImportFromEPSG(4326)

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

        return float(x), float(y)

    def get_corner_coordinates(
        self,
    ) -> dict[str, CornerCoordinate]:
        transform = self._create_coordinate_transform()

        width = float(self.dataset.RasterXSize)
        height = float(self.dataset.RasterYSize)

        corners = {
            "upper_left": (0.0, 0.0),
            "lower_left": (0.0, height),
            "upper_right": (width, 0.0),
            "lower_right": (width, height),
            "center": (width / 2.0, height / 2.0),
        }

        results = {}

        for name, (px, py) in corners.items():
            x, y = self.pixel_to_world(px, py)

            lon, lat, _ = transform.TransformPoint(x, y)

            results[name] = CornerCoordinate(
                pixel_x=float(px),
                pixel_y=float(py),
                projected_x=float(x),
                projected_y=float(y),
                longitude=float(lon),
                latitude=float(lat),
            )

        return results

    def get_corner_coordinates_as_rows(
        self,
    ) -> list[dict[str, Any]]:
        corners = self.get_corner_coordinates()

        return [
            {
                "name": str(name),
                **asdict(coord),
            }
            for name, coord in corners.items()
        ]

    # =========================================================================
    # SAFE CAST HELPERS
    # =========================================================================

    @staticmethod
    def _safe_float(value: Any) -> float | None:
        if value is None:
            return None

        return float(value)

    @staticmethod
    def _safe_str(value: Any) -> str | None:
        if value is None:
            return None

        return str(value)


# =============================================================================
# EXAMPLE USAGE
# =============================================================================

if __name__ == "__main__":
    spark = (
        SparkSession.builder
        .appName("RasterInspector")
        .getOrCreate()
    )

    inspector = RasterInspector(
        spark=spark,
        #file_path="FT_20240415_001838_3_BC0030VB0082.tif",
        file_path="FT_20241016_062303_6_BC0030VB0153.jpg",
    )

    print("\nSCHEMA")
    print(inspector.schema.simpleString())

    df = inspector.to_spark_df()

    print("\nDATAFRAME SCHEMA")
    df.printSchema()

    print("\nDATAFRAME CONTENT")
    df.show(truncate=False)
