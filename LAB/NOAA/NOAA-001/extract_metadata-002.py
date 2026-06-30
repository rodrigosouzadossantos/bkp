from typing import Any, Dict, List
from pyspark.sql import SparkSession
from pyspark.sql.types import StructType, StructField, StringType
from exiftool import ExifToolHelper

import xml.etree.ElementTree as ET


# ----------------------------
# normalize key into path
# ----------------------------
def key_to_path(key: str) -> List[str]:
    return [
        part.strip()
        for part in key.replace(":", "_").split("_")
        if part.strip()
    ]


# ----------------------------
# insert value into nested dict
# ----------------------------
def insert_nested(dct: Dict, path: List[str], value: Any):
    #for p in path[:-1]:
    #    d = d.setdefault(p, {})
    #d[path[-1]] = value
    key = path[0]

    if len(path) == 1:
        dct[key] = value
        return

    if key not in dct or not isinstance(dct[key], dict):
        dct[key] = {}

    insert_nested(dct[key], path[1:], value)


# ----------------------------
# convert nested dict → spark schema
# ----------------------------
def dict_to_schema(d: Dict) -> StructType:
    fields = []
    for k, v in d.items():
        if isinstance(v, dict):
            fields.append(StructField(k, dict_to_schema(v), True))
        else:
            fields.append(StructField(k, StringType(), True))
    return StructType(fields)


# ----------------------------
# convert dict → row-friendly dict
# ----------------------------
def dict_to_row(d: Dict) -> Dict:
    out = {}
    for k, v in d.items():
        if isinstance(v, dict):
            out[k] = dict_to_row(v)
        else:
            out[k] = str(v)
    return out


def flatten_xml(element, prefix="", output=None):
    """
    Flatten XML recursively into a flat dict.
    """

    if output is None:
        output = {}

    current = f"{prefix}_{element.tag}" if prefix else element.tag

    # attributes
    for attr_name, attr_value in element.attrib.items():
        key = f"{current}_{attr_name}"
        output[key] = attr_value

    # text value
    text = (element.text or "").strip()

    if text:
        output[current] = text

    # children
    for child in element:
        flatten_xml(child, current, output)

    return output


def detect_xml_fields(metadata):
    """
    Dynamically detect metadata fields containing XML.
    """

    xml_fields = []

    for key, value in metadata.items():

        if not isinstance(value, str):
            continue

        value = value.strip()

        # Fast XML heuristic
        if not value.startswith("<"):
            continue

        if ">" not in value:
            continue

        try:
            ET.fromstring(value)
            xml_fields.append(key)

        except Exception:
            pass

    return xml_fields


def parse_xml_comments(metadata):
    """
    Parse XML embedded in comments.
    """

    parsed = {}

    xml_fields = detect_xml_fields(metadata)

    for field in xml_fields:

        raw = metadata[field]

        if not raw:
            continue

        try:
            root = ET.fromstring(raw)

            xml_data = flatten_xml(root)

            for k, v in xml_data.items():
                parsed[f"{field}_{k}"] = v

        except Exception:
            # ignore malformed XML
            pass

    return parsed, xml_fields


# ----------------------------
# extract metadata
# ----------------------------
def extract_metadata(image_path: str):
    structured = {}

    with ExifToolHelper() as et:
        metadata = et.get_metadata(
            image_path,
            params=[
                "-a",
                "-u",
                "-G1",
                "-n",
            ],
        )[0]

    # Parse embedded XML
    xml_metadata, xml_fields = parse_xml_comments(metadata)

    # Merge XML into metadata
    metadata.update(xml_metadata)

    for f in xml_fields:
        metadata.pop(f, None)

    for key, value in metadata.items():
        path = key_to_path(key)
        insert_nested(structured, path, value)

    return structured


# ----------------------------
# main
# ----------------------------
if __name__ == "__main__":
    spark = SparkSession.builder.appName("ExifToolNested").getOrCreate()

    #image_file = "/root/LAB/NOAA/FT_20241016_062303_6_BC0030VB0153.jpg"
    image_file = "/root/LAB/NOAA/FT_20240415_001838_3_BC0030VB0082.tif"

    structured = extract_metadata(image_file)

    row = dict_to_row(structured)
    schema = dict_to_schema(structured)

    df = spark.createDataFrame([row], schema=schema)

    print("\n========== SCHEMA ==========\n")
    df.printSchema()

    print("\n========== DATA ==========\n")
    #df.show(truncate=False,vertical=True)


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

    print_schema_like(df, 1)
