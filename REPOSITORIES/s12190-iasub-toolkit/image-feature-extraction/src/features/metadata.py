from .base import FeatureExtractor

import io
from PIL import Image, ExifTags
from pyspark.sql.types import MapType, StringType

import struct
import xml.etree.ElementTree as ET

from pyspark.sql.types import IntegerType, FloatType
from pyspark.sql.types import *


def _safe_int(val) -> int | None:
  if val is None: return None
  try:    return int(val)
  except: return None

def _safe_str(val) -> str | None:
  if val is None: return None
  try:    return str(val)
  except: return None

def _safe_float(val) -> float | None:
  if val is None: return None
  try:    return float(val)
  except: return None

class MetadataExtractor(FeatureExtractor):
  name = "metadata"
  order = 4

  def extract(self, ctx):
    content = ctx["content"]
    tags = self._parse_metadata(content)

    return {
      "telemetry": {
        "image_time": tags.get("image_time"),
        "image_date": tags.get("image_date"),
        "acq_index": tags.get("acq_index"),
        "longitude": tags.get("longitude"),
        "latitude": tags.get("latitude"),
        "depth_m": tags.get("depth_m"),
        "altitude_m": tags.get("altitude_m"),
        "pitch_deg": tags.get("pitch_deg"),
        "roll_deg": tags.get("roll_deg"),
        "yaw_deg": tags.get("yaw_deg"),
        "position_time": tags.get("position_time"),
        "position_received": tags.get("position_received"),
        "position_extrapolated": tags.get("position_extrapolated"),
        "position_age_ms": tags.get("position_age_ms"),
        "exposure": tags.get("exposure"),
        "aperture": tags.get("aperture"),
        "focus": tags.get("focus"),
        "digital_gain": tags.get("digital_gain"),
        "analog_gain": tags.get("analog_gain"),
        "sensor_gain": tags.get("sensor_gain"),
        "camera_name": tags.get("camera_name"),
        "session_name": tags.get("session_name"),
        "focus_enc": tags.get("focus_enc"),
        "seq_slot": tags.get("seq_slot"),
        "sw_version": tags.get("sw_version"),
        "fpga_version": tags.get("fpga_version"),
        "serial_number": tags.get("serial_number"),
        "clarity_date": tags.get("clarity_date"),
        "clarity_version": tags.get("clarity_version"),
        "clarity_filters": tags.get("clarity_filters"),
        "camera_model": tags.get("camera_model"),
        "camera_serial": tags.get("camera_serial"),
        "camera_firmware": tags.get("camera_firmware"),
        "focal_length_px": tags.get("focal_length_px"),
        "k1": tags.get("k1"),
        "k2": tags.get("k2"),
        "k3": tags.get("k3"),
        "p1": tags.get("p1"),
        "p2": tags.get("p2"),
        "sensor_width_px": tags.get("sensor_width_px"),
        "sensor_height_px": tags.get("sensor_height_px"),
        "offset_x": tags.get("offset_x"),
        "offset_y": tags.get("offset_y"),
        "lever_x_mm": tags.get("lever_x_mm"),
        "lever_y_mm": tags.get("lever_y_mm"),
        "lever_z_mm": tags.get("lever_z_mm"),
        "lever_pitch": tags.get("lever_pitch"),
        "lever_roll": tags.get("lever_roll"),
        "lever_yaw": tags.get("lever_yaw"),
        "jfif_resolution_unit": tags.get("jfif_resolution_unit"),
        "jfif_x_resolution": tags.get("jfif_x_resolution"),
        "jfif_y_resolution": tags.get("jfif_y_resolution"),
        "exif_byte_order": tags.get("exif_byte_order"),
        "exif_pixel_width": tags.get("exif_pixel_width"),
        "exif_pixel_height": tags.get("exif_pixel_height"),
      },
      "geo_info": {
        "geo_pixel_x_size": tags.get("geo_pixel_x_size"),
        "geo_pixel_y_size": tags.get("geo_pixel_y_size"),
        "geo_rot1": tags.get("geo_rot1"),
        "geo_rot2": tags.get("geo_rot2"),
        "geo_upper_left_x": tags.get("geo_upper_left_x"),
        "geo_upper_left_y": tags.get("geo_upper_left_y"),
        "gt_model_type": tags.get("gt_model_type"),
        "gt_raster_type": tags.get("gt_raster_type"),
        "gt_citation": tags.get("gt_citation"),
        "projected_cs_type": tags.get("projected_cs_type"),
        "pcs_citation": tags.get("pcs_citation"),
        "projection": tags.get("projection"),
        "proj_linear_units": tags.get("proj_linear_units"),
        "geog_type": tags.get("geog_type"),
        "geog_citation": tags.get("geog_citation"),
        "geog_geodetic_datum":tags.get("geog_geodetic_datum"),
        "geog_ellipsoid": tags.get("geog_ellipsoid"),
        "geog_semi_major_axis": tags.get("geog_semi_major_axis"),
        "geog_semi_minor_axis": tags.get("geog_semi_minor_axis"),
        "geog_inv_flattening": tags.get("geog_inv_flattening"),
        "nodata": tags.get("nodata"),
        "bits_per_sample": str(tags.get("bits_per_sample")) if tags.get("bits_per_sample") is not None else None,
        "compression": _safe_int(tags.get("compression")),
        "samples_per_pixel": _safe_int(tags.get("samples_per_pixel")),
        "planar_config": tags.get("planar_config"),
        "orientation": _safe_int(tags.get("orientation")),
      },
    }


  def schema(self):
    return {
      "telemetry": StructType([
        # Image header
        StructField("image_time", StringType(), True),
        StructField("image_date", StringType(), True),
        StructField("acq_index", IntegerType(), True),
        # Position
        StructField("longitude", DoubleType(), True),
        StructField("latitude", DoubleType(), True),
        StructField("depth_m", DoubleType(), True),
        StructField("altitude_m", DoubleType(), True),
        StructField("pitch_deg", DoubleType(), True),
        StructField("roll_deg", DoubleType(), True),
        StructField("yaw_deg", DoubleType(), True),
        StructField("position_time", StringType(), True),
        StructField("position_received", StringType(), True),
        StructField("position_extrapolated", BooleanType(), True),
        StructField("position_age_ms", DoubleType(), True),
        # Acquisition
        StructField("exposure", IntegerType(), True),
        StructField("aperture", DoubleType(), True),
        StructField("focus", IntegerType(), True),
        StructField("digital_gain", DoubleType(), True),
        StructField("analog_gain", IntegerType(), True),
        StructField("sensor_gain", IntegerType(), True),
        StructField("camera_name", StringType(), True),
        StructField("session_name", StringType(), True),
        StructField("focus_enc", IntegerType(), True),
        StructField("seq_slot", IntegerType(), True),
        # Versions
        StructField("sw_version", StringType(), True),
        StructField("fpga_version", StringType(), True),
        StructField("serial_number", StringType(), True),
        # Clarity / camera intrinsics
        StructField("clarity_date", StringType(), True),
        StructField("clarity_version", StringType(), True),
        StructField("clarity_filters", StringType(), True),
        StructField("camera_model", StringType(), True),
        StructField("camera_serial", StringType(), True),
        StructField("camera_firmware", StringType(), True),
        StructField("focal_length_px", DoubleType(), True),
        StructField("k1", DoubleType(), True),
        StructField("k2", DoubleType(), True),
        StructField("k3", DoubleType(), True),
        StructField("p1", DoubleType(), True),
        StructField("p2", DoubleType(), True),
        StructField("sensor_width_px", IntegerType(), True),
        StructField("sensor_height_px", IntegerType(), True),
        StructField("offset_x", DoubleType(), True),
        StructField("offset_y", DoubleType(), True),
        # Lever arms
        StructField("lever_x_mm", DoubleType(), True),
        StructField("lever_y_mm", DoubleType(), True),
        StructField("lever_z_mm", DoubleType(), True),
        StructField("lever_pitch", DoubleType(), True),
        StructField("lever_roll", DoubleType(), True),
        StructField("lever_yaw", DoubleType(), True),
        # JFIF
        StructField("jfif_resolution_unit", StringType(), True),
        StructField("jfif_x_resolution", IntegerType(), True),
        StructField("jfif_y_resolution", IntegerType(), True),
        # EXIF
        StructField("exif_byte_order", StringType(), True),
        StructField("exif_pixel_width", IntegerType(), True),
        StructField("exif_pixel_height", IntegerType(), True),
      ]),

      "geo_info": StructType([
        # Spatial transform (from .jgw or GeoTIFF ModelPixelScale+Tiepoint)
        StructField("geo_pixel_x_size", DoubleType(), True),
        StructField("geo_pixel_y_size", DoubleType(), True),
        StructField("geo_rot1", DoubleType(), True),
        StructField("geo_rot2", DoubleType(), True),
        StructField("geo_upper_left_x", DoubleType(), True),
        StructField("geo_upper_left_y", DoubleType(), True),
        # CRS / GeoKey
        StructField("gt_model_type", IntegerType(), True),
        StructField("gt_raster_type", IntegerType(), True),
        StructField("gt_citation", StringType(), True),
        StructField("projected_cs_type", IntegerType(), True),
        StructField("pcs_citation", StringType(), True),
        StructField("projection", IntegerType(), True),
        StructField("proj_linear_units", IntegerType(), True),
        StructField("geog_type", IntegerType(), True),
        StructField("geog_citation", StringType(), True),
        StructField("geog_geodetic_datum",IntegerType(), True),
        StructField("geog_ellipsoid", IntegerType(), True),
        StructField("geog_semi_major_axis", DoubleType(), True),
        StructField("geog_semi_minor_axis", DoubleType(), True),
        StructField("geog_inv_flattening", DoubleType(), True),
        StructField("nodata", StringType(), True),
        # Standard TIFF tags (present in both JPEG-via-EXIF and TIFF)
        StructField("bits_per_sample", StringType(), True),
        StructField("compression", IntegerType(), True),
        StructField("samples_per_pixel", IntegerType(), True),
        StructField("planar_config", IntegerType(), True),
        StructField("orientation", IntegerType(), True),
      ]),
    }


  def _parse_metadata(self, raw: bytes, jgw_bytes: bytes = None) -> dict:
    #is_tiff = raw[:2] in (b'II', b'MM')
    #is_jpeg = raw[:2] == b'\xff\xd8'

    #if is_jpeg:
    #  return self._parse_jpeg_metadata(raw, jgw_bytes)
    #elif is_tiff:
    #  return self._parse_tiff_metadata(raw)
    #return {}

    result = {}

    try:
      result.update(self._parse_jpeg_metadata(raw, jgw_bytes))
    except Exception as e:
      pass

    try:
      result.update(self._parse_tiff_metadata(raw))
    except Exception as e:
      pass

    return result


  # ─────────────────────────────────────────────
  # JPEG
  # ─────────────────────────────────────────────

  def _parse_jpeg_metadata(self, raw: bytes, jgw_bytes: bytes = None) -> dict:
    result = {}

    # --- JFIF header (APP0) ---
    jfif = self._parse_jfif(raw)
    result.update(jfif)

    # --- EXIF (APP1) ---
    exif = self._parse_jpeg_exif(raw)
    result.update(exif)

    # --- AUV XML from COM segment ---
    xml_str = self._extract_jpeg_comment(raw)
    if xml_str:
      result.update(self._parse_auv_xml(xml_str))

    # --- .jgw sidecar ---
    if jgw_bytes:
      result.update(self._parse_jgw(jgw_bytes))

    return result


  def _parse_jfif(self, raw: bytes) -> dict:
    """Parse APP0 JFIF segment for resolution metadata."""
    result = {}
    i = 2
    while i < len(raw) - 4:
      marker = raw[i:i+2]
      if marker == b'\xff\xe0':                         # APP0
        # JFIF: identifier(5) + version(2) + units(1) + Xdensity(2) + Ydensity(2)
        if raw[i+4:i+9] == b'JFIF\x00':
          units = raw[i+11]
          x_res = struct.unpack('>H', raw[i+12:i+14])[0]
          y_res = struct.unpack('>H', raw[i+14:i+16])[0]
          unit_map = {0: 'aspect', 1: 'inch', 2: 'cm'}
          result['jfif_resolution_unit'] = unit_map.get(units, str(units))
          result['jfif_x_resolution'] = x_res
          result['jfif_y_resolution'] = y_res
        break
      elif marker[0:1] == b'\xff' and i + 4 <= len(raw):
        length = struct.unpack('>H', raw[i+2:i+4])[0]
        i += 2 + length
      else:
        break
    return result


  def _parse_jpeg_exif(self, raw: bytes) -> dict:
    """Parse APP1 EXIF segment for pixel dimensions and byte order."""
    result = {}
    i = 2
    while i < len(raw) - 4:
      marker = raw[i:i+2]
      if marker == b'\xff\xe1':                         # APP1
        length = struct.unpack('>H', raw[i+2:i+4])[0]
        seg = raw[i+4:i+2+length]
        if seg[:6] == b'Exif\x00\x00':
          tiff_data = seg[6:]
          byte_order = tiff_data[:2]
          bo = '>' if byte_order == b'MM' else '<'
          result['exif_byte_order'] = 'big-endian' if bo == '>' else 'little-endian'
          # IFD0 offset
          ifd_offset = struct.unpack(bo + 'I', tiff_data[4:8])[0]
          tags = self._read_tiff_ifd(tiff_data, ifd_offset, bo)
          # Tag 0xA002 = PixelXDimension, 0xA003 = PixelYDimension
          if 0xA002 in tags: result['exif_pixel_width']  = tags[0xA002]
          if 0xA003 in tags: result['exif_pixel_height'] = tags[0xA003]
        break
      elif marker[0:1] == b'\xff' and i + 4 <= len(raw):
        length = struct.unpack('>H', raw[i+2:i+4])[0]
        i += 2 + length
      else:
        break
    return result


  def _extract_jpeg_comment(self, raw: bytes) -> str:
    """Extract raw string from JPEG COM (0xFFFE) segment."""
    i = 2
    while i < len(raw) - 4:
      marker = raw[i:i+2]
      if marker == b'\xff\xfe':                         # COM
        length = struct.unpack('>H', raw[i+2:i+4])[0]
        return raw[i+4:i+2+length].decode('utf-8', errors='ignore')
      elif marker[0:1] == b'\xff' and i + 4 <= len(raw):
        length = struct.unpack('>H', raw[i+2:i+4])[0]
        i += 2 + length
      else:
        break
    return ''


  def _parse_auv_xml(self, xml_str: str) -> dict:
    """Parse NOAA AUV XML comment — full extraction of all available fields."""
    result = {}

    # Sanitize: replace common non-XML line separators and control chars
    clean = (xml_str
      .strip()
      .replace('..', '\n') # exiftool display artifact
      .replace('\x00', '') # null bytes
      .replace('\r\n', '\n')
      .replace('\r', '\n')
    )

    # Strip any leading non-XML content before the root tag
    start = clean.find('<image')
    if start == -1:
      start = clean.find('<')
    if start > 0:
      clean = clean[start:]

    # Remove any trailing content after the closing tag
    end = clean.rfind('</image>')
    if end != -1:
      clean = clean[:end + len('</image>')]

    try:
      root = ET.fromstring(clean)
    except ET.ParseError as e:
      # Log the line that failed to help diagnose future variants
      lines = clean.splitlines()
      import logging
      logging.warning(f"metadata XML parse failed: {e}")
      line_no = e.position[0] - 1 if hasattr(e, 'position') else -1
      if 0 <= line_no < len(lines):
          logging.warning(f"  offending line {line_no}: {lines[line_no]!r}")
      return result


    #root = ET.fromstring(xml_str.strip())

    # Image header
    result['image_time'] = root.get('time', '')
    result['image_date'] = root.get('date', '')
    result['acq_index'] = int(root.get('acq_index', 0))

    # Position
    pos = root.find('Position')
    if pos is not None:
      result['position_time'] = pos.get('time', '')
      result['position_received'] = pos.get('received', '')
      result['position_extrapolated'] = pos.get('extrapolated', '') == 'true'
      result['position_age_ms'] = float(pos.get('age', 0))

      coords = pos.find('Coords')
      if coords is not None:
        result['longitude'] = float(coords.get('long', 0))
        result['latitude'] = float(coords.get('lat', 0))

      depth = pos.find('Depth')
      if depth is not None:
        result['depth_m'] = float(depth.get('depth', 0))
        result['altitude_m'] = float(depth.get('altitude', 0))

      direc = pos.find('Direction')
      if direc is not None:
        result['pitch_deg'] = float(direc.get('pitch', 0))
        result['roll_deg'] = float(direc.get('roll', 0))
        result['yaw_deg'] = float(direc.get('yaw', 0))

    # Acquisition
    acq = root.find('acquisition')
    if acq is not None:
      result['exposure'] = int(acq.findtext('exposure', '0'))
      result['aperture'] = float(acq.findtext('aperture', '0'))
      result['focus'] = int(acq.findtext('focus', '0'))
      result['digital_gain'] = float(acq.findtext('digital_gain', '0'))
      result['analog_gain'] = int(acq.findtext('analog_gain', '0'))
      result['sensor_gain'] = int(acq.findtext('sensor_gain', '0'))
      result['camera_name'] = acq.findtext('name', '')
      result['session_name'] = acq.findtext('camera_session_name', '')
      result['focus_enc'] = int(acq.findtext('focus_enc', '0'))
      result['seq_slot'] = int(acq.findtext('seq_slot', '0'))

    # Versions
    ver = root.find('versions')
    if ver is not None:
      result['sw_version'] = ver.findtext('software', '')
      result['fpga_version'] = ver.findtext('fpga', '')
      result['serial_number'] = ver.findtext('serial_number', '')

    # Clarity processing / camera intrinsics
    cp = root.find('clarity-processing')
    if cp is not None:
      result['clarity_date'] = cp.get('Date', '')
      result['clarity_version'] = cp.get('Version', '')
      result['clarity_filters'] = cp.findtext('Filters', '')

      cam = cp.find('.//Camera/Camera')   # inner Camera element
      if cam is None:
        cam = cp.find('.//Config/Camera')
      if cam is not None:
        result['camera_model'] = cam.findtext('Model', '')
        result['camera_serial'] = cam.findtext('SerialNumber', '')
        result['camera_firmware'] = cam.findtext('Firmware',     '')
        result['focal_length_px'] = float(cam.findtext('F',  '0'))
        result['k1'] = float(cam.findtext('K1', '0'))
        result['k2'] = float(cam.findtext('K2', '0'))
        result['k3'] = float(cam.findtext('K3', '0'))
        result['p1'] = float(cam.findtext('P1', '0'))
        result['p2'] = float(cam.findtext('P2', '0'))
        result['sensor_width_px'] = int(cam.findtext('Width', '0'))
        result['sensor_height_px'] = int(cam.findtext('Height', '0'))
        result['offset_x'] = float(cam.findtext('OffsetX', '0'))
        result['offset_y'] = float(cam.findtext('OffsetY', '0'))

      la = cp.find('.//LeverArms')
      if la is not None:
        result['lever_x_mm'] = float(la.findtext('X', '0'))
        result['lever_y_mm'] = float(la.findtext('Y', '0'))
        result['lever_z_mm'] = float(la.findtext('Z', '0'))
        result['lever_pitch'] = float(la.findtext('Pitch', '0'))
        result['lever_roll'] = float(la.findtext('Roll', '0'))
        result['lever_yaw'] = float(la.findtext('Yaw', '0'))

    return result


  def _parse_jgw(self, jgw_bytes: bytes) -> dict:
    """
    Parse .jgw world file (6 lines):
      pixel_x_size, rot1, rot2, pixel_y_size (negative), upper_left_x, upper_left_y
    """
    lines = [l.strip() for l in jgw_bytes.decode('utf-8', errors='ignore').splitlines()
             if l.strip()]
    if len(lines) < 6:
        return {}
    v = [float(l) for l in lines[:6]]
    return {
      'geo_rot1': v[1],
      'geo_rot2': v[2],
      'geo_pixel_x_size': v[0],
      'geo_pixel_y_size': v[3],
      'geo_upper_left_x': v[4],
      'geo_upper_left_y': v[5],
    }


  # ─────────────────────────────────────────────
  # TIFF
  # ─────────────────────────────────────────────

  def _parse_tiff_metadata(self, raw: bytes) -> dict:
    """
    Full GeoTIFF metadata extraction via nvimgcodec sub-code-stream
    + tifffile for GeoKey decoding.
    """
    result = {}

    # nvimgcodec path for raw tag values
    try:
      cs  = nvimgcodec.CodeStream(raw)
      scs = cs.get_sub_code_stream(0)
      for m in self.decoder.get_metadata(scs):
        if m.kind == nvimgcodec.MetadataKind.UNKNOWN:
          result[f'tag_{m.id}'] = m.value
        else:
          result[f'tag_{m.id}'] = (
            m.buffer.decode('utf-8', errors='ignore')
            if hasattr(m, 'buffer') else m.value
          )
    except Exception:
      pass

    # tifffile for structured GeoTIFF decoding
    try:
      import io, tifffile
      with tifffile.TiffFile(io.BytesIO(raw)) as tif:
        page = tif.pages[0]

        # Standard TIFF tags
        tags = {t.code: t.value for t in page.tags.values()}

        result['tiff_width']  = _safe_int(tags.get(256)) # ImageWidth
        result['tiff_height'] = _safe_int(tags.get(257)) # ImageLength
        result['bits_per_sample'] = _safe_str(tags.get(258)) # BitsPerSample
        result['compression'] = _safe_int(tags.get(259)) # Compression
        result['photometric'] = _safe_int(tags.get(262)) # PhotometricInterp
        result['samples_per_pixel'] = _safe_int(tags.get(277)) # SamplesPerPixel
        result['planar_config'] = _safe_int(tags.get(284)) # PlanarConfiguration
        result['sample_format'] = _safe_str(tags.get(339)) # SampleFormat
        result['orientation'] = _safe_int(tags.get(274)) # Orientation
        result['nodata'] = _safe_str(tags.get(42113)) # GDAL_NODATA

        # GeoTIFF spatial tags
        pixel_scale = tags.get(33550) # ModelPixelScaleTag
        if pixel_scale is not None:
          result['geo_pixel_x_size'] = float(pixel_scale[0])
          result['geo_pixel_y_size'] = float(pixel_scale[1])

        tiepoint = tags.get(33922) # ModelTiepointTag
        if tiepoint is not None:
          result['geo_upper_left_x'] = float(tiepoint[3])
          result['geo_upper_left_y'] = float(tiepoint[4])

        # GeoKey directory → CRS info
        geo_key_dir = tags.get(34735) # GeoKeyDirectoryTag
        if geo_key_dir is not None:
          geo_doubles = tags.get(34736, []) # GeoDoubleParamsTag
          geo_ascii   = tags.get(34737, '') # GeoAsciiParamsTag
          result.update(
            self._decode_geokeys_full(geo_key_dir, geo_doubles, geo_ascii)
          )

    except Exception:
        pass

    return result


  def _decode_geokeys_full(self, directory, doubles, ascii_params) -> dict:
    """Decode GeoTIFF GeoKey directory into named CRS fields."""
    KEY_MAP = {
      1024: 'gt_model_type',
      1025: 'gt_raster_type',
      1026: 'gt_citation',
      2048: 'geog_type',
      2049: 'geog_citation',
      2050: 'geog_geodetic_datum',
      2051: 'geog_prime_meridian',
      2052: 'geog_linear_units',
      2053: 'geog_linear_unit_size',
      2054: 'geog_angular_units',
      2055: 'geog_angular_unit_size',
      2056: 'geog_ellipsoid',
      2057: 'geog_semi_major_axis',
      2058: 'geog_semi_minor_axis',
      2059: 'geog_inv_flattening',
      3072: 'projected_cs_type',
      3073: 'pcs_citation',
      3074: 'projection',
      3075: 'proj_coord_trans',
      3076: 'proj_linear_units',
      3078: 'proj_std_parallel1',
      3082: 'proj_false_easting',
      3083: 'proj_false_northing',
      4096: 'vertical_cs_type',
    }
    result  = {}
    n_keys  = int(directory[3])
    doubles = list(doubles) if doubles is not None else []
    ascii_s = ascii_params if isinstance(ascii_params, str) else ''

    for i in range(1, n_keys + 1):
      key_id    = int(directory[i * 4])
      tiff_tag  = int(directory[i * 4 + 1])
      count     = int(directory[i * 4 + 2])
      value_off = int(directory[i * 4 + 3])

      name = KEY_MAP.get(key_id, f'geokey_{key_id}')

      if tiff_tag == 0:
        result[name] = value_off                             # SHORT value inline
      elif tiff_tag == 34736:                                  # DOUBLE
        result[name] = doubles[value_off] if value_off < len(doubles) else None
      elif tiff_tag == 34737:                                  # ASCII
        result[name] = ascii_s[value_off:value_off + count].rstrip('|')

    return result


  def _read_tiff_ifd(self, data: bytes, offset: int, bo: str) -> dict:
    """Minimal IFD reader for EXIF tag extraction."""
    tags   = {}
    n_tags = struct.unpack(bo + 'H', data[offset:offset+2])[0]
    for i in range(n_tags):
      base   = offset + 2 + i * 12
      tag_id = struct.unpack(bo + 'H', data[base:base+2])[0]
      t_type = struct.unpack(bo + 'H', data[base+2:base+4])[0]
      count  = struct.unpack(bo + 'I', data[base+4:base+8])[0]
      v_off  = data[base+8:base+12]
      if t_type in (3,) and count == 1:                       # SHORT
        tags[tag_id] = struct.unpack(bo + 'H', v_off[:2])[0]
      elif t_type in (4,) and count == 1:                     # LONG
        tags[tag_id] = struct.unpack(bo + 'I', v_off)[0]
    return tags

