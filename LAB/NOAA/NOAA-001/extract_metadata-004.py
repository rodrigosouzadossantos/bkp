from typing import Any, Dict, List, Tuple
from pyspark.sql import SparkSession
from pyspark.sql.types import StructType, StructField, StringType
from exiftool import ExifToolHelper
import xml.etree.ElementTree as ET


class ExifMetadataProcessor:
    def __init__(self, spark: SparkSession):
        self.spark = spark

    # ----------------------------
    # key normalization
    # ----------------------------
    @staticmethod
    def key_to_path(key: str) -> List[str]:
        return [
            part.strip()
            for part in key.replace(":", "_").split("_")
            if part.strip()
        ]

    # ----------------------------
    # nested dict insertion
    # ----------------------------
    @staticmethod
    def insert_nested(dct: Dict, path: List[str], value: Any):
        key = path[0]

        if len(path) == 1:
            dct[key] = value
            return

        if key not in dct or not isinstance(dct[key], dict):
            dct[key] = {}

        ExifMetadataProcessor.insert_nested(dct[key], path[1:], value)

    # ----------------------------
    # dict → Spark schema
    # ----------------------------
    @staticmethod
    def dict_to_schema(d: Dict) -> StructType:
        fields = []
        for k, v in d.items():
            if isinstance(v, dict):
                fields.append(StructField(k, ExifMetadataProcessor.dict_to_schema(v), True))
            else:
                fields.append(StructField(k, StringType(), True))
        return StructType(fields)

    # ----------------------------
    # dict → Spark row
    # ----------------------------
    @staticmethod
    def dict_to_row(d: Dict) -> Dict:
        out = {}
        for k, v in d.items():
            if isinstance(v, dict):
                out[k] = ExifMetadataProcessor.dict_to_row(v)
            else:
                out[k] = str(v)
        return out

    # ----------------------------
    # XML flattening
    # ----------------------------
    @staticmethod
    def flatten_xml(element, prefix="", output=None):
        if output is None:
            output = {}

        current = f"{prefix}_{element.tag}" if prefix else element.tag

        for attr_name, attr_value in element.attrib.items():
            output[f"{current}_{attr_name}"] = attr_value

        text = (element.text or "").strip()
        if text:
            output[current] = text

        for child in element:
            ExifMetadataProcessor.flatten_xml(child, current, output)

        return output

    # ----------------------------
    # XML detection
    # ----------------------------
    @staticmethod
    def detect_xml_fields(metadata: Dict) -> List[str]:
        xml_fields = []

        for key, value in metadata.items():
            if not isinstance(value, str):
                continue

            value = value.strip()

            if not value.startswith("<") or ">" not in value:
                continue

            try:
                ET.fromstring(value)
                xml_fields.append(key)
            except Exception:
                pass

        return xml_fields

    # ----------------------------
    # XML parsing in metadata
    # ----------------------------
    @staticmethod
    def parse_xml_comments(metadata: Dict) -> Tuple[Dict, List[str]]:
        parsed = {}
        xml_fields = ExifMetadataProcessor.detect_xml_fields(metadata)

        for field in xml_fields:
            raw = metadata.get(field)
            if not raw:
                continue

            try:
                root = ET.fromstring(raw)
                xml_data = ExifMetadataProcessor.flatten_xml(root)

                for k, v in xml_data.items():
                    parsed[f"{field}_{k}"] = v

            except Exception:
                pass

        return parsed, xml_fields

    # ----------------------------
    # main extraction
    # ----------------------------
    def extract_metadata(self, image_path: str) -> Dict:
        structured = {}

        #with ExifToolHelper() as et:
        #    metadata = et.get_metadata(
        #        image_path,
        #        params=["-a", "-u", "-G1", "-n"],
        #    )[0]

        import subprocess
        import json

        metadata =  json.loads(subprocess.run(
            [
                "exiftool",
                "-json",
                "-G1",
                "-struct",
                "-n",
                image_path,
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True
        ).stdout.decode("utf-8"))[0]


        xml_metadata, xml_fields = self.parse_xml_comments(metadata)
        metadata.update(xml_metadata)

        for f in xml_fields:
            metadata.pop(f, None)

        for key, value in metadata.items():
            path = self.key_to_path(key)
            self.insert_nested(structured, path, value)

        return structured

    # ----------------------------
    # build Spark DataFrame
    # ----------------------------
    def build_dataframe(self, image_path: str):
        structured = self.extract_metadata(image_path)

        row = self.dict_to_row(structured)
        schema = self.dict_to_schema(structured)

        self.df = self.spark.createDataFrame([row], schema=schema)
        return self.df, structured

    # ----------------------------
    # pretty print schema-like view
    # ----------------------------
    @staticmethod
    def print_schema_like(df, n=1):
        row = df.take(n)[0].asDict(recursive=True)

        def recurse(d, indent=0):
            for k, v in d.items():
                prefix = " |    " * indent + " |-- "
                if isinstance(v, dict):
                    print(f"{prefix}{k}:")
                    recurse(v, indent + 1)
                else:
                    print(f"{prefix}{k}: {v}")

        recurse(row)

    def __str__(self):
        # Assumes 'self.df' is available within the class
        row = self.df.take(1)[0].asDict(recursive=True)
        lines = []

        def recurse(d, indent=0):
            for k, v in d.items():
                prefix = " |    " * indent + " |-- "
                if isinstance(v, dict):
                    lines.append(f"{prefix}{k}:")
                    recurse(v, indent + 1)
                else:
                    lines.append(f"{prefix}{k}: {v}")

        recurse(row)
        return "\n".join(lines)



if __name__ == "__main__":
    spark = SparkSession.builder.appName("ExifToolNested").getOrCreate()

    processor = ExifMetadataProcessor(spark)

    image_file = "/root/LAB/NOAA/FT_20240415_001838_3_BC0030VB0082.tif"
    image_file = "/root/LAB/NOAA/FT_20241016_062303_6_BC0030VB0153.jpg"
    image_file = "FT_20240415_150151_6_BC0030VB0082.tif"

    df, structured = processor.build_dataframe(image_file)

    print("\n========== SCHEMA ==========\n")
    df.printSchema()

    print("\n========== DATA ==========\n")
    #ExifMetadataProcessor.print_schema_like(df)
    print(processor)
