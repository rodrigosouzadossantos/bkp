from __future__ import annotations

import time
import xml.etree.ElementTree as ET
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
    # COMMENT PARSER (NEW)
    # =========================================================================

    def _parse_comment(self, comment: str | None) -> dict | None:
        if not comment:
            return None

        try:
            xml_start = comment.find("<image")
            xml_end = comment.rfind("</image>")

            if xml_start == -1 or xml_end == -1:
                return {"raw": comment}

            xml_str = comment[xml_start: xml_end + len("</image>")]

            root = ET.fromstring(xml_str)

            def node_to_dict(node):
                result = {}

                # attributes
                for k, v in node.attrib.items():
                    result[k] = v

                # children
                for child in node:
                    child_dict = node_to_dict(child)

                    for ck, cv in child_dict.items():
                        if ck in result and isinstance(result[ck], dict) and isinstance(cv, dict):
                            result[ck].update(cv)
                        else:
                            result[ck] = cv

                if not result and node.text:
                    return {node.tag: node.text.strip()}

                return {node.tag: result}

            return node_to_dict(root)

        except Exception:
            return {"raw": comment}

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
                                            StructField("parsed_comment",
                                                        StringType(),
                                                        True),
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
    # METADATA (FIXED COMMENT HANDLING)
    # =========================================================================

    def get_metadata(self) -> dict[str, Any]:
        domains = []

        for domain in self.dataset.GetMetadataDomainList() or []:
            metadata = self.dataset.GetMetadata(domain)

            entries = []

            for key, value in metadata.items():

                if str(key).upper() == "COMMENT":
                    parsed_comment = self._parse_comment(str(value))

                    entries.append({
                        "key": str(key),
                        "value": str(value),   # KEEP RAW (TIFF SAFE)
                        "parsed_comment": parsed_comment,  # STRUCT ONLY HERE
                    })

                else:
                    entries.append({
                        "key": str(key),
                        "value": str(value),
                        "parsed_comment": None,
                    })

            domains.append({
                "domain": str(domain),
                "entries": entries,
            })

        return {
            "domains": domains,
        }

    # =========================================================================
    # REST (UNCHANGED EXCEPT SAFETY)
    # =========================================================================

    def get_raster_size(self) -> dict[str, int]:
        return {
            "width": int(self.dataset.RasterXSize),
            "height": int(self.dataset.RasterYSize),
            "bands": int(self.dataset.RasterCount),
        }

    def get_geotransform_info(self) -> dict[str, Any]:
        gt = self.geotransform

        if gt is None:
            return {
                "origin": {"x": None, "y": None},
                "pixel_size": {"width": None, "height": None},
                "rotation": {"x": None, "y": None},
            }

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

    def get_projection_info(self) -> dict[str, Any]:
        if self.srs is None:
            return {}

        return {
            "projected_cs": self.srs.GetAttrValue("PROJCS"),
            "geographic_cs": self.srs.GetAttrValue("GEOGCS"),
            "datum": self.srs.GetAttrValue("DATUM"),
            "projection": self.srs.GetAttrValue("PROJECTION"),
            "epsg": self.srs.GetAuthorityCode(None),
        }

    def get_band_info(self) -> list[dict[str, Any]]:
        bands = []

        for index in range(1, self.dataset.RasterCount + 1):
            band = self.dataset.GetRasterBand(index)
            stats = band.GetStatistics(True, True)

            bands.append({
                "index": index,
                "description": band.GetDescription(),
                "data_type": gdal.GetDataTypeName(band.DataType),
                "color_interpretation": gdal.GetColorInterpretationName(
                    band.GetColorInterpretation()
                ),
                "nodata": band.GetNoDataValue(),
                "min": stats[0] if stats else None,
                "max": stats[1] if stats else None,
                "mean": stats[2] if stats else None,
                "stddev": stats[3] if stats else None,
            })

        return bands

    # =========================================================================
    # COORDINATES (UNCHANGED)
    # =========================================================================

    def _create_coordinate_transform(self):
        if self.srs is None:
            return None

        target_srs = osr.SpatialReference()
        target_srs.ImportFromEPSG(4326)

        target_srs.SetAxisMappingStrategy(
            osr.OAMS_TRADITIONAL_GIS_ORDER
        )

        return osr.CoordinateTransformation(self.srs, target_srs)

    def pixel_to_world(self, pixel_x: float, pixel_y: float):
        gt = self.geotransform

        if gt is None:
            return 0.0, 0.0

        x = gt[0] + pixel_x * gt[1] + pixel_y * gt[2]
        y = gt[3] + pixel_x * gt[4] + pixel_y * gt[5]

        return float(x), float(y)

    def get_corner_coordinates(self):
        transform = self._create_coordinate_transform()

        width = float(self.dataset.RasterXSize)
        height = float(self.dataset.RasterYSize)

        corners = {
            "upper_left": (0.0, 0.0),
            "lower_left": (0.0, height),
            "upper_right": (width, 0.0),
            "lower_right": (width, height),
            "center": (width / 2, height / 2),
        }

        results = {}

        for name, (px, py) in corners.items():
            x, y = self.pixel_to_world(px, py)

            lon, lat = None, None
            if transform:
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

    def get_corner_coordinates_as_rows(self):
        corners = self.get_corner_coordinates()

        return [
            {"name": name, **asdict(c)}
            for name, c in corners.items()
        ]

    # =========================================================================
    # SAFE CAST HELPERS
    # =========================================================================

    @staticmethod
    def _safe_float(value: Any) -> float | None:
        return None if value is None else float(value)

    @staticmethod
    def _safe_str(value: Any) -> str | None:
        return None if value is None else str(value)


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
    df.show(truncate=False,vertical=True)
