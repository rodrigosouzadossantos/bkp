from __future__ import annotations

import time
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass
from typing import Any

from osgeo import gdal, osr
from pyspark.sql import DataFrame, SparkSession
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

    def __init__(self, spark: SparkSession, file_path: str):
        self.spark = spark
        self.file_path = file_path

        self.dataset = self._open_dataset()
        self.geotransform = self.dataset.GetGeoTransform()
        self.srs = self._build_spatial_reference()

    # =========================================================================
    # INIT
    # =========================================================================

    def _open_dataset(self):
        ds = gdal.Open(self.file_path)
        if ds is None:
            raise FileNotFoundError(self.file_path)
        return ds

    def _build_spatial_reference(self):
        proj = self.dataset.GetProjection()
        if not proj:
            return None
        srs = osr.SpatialReference()
        srs.ImportFromWkt(proj)
        return srs

    # =========================================================================
    # COMMENT PARSER → TELEMETRY FLATTENER
    # =========================================================================

    def _parse_comment(self, comment: str | None) -> dict | None:
        if not comment:
            return None

        try:
            start = comment.find("<image")
            end = comment.rfind("</image>")

            if start == -1 or end == -1:
                return {"raw_comment": comment}

            xml_str = comment[start:end + len("</image>")]
            root = ET.fromstring(xml_str)

            out = {"raw_comment": comment}

            # -------- IMAGE ATTRIBUTES --------
            if root.attrib:
                out["acq_time"] = root.attrib.get("time")
                out["acq_date"] = root.attrib.get("date")
                out["acq_index"] = root.attrib.get("acq_index")

            # -------- POSITION --------
            pos = root.find(".//Position")
            if pos is not None:

                coords = pos.find("Coords")
                if coords is not None:
                    out["lon"] = self._safe_float(coords.attrib.get("long"))
                    out["lat"] = self._safe_float(coords.attrib.get("lat"))

                depth = pos.find("Depth")
                if depth is not None:
                    out["altitude"] = self._safe_float(depth.attrib.get("altitude"))
                    out["depth"] = self._safe_float(depth.attrib.get("depth"))

                direction = pos.find("Direction")
                if direction is not None:
                    out["pitch"] = self._safe_float(direction.attrib.get("pitch"))
                    out["roll"] = self._safe_float(direction.attrib.get("roll"))
                    out["yaw"] = self._safe_float(direction.attrib.get("yaw"))

            return out

        except Exception:
            return {"raw_comment": comment}

    # =========================================================================
    # SCHEMA
    # =========================================================================

    @property
    def schema(self) -> StructType:
        return StructType([
            StructField("file_path", StringType(), False),

            StructField("raster_size", StructType([
                StructField("width", IntegerType()),
                StructField("height", IntegerType()),
                StructField("bands", IntegerType()),
            ])),

            StructField("telemetry", StructType([
                StructField("acq_time", StringType()),
                StructField("acq_date", StringType()),
                StructField("acq_index", StringType()),
                StructField("lon", DoubleType()),
                StructField("lat", DoubleType()),
                StructField("altitude", DoubleType()),
                StructField("depth", DoubleType()),
                StructField("pitch", DoubleType()),
                StructField("roll", DoubleType()),
                StructField("yaw", DoubleType()),
                StructField("raw_comment", StringType()),
            ])),

            StructField("corners", ArrayType(StructType([
                StructField("name", StringType()),
                StructField("pixel_x", DoubleType()),
                StructField("pixel_y", DoubleType()),
                StructField("projected_x", DoubleType()),
                StructField("projected_y", DoubleType()),
                StructField("longitude", DoubleType()),
                StructField("latitude", DoubleType()),
            ]))),

            StructField("ingestion_timestamp", LongType()),
        ])

    # =========================================================================
    # PUBLIC API
    # =========================================================================

    def inspect(self) -> dict[str, Any]:
        return {
            "file_path": self.file_path,
            "raster_size": {
                "width": int(self.dataset.RasterXSize),
                "height": int(self.dataset.RasterYSize),
                "bands": int(self.dataset.RasterCount),
            },
            "telemetry": self._extract_telemetry(),
            "corners": self.get_corner_coordinates_as_rows(),
            "ingestion_timestamp": int(time.time()),
        }

    def to_spark_df(self) -> DataFrame:
        return self.spark.createDataFrame([self.inspect()], self.schema)

    # =========================================================================
    # TELEMETRY EXTRACTION
    # =========================================================================

    def _extract_telemetry(self) -> dict | None:
        domains = self.dataset.GetMetadataDomainList() or []

        for d in domains:
            md = self.dataset.GetMetadata(d)

            for k, v in md.items():
                if str(k).upper() == "COMMENT":
                    return self._parse_comment(str(v))

        return None

    # =========================================================================
    # CORNERS
    # =========================================================================

    def pixel_to_world(self, px, py):
        gt = self.geotransform
        x = gt[0] + px * gt[1] + py * gt[2]
        y = gt[3] + px * gt[4] + py * gt[5]
        return float(x), float(y)

    def get_corner_coordinates(self):
        width = float(self.dataset.RasterXSize)
        height = float(self.dataset.RasterYSize)

        corners = {
            "upper_left": (0, 0),
            "lower_left": (0, height),
            "upper_right": (width, 0),
            "lower_right": (width, height),
            "center": (width / 2, height / 2),
        }

        return [
            {
                "name": k,
                "pixel_x": float(px),
                "pixel_y": float(py),
                "projected_x": float(self.pixel_to_world(px, py)[0]),
                "projected_y": float(self.pixel_to_world(px, py)[1]),
                "longitude": None,
                "latitude": None,
            }
            for k, (px, py) in corners.items()
        ]

    def get_corner_coordinates_as_rows(self):
        return self.get_corner_coordinates()

    # =========================================================================
    # SAFE CAST
    # =========================================================================

    @staticmethod
    def _safe_float(v):
        try:
            return float(v)
        except Exception:
            return None



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
        #file_path="FT_20241016_062303_6_BC0030VB0153.jpg",
        #file_path="FT_20240415_225635_6_BC0030VB0083.tif",
        file_path="FT_20240415_150151_6_BC0030VB0082.tif",
    )

    print("\nSCHEMA")
    print(inspector.schema.simpleString())

    df = inspector.to_spark_df()

    print("\nDATAFRAME SCHEMA")
    df.printSchema()

    print("\nDATAFRAME CONTENT")
    df.show(truncate=False,vertical=True)
