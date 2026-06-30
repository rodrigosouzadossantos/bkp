#import io
#import json
import uuid
#import math
#import numpy as np
from datetime import datetime

import boto3
from boto3 import Session

import ssl

ssl._create_default_https_context = ssl._create_unverified_context

from pyspark.sql import Row

def load_image_bytes(s3_client, uri: str) -> bytes:
  bucket, key = uri.replace("s3://", "").split("/", 1)
  obj = s3_client.get_object(Bucket=bucket, Key=key)
  return obj["Body"].read()

def process_image(uri: str) -> Row:
  print(f"Processing image: {uri}")

  session = boto3.Session(profile_name="lakefs")

  s3 = session.client(
      service_name="s3",
      endpoint_url="http://localhost:8000",
  )

  img_bytes = load_image_bytes(s3, uri)

  return Row(
    image_id=str(uuid.uuid4()),
    s3_uri=uri,
    ingestion_time=datetime.utcnow(),
)


def run_ingestion(spark):
  print("Ingestion pipeline started")

  # 1. Read S3 images
  # 2. Detect CAMERA vs RASTER
  # 3. Extract metadata (EXIF / GeoTIFF)
  # 4. Compute CV features
  # 5. Write to Iceberg

  uris = [
    's3://noaa-auv/main/NOAA-AUV/VIOLA/6000713538/FT_20241016_053320_3_BC0030VB0153.jpg'
    's3://noaa-auv/main/NOAA-AUV/VIOLA/6000713538/FT_20241016_035829_6_BC0030VB0153.jpg'
    's3://noaa-auv/main/NOAA-AUV/VIOLA/6000713538/FT_20241016_061747_6_BC0030VB0153.jpg'
    's3://noaa-auv/main/NOAA-AUV/VIOLA/6000713538/FT_20241016_055914_3_BC0030VB0153.jpg'
    's3://noaa-auv/main/NOAA-AUV/VIOLA/6000713538/FT_20241016_023259_3_BC0030VB0153.jpg'
    's3://noaa-auv/main/NOAA-AUV/VIOLA/6000713538/FT_20241016_055251_0_BC0030VB0153.jpg'
    's3://noaa-auv/main/NOAA-AUV/VIOLA/6000713538/FT_20241016_041356_6_BC0030VB0153.jpg'
    's3://noaa-auv/main/NOAA-AUV/VIOLA/6000713538/FT_20241016_021849_6_BC0030VB0153.jpg'
    's3://noaa-auv/main/NOAA-AUV/VIOLA/6000713538/FT_20241016_061946_0_BC0030VB0153.jpg'
    's3://noaa-auv/main/NOAA-AUV/VIOLA/6000713538/FT_20241016_035420_3_BC0030VB0153.jpg'
    's3://noaa-auv/main/NOAA-AUV/VIOLA/6000713538/FT_20241016_022332_3_BC0030VB0153.jpg'
    's3://noaa-auv/main/NOAA-AUV/VIOLA/6000713538/FT_20241016_035449_0_BC0030VB0153.jpg'
    's3://noaa-auv/main/NOAA-AUV/VIOLA/6000713538/FT_20241016_053636_3_BC0030VB0153.jpg'
    's3://noaa-auv/main/NOAA-AUV/VIOLA/6000713538/FT_20241016_060446_0_BC0030VB0153.jpg'
    's3://noaa-auv/main/NOAA-AUV/VIOLA/6000713538/FT_20241016_060443_3_BC0030VB0153.jpg'
    's3://noaa-auv/main/NOAA-AUV/VIOLA/6000713538/FT_20241016_053256_0_BC0030VB0153.jpg'
    's3://noaa-auv/main/NOAA-AUV/VIOLA/6000713538/FT_20241016_042746_0_BC0030VB0153.jpg'
    's3://noaa-auv/main/NOAA-AUV/VIOLA/6000713538/FT_20241016_042439_3_BC0030VB0153.jpg'
    's3://noaa-auv/main/NOAA-AUV/VIOLA/6000713538/FT_20241016_032043_0_BC0030VB0153.jpg'
    's3://noaa-auv/main/NOAA-AUV/VIOLA/6000713538/FT_20241016_040111_0_BC0030VB0153.jpg'
  ]

  rdd = spark.sparkContext.parallelize(uris)

  rows = rdd.map(process_image)

  df = spark.createDataFrame(rows)

  #df.writeTo("lakefs.noaa.auv.image.metadata").append()


  print("✅ Done (stub)")
