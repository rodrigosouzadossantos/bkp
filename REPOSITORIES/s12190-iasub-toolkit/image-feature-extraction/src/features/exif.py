from .base import FeatureExtractor

from typing import Any, Dict, List, Tuple
from exiftool import ExifToolHelper
import xml.etree.ElementTree as ET

import subprocess
import json


class ExifExtractor(FeatureExtractor):
  name = "exif"
  order = 4
  _schema = None

  def extract(self, ctx):
    content = ctx["content"]

    return {self.name: self.build_dataframe(content)}

  def schema(self):
    return self._schema

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

    ExifExtractor.insert_nested(dct[key], path[1:], value)

  # ----------------------------
  # dict → Spark row
  # ----------------------------
  @staticmethod
  def dict_to_row(d: Dict) -> Dict:
    out = {}
    for k, v in d.items():
      if isinstance(v, dict):
        out[k] = ExifExtractor.dict_to_row(v)
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
          ExifExtractor.flatten_xml(child, current, output)

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
      xml_fields = ExifExtractor.detect_xml_fields(metadata)

      for field in xml_fields:
          raw = metadata.get(field)
          if not raw:
              continue

          try:
              root = ET.fromstring(raw)
              xml_data = ExifExtractor.flatten_xml(root)

              for k, v in xml_data.items():
                  parsed[f"{field}_{k}"] = v

          except Exception:
              pass

      return parsed, xml_fields

  # ----------------------------
  # main extraction
  # ----------------------------
  def extract_metadata(self, raw: bytes) -> Dict:
      structured = {}

      #with ExifToolHelper() as et:
      #    metadata = et.get_metadata(
      #        image_path,
      #        params=["-a", "-u", "-G1", "-n"],
      #    )[0]

      if raw is None or len(raw) == 0:
        raise ValueError("Empty image bytes")

      try:
        metadata = json.loads(subprocess.run(
          [
              "exiftool",
              "-json",
              "-G1",
              "-struct",
              "-n",
              "-",
          ],
          input=raw,
          stdout=subprocess.PIPE,
          #stderr=subprocess.PIPE,
          check=True
        ).stdout.decode("utf-8"))[0]
      except subprocess.CalledProcessError as e:
        print(f"ExifTool failed: {e.stderr.decode('utf-8')}")

      except Exception as e:
        print(f"Unexpected error: {e}")

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
  def build_dataframe(self, raw: bytes):
      structured = self.extract_metadata(raw)

      row = self.dict_to_row(structured)

      return row

  # ----------------------------
  # pretty print schema-like view
  # ----------------------------
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

