from os import path
from pyspark.sql import SparkSession
from PIL import Image
from io import BytesIO


from src.ingestion.spark_session import create_spark

# -------------------------------------------------------
# 1. Create Spark Session (IMPORTANT: cluster mode)
# -------------------------------------------------------
#spark = SparkSession.builder \
#    .appName("ReadImageFromS3Cluster") \
#    .master("spark://NOCPU162535.localdomain:7077") \
#    .config("spark.driver.maxResultSize", "2g") \
#    .getOrCreate()

#spark.sparkContext.setLogLevel("WARN")

spark = create_spark()

#log4j = spark._jvm.org.apache.log4j
#logger = log4j.LogManager.getRootLogger()
#logger.setLevel(log4j.Level.WARN)

# -------------------------------------------------------
# 2. Configure S3 / MinIO / LakeFS access
#    (runs on ALL executors via Hadoop config)
# -------------------------------------------------------
#hadoop_conf = spark._jsc.hadoopConfiguration()
#
#hadoop_conf.set("fs.s3a.endpoint", "http://localhost:8000")
#hadoop_conf.set("fs.s3a.path.style.access", "true")
#hadoop_conf.set("fs.s3a.access.key", "AKIAJPG2FGB3ZE4VLNGQ")
#hadoop_conf.set("fs.s3a.secret.key", "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")
#hadoop_conf.set("fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem")

# -------------------------------------------------------
# 3. Read image from S3 (distributed file read)
# -------------------------------------------------------
path = [
  's3a://noaa-auv/main/NOAA-AUV/VIOLA/6000713538/FT_20241016_053320_3_BC0030VB0153.jpg',
  's3a://noaa-auv/main/NOAA-AUV/VIOLA/6000713538/FT_20241016_035829_6_BC0030VB0153.jpg',
  's3a://noaa-auv/main/NOAA-AUV/VIOLA/6000713538/FT_20241016_061747_6_BC0030VB0153.jpg',
  's3a://noaa-auv/main/NOAA-AUV/VIOLA/6000713538/FT_20241016_055914_3_BC0030VB0153.jpg',
  's3a://noaa-auv/main/NOAA-AUV/VIOLA/6000713538/FT_20241016_023259_3_BC0030VB0153.jpg',
  's3a://noaa-auv/main/NOAA-AUV/VIOLA/6000713538/FT_20241016_055251_0_BC0030VB0153.jpg',
  's3a://noaa-auv/main/NOAA-AUV/VIOLA/6000713538/FT_20241016_041356_6_BC0030VB0153.jpg',
  's3a://noaa-auv/main/NOAA-AUV/VIOLA/6000713538/FT_20241016_021849_6_BC0030VB0153.jpg',
  's3a://noaa-auv/main/NOAA-AUV/VIOLA/6000713538/FT_20241016_061946_0_BC0030VB0153.jpg',
  's3a://noaa-auv/main/NOAA-AUV/VIOLA/6000713538/FT_20241016_035420_3_BC0030VB0153.jpg',
  's3a://noaa-auv/main/NOAA-AUV/VIOLA/6000713538/FT_20241016_022332_3_BC0030VB0153.jpg',
  's3a://noaa-auv/main/NOAA-AUV/VIOLA/6000713538/FT_20241016_035449_0_BC0030VB0153.jpg',
  's3a://noaa-auv/main/NOAA-AUV/VIOLA/6000713538/FT_20241016_053636_3_BC0030VB0153.jpg',
  's3a://noaa-auv/main/NOAA-AUV/VIOLA/6000713538/FT_20241016_060446_0_BC0030VB0153.jpg',
  's3a://noaa-auv/main/NOAA-AUV/VIOLA/6000713538/FT_20241016_060443_3_BC0030VB0153.jpg',
  's3a://noaa-auv/main/NOAA-AUV/VIOLA/6000713538/FT_20241016_053256_0_BC0030VB0153.jpg',
  's3a://noaa-auv/main/NOAA-AUV/VIOLA/6000713538/FT_20241016_042746_0_BC0030VB0153.jpg',
  's3a://noaa-auv/main/NOAA-AUV/VIOLA/6000713538/FT_20241016_042439_3_BC0030VB0153.jpg',
  's3a://noaa-auv/main/NOAA-AUV/VIOLA/6000713538/FT_20241016_032043_0_BC0030VB0153.jpg',
  's3a://noaa-auv/main/NOAA-AUV/VIOLA/6000713538/FT_20241016_040111_0_BC0030VB0153.jpg',
]
#path = 's3a://noaa-auv/main/NOAA-AUV/VIOLA/6000713538/FT_20241016_05*.jpg'
path = 's3a://noaa-auv/main/NOAA-AUV/VIOLA/6000713538/'

df = spark.read.format("binaryFile").load(path)

# -------------------------------------------------------
# 4. Trigger REAL cluster job
# -------------------------------------------------------
#df.show(5)

#print("Total files:", df.count())

# -------------------------------------------------------
# 5. Extract single image bytes (optional)
# -------------------------------------------------------
#image_bytes = df.select("content").first()[0]

from pyspark.sql import functions as F
N = 20
sample_df = df.select("content").orderBy(F.rand()).limit(N)
rows = sample_df.collect()

#for row in rows:
#  image = Image.open(BytesIO(row['content']))
#  image.show()

N_COLS = 5
THUMB_SIZE = (200, 200)  # size of each tile
BORDER_SIZE = 0          # thickness of border
SPACING = 3              # gap between images
BORDER_COLOR = (0, 0, 0) # black border

from PIL import ImageOps
images = []
for row in rows:
    img = Image.open(BytesIO(row["content"])).convert("RGB")
    img = img.resize(THUMB_SIZE)
    img = ImageOps.expand(img, border=BORDER_SIZE, fill=BORDER_COLOR)
    images.append(img)

import math
n_images = len(images)
n_rows = math.ceil(n_images / N_COLS)

n_images = len(images)
n_rows = math.ceil(n_images / N_COLS)

tile_w, tile_h = images[0].size

mosaic_w = N_COLS * tile_w + (N_COLS + 1) * SPACING
mosaic_h = n_rows * tile_h + (n_rows + 1) * SPACING

mosaic = Image.new("RGB", (mosaic_w, mosaic_h), color=(255, 255, 255))

for idx, img in enumerate(images):
    row = idx // N_COLS
    col = idx % N_COLS

    x = SPACING + col * (tile_w + SPACING)
    y = SPACING + row * (tile_h + SPACING)

    mosaic.paste(img, (x, y))

mosaic.show()


print("Total images:", df.count())

df.select("length").describe().show()
df.summary().show()
# -------------------------------------------------------
# 6. Stop Spark session
# -------------------------------------------------------
spark.stop()
