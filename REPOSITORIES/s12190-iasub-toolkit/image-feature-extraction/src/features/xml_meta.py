from .base import FeatureExtractor

import re
import xml.etree.ElementTree as ET
from pyspark.sql.types import (
    DoubleType, StringType
)



class XMLMetadataExtractor(FeatureExtractor):
  name = "xml_meta"
  order = 5

  def extract(self, ctx):
    content = ctx["content"]

    result = {
      "gps_lat": None,
      "gps_lon": None,
      "depth": None,
      "altitude": None,
      "pitch": None,
      "roll": None,
      "yaw": None,
      "camera_model": None,
      "camera_serial": None,
      "exposure": None,
      "aperture": None,
      "analog_gain": None,
      "digital_gain": None,
      "sensor_gain": None,
    }

    try:
      text = content.decode(errors="ignore")

      match = re.search(r"<image.*?</image>", text, re.DOTALL)
      if not match:
        return result

      root = ET.fromstring(match.group(0))

      coords = root.find(".//Coords")
      if coords is not None:
        result["gps_lon"] = float(coords.attrib.get("long", "nan"))
        result["gps_lat"] = float(coords.attrib.get("lat", "nan"))

      depth = root.find(".//Depth")
      if depth is not None:
        result["depth"] = float(depth.attrib.get("depth", "nan"))
        result["altitude"] = float(depth.attrib.get("altitude", "nan"))

      direction = root.find(".//Direction")
      if direction is not None:
        result["pitch"] = float(direction.attrib.get("pitch", "nan"))
        result["roll"] = float(direction.attrib.get("roll", "nan"))
        result["yaw"] = float(direction.attrib.get("yaw", "nan"))

      acq = root.find(".//acquisition")
      if acq is not None:
        result["exposure"] = float(acq.findtext("exposure", "nan"))
        result["aperture"] = float(acq.findtext("aperture", "nan"))
        result["analog_gain"] = float(acq.findtext("analog_gain", "nan"))
        result["digital_gain"] = float(acq.findtext("digital_gain", "nan"))
        result["sensor_gain"] = float(acq.findtext("sensor_gain", "nan"))

      cam = root.find(".//Camera")
      if cam is not None:
        result["camera_model"] = cam.findtext("Model")
        result["camera_serial"] = cam.findtext("SerialNumber")

    except Exception:
      pass

    return result

  def schema(self):
    return {
      "gps_lat": DoubleType(),
      "gps_lon": DoubleType(),
      "depth": DoubleType(),
      "altitude": DoubleType(),
      "pitch": DoubleType(),
      "roll": DoubleType(),
      "yaw": DoubleType(),
      "camera_model": StringType(),
      "camera_serial": StringType(),
      "exposure": DoubleType(),
      "aperture": DoubleType(),
      "analog_gain": DoubleType(),
      "digital_gain": DoubleType(),
      "sensor_gain": DoubleType(),
    }
