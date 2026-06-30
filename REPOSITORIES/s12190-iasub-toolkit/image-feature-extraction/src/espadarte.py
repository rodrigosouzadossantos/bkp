from .ingestion.spark_session import create_spark

from re import I
#from ingestion.ingest import run_ingestion

from pyspark.sql.window import Window
from pyspark.sql import functions as F

import math
from PIL import Image, ImageOps
from io import BytesIO

import cv2
import numpy as np


PATH = 's3a://noaa-auv/main/NOAA-AUV/ESPADARTE/6000702270/COM20240425/'

N = 50
N_COLS = 5
THUMB_SIZE = (200, 200)  # size of each tile
BORDER_SIZE = 0          # thickness of border
SPACING = 3              # gap between images
BORDER_COLOR = (0, 0, 0) # black border

from .schemas.noaa_auv import noaa_auv_schema

def main():
  spark = create_spark()

  df = (
    spark.read
    .format("binaryFile")
    .option("recursiveFileLookup", "true")
    .option("pathGlobFilter", "*.tif")
    .load(PATH)
  )

  #df = df.repartition(512)

  #print("Total images:", df.count())
  #df.show()

  #df = df.withColumn("id", F.monotonically_increasing_id())
  #df.select("path", "length", "id").show( )
  #df.select("path", "length").show( N )

  from pyspark.sql.functions import pandas_udf
  import pandas as pd

  import numpy as np
  import cv2
  from skimage.feature import local_binary_pattern

  from PIL import Image, ExifTags
  import io
  import xml.etree.ElementTree as ET
  import re

  from pyspark.sql import Row

  def process_partition(iterator):

    for row in iterator:
        try:
            content = row.content
            path = row.path

            # -------------------------
            # Decode image
            # -------------------------
            nparr = np.frombuffer(content, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

            if img is None:
                raise ValueError("Invalid image")

            h, w = img.shape[:2]

            # -------------------------
            # Image stats
            # -------------------------
            hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

            brightness = float(hsv[:, :, 2].mean())
            contrast = float(img.std())
            blur = float(cv2.Laplacian(img, cv2.CV_64F).var())

            mean_b, mean_g, mean_r = img.mean(axis=(0, 1))

            # --- histograms ---
            rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

            hist_r = cv2.calcHist([rgb], [0], None, [32], [0, 256]).flatten()
            hist_g = cv2.calcHist([rgb], [1], None, [32], [0, 256]).flatten()
            hist_b = cv2.calcHist([rgb], [2], None, [32], [0, 256]).flatten()

            hist_r = (hist_r / hist_r.sum()).astype(float).tolist()
            hist_g = (hist_g / hist_g.sum()).astype(float).tolist()
            hist_b = (hist_b / hist_b.sum()).astype(float).tolist()

            # --- LBP ---
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            lbp = local_binary_pattern(gray, P=8, R=1, method="uniform")

            lbp_hist, _ = np.histogram(
                lbp.ravel(),
                bins=20,
                range=(0, 20),
                density=True
            )
            lbp_hist = lbp_hist.astype(float).tolist()

            # -------------------------
            # EXIF
            # -------------------------
            exif_dict = {}
            pil_img = Image.open(io.BytesIO(content))

            if hasattr(pil_img, "_getexif") and pil_img._getexif():
                raw = pil_img._getexif()
                for tag, value in raw.items():
                    tag_name = ExifTags.TAGS.get(tag, str(tag))
                    exif_dict[tag_name] = str(value)

            # -------------------------
            # XML extraction
            # -------------------------
            gps_lat = gps_lon = None
            depth = altitude = None
            pitch = roll = yaw = None

            camera_model = camera_serial = None
            exposure = aperture = None
            analog_gain = digital_gain = sensor_gain = None

            try:
                text = content.decode(errors="ignore")

                match = re.search(r"<image.*?</image>", text, re.DOTALL)

                if match:
                    root = ET.fromstring(match.group(0))

                    coords = root.find(".//Coords")
                    if coords is not None:
                        gps_lon = float(coords.attrib.get("long", "nan"))
                        gps_lat = float(coords.attrib.get("lat", "nan"))

                    depth_node = root.find(".//Depth")
                    if depth_node is not None:
                        depth = float(depth_node.attrib.get("depth", "nan"))
                        altitude = float(depth_node.attrib.get("altitude", "nan"))

                    direction = root.find(".//Direction")
                    if direction is not None:
                        pitch = float(direction.attrib.get("pitch", "nan"))
                        roll = float(direction.attrib.get("roll", "nan"))
                        yaw = float(direction.attrib.get("yaw", "nan"))

                    acq = root.find(".//acquisition")
                    if acq is not None:
                        exposure = float(acq.findtext("exposure", default="nan"))
                        aperture = float(acq.findtext("aperture", default="nan"))
                        analog_gain = float(acq.findtext("analog_gain", default="nan"))
                        digital_gain = float(acq.findtext("digital_gain", default="nan"))
                        sensor_gain = float(acq.findtext("sensor_gain", default="nan"))

                    cam = root.find(".//Camera")
                    if cam is not None:
                        camera_model = cam.findtext("Model")
                        camera_serial = cam.findtext("SerialNumber")

            except Exception:
                pass

            yield Row(
                path=path,
                width=int(w),
                height=int(h),
                brightness=brightness,
                contrast=contrast,
                blur=blur,

                mean_r=float(mean_r),
                mean_g=float(mean_g),
                mean_b=float(mean_b),

                hist_r=hist_r,
                hist_g=hist_g,
                hist_b=hist_b,
                lbp_hist=lbp_hist,

                gps_lat=gps_lat,
                gps_lon=gps_lon,
                depth=depth,
                altitude=altitude,
                pitch=pitch,
                roll=roll,
                yaw=yaw,

                camera_model=camera_model,
                camera_serial=camera_serial,
                exposure=exposure,
                aperture=aperture,
                analog_gain=analog_gain,
                digital_gain=digital_gain,
                sensor_gain=sensor_gain,

                exif=exif_dict
            )

        except Exception:
            yield Row(**{f.name: None for f in noaa_auv_schema.fields})



  fraction = 10 / 310959 #df.count()

  print('>> RDD...')
  rdd = ( df
  #  .sample(fraction=fraction, seed=42)
    .select("path", "content")
    .rdd.mapPartitions(process_partition)
  )
  print('>> CreateDF...')
  df_out = spark.createDataFrame(rdd, noaa_auv_schema)

  #print('>> Repartition...')
  #df_out = df_out.repartition(200)

  print('>> WriteTo...')
  df_out \
    .writeTo("lakefs.images.espadarte") \
    .using("iceberg") \
    .tableProperty("format-version", "2") \
    .tableProperty("write.format.default", "parquet") \
    .option("write.target-file-size-bytes", 134217728) \
    .createOrReplace()


  print('>> LAKEFS...')

  #hconf = spark.sparkContext._jsc.hadoopConfiguration()
  #print(hconf.get("spark.hadoop.fs.s3a.endpoint"))
  #print(hconf.get("spark.hadoop.fs.s3a.access.key"))
  #print(hconf.get("spark.hadoop.fs.s3a.secret.key"))

  from lakefs.client import Client
  from lakefs.repository import Repository

  client = Client(
    host=spark.conf.get("spark.hadoop.fs.s3a.endpoint"),
    username=spark.conf.get("spark.hadoop.fs.s3a.access.key"),
    password=spark.conf.get("spark.hadoop.fs.s3a.secret.key"),
  )

  print('>> COMMIT...')

  #import lakefs
  #all_repos = lakefs.repositories(client=client)
  #for repo in all_repos:
  #  print(repo.id)

  repo = Repository("iceberg", client)
  repo.branch("main").commit(
    message="Iceberg dataset update",
    metadata={
      "dataset": "images.espadarte",
      "rows": str(df_out.count()),
      "features": "brightness,contrast,lbp_hist"
    }
  )

  #df_out.printSchema()

  #df_out.show()

  #print("Total images:", df_out.count())

  print('>> DONE...')


if __name__ == "__main__":
  main()
