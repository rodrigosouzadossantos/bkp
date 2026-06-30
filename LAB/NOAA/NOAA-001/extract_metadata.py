#!/usr/bin/env python3

from pathlib import Path
import xml.etree.ElementTree as ET

from exiftool import ExifToolHelper

from pyspark.sql import SparkSession
from pyspark.sql.types import (
    StructType,
    StructField,
    StringType,
    DoubleType,
    LongType,
    BooleanType,
)


def infer_type(value):

    if isinstance(value, dict):
        return build_schema(value)

    if isinstance(value, bool):
        return BooleanType()

    if isinstance(value, int):
        return LongType()

    if isinstance(value, float):
        return DoubleType()

    return StringType()

def clean_values(obj):

    if isinstance(obj, dict):
        return {k: clean_values(v) for k, v in obj.items()}

    if isinstance(obj, list):
        return [clean_values(v) for v in obj]

    return obj


def build_schema(obj):

    if isinstance(obj, dict):
        return StructType([
            StructField(k, build_schema(v), True)
            for k, v in obj.items()
        ])

    if isinstance(obj, bool):
        return BooleanType()

    if isinstance(obj, int):
        return LongType()

    if isinstance(obj, float):
        return DoubleType()

    return StringType()

def ___build_schema(obj):

    if isinstance(obj, dict):

        fields = []

        for k, v in obj.items():
            fields.append(
                StructField(
                    k,
                    build_schema(v),
                    True
                )
            )

        return StructType(fields)

    elif isinstance(obj, bool):
        return BooleanType()

    elif isinstance(obj, int):
        return LongType()

    elif isinstance(obj, float):
        return DoubleType()

    else:
        return StringType()

def _build_schema(dct):

    fields = []

    for key, value in dct.items():

        if isinstance(value, dict):
            fields.append(
                StructField(
                    key,
                    build_schema(value),
                    True
                )
            )
        else:
            fields.append(
                StructField(
                    key,
                    infer_type(value),
                    True
                )
            )

    return StructType(fields)

def normalize_dict(dct):

    if isinstance(dct, dict):

        return {
            k: normalize_dict(v)
            for k, v in dct.items()
        }

    return dct

def insert_path(tree, path, value):
    """
    Build nested dict from key path.
    """

    key = path[0]

    if len(path) == 1:
        tree[key] = value
        return

    if key not in tree or not isinstance(tree[key], dict):
        tree[key] = {}

    insert_path(tree[key], path[1:], value)


def to_nested(metadata):
    """
    Convert ExifTool flat dict into nested structure.
    """

    root = {}

    for key, value in metadata.items():

        # IMPORTANT: ExifTool uses ":" as hierarchy
        parts = key.split(":")

        insert_path(root, parts, value)

    return root

def insert_nested(dct, path, value):
    """
    Insert value into nested dict using path list.
    """
    key = path[0]

    if len(path) == 1:
        dct[key] = value
        return

    if key not in dct or not isinstance(dct[key], dict):
        dct[key] = {}

    insert_nested(dct[key], path[1:], value)


def build_nested_structure(metadata):
    """
    Convert flat ExifTool dict into nested structure.
    """

    root = {}

    for key, value in metadata.items():

        parts = key.split(":")

        insert_nested(root, parts, value)

    return root


def extract_metadata(file_path):
    """
    Extract metadata using pyexiftool.
    """

    file_path = str(Path(file_path).resolve())

    with ExifToolHelper() as et:
        metadata = et.get_metadata(
            file_path,
            params=[
                "-a",
                "-u",
                "-G1",
                "-n",
            ],
        )

    return metadata[0] if metadata else {}


def infer_spark_type(value):

    if isinstance(value, bool):
        return BooleanType()

    if isinstance(value, int):
        return LongType()

    if isinstance(value, float):
        return DoubleType()

    return StringType()


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


def normalize_metadata(metadata):

    normalized = {}

    for key, value in metadata.items():

        clean_key = (
            key.replace(":", "_")
               .replace("-", "_")
               .replace(" ", "_")
               .replace(".", "_")
        )

        if value is None:
            normalized[clean_key] = None

        elif isinstance(value, (str, int, float, bool)):
            normalized[clean_key] = value

        else:
            normalized[clean_key] = str(value)

    return normalized


def __build_schema(metadata):

    fields = []

    for key, value in metadata.items():

        fields.append(
            StructField(
                key,
                infer_spark_type(value),
                nullable=True,
            )
        )

    return StructType(fields)


if __name__ == "__main__":

    image_file = "FT_20241016_062303_6_BC0030VB0153.jpg"

    raw = extract_metadata(image_file)

    #metadata = normalize_metadata(raw_metadata)

    # Parse embedded XML
    xml_metadata, xml_fields = parse_xml_comments(raw)

    # Merge XML into metadata
    raw.update(xml_metadata)

    for f in xml_fields:
        raw.pop(f, None)

    # build nested structure
    #nested = build_nested_structure(raw)
    nested = to_nested(raw)

    nested = clean_values(nested)

    schema = build_schema(nested)

    spark = (
        SparkSession.builder
        .appName("ExifToolXMLMetadata")
        .getOrCreate()
    )

    df = spark.createDataFrame([nested], schema=schema)

    #df = spark.createDataFrame(
    #    [nested],
    #    schema=schema,
    #)

    print("\n========== SCHEMA ==========\n")
    df.printSchema()

    print("\n========== DATA ==========\n")
    df.show(
        truncate=False,
        vertical=True,
    )
