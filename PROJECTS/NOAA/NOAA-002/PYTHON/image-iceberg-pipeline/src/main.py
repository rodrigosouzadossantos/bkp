from re import I
from ingestion.spark_session import create_spark
#from ingestion.ingest import run_ingestion

from pyspark.sql import functions as F
import math
from PIL import Image, ImageOps
from io import BytesIO


PATH = 's3a://noaa-auv/main/NOAA-AUV/VIOLA/6000713538/'
N = 10
N_COLS = 5
THUMB_SIZE = (200, 200)  # size of each tile
BORDER_SIZE = 0          # thickness of border
SPACING = 3              # gap between images
BORDER_COLOR = (0, 0, 0) # black border


def main():
  spark = create_spark()
  #run_ingestion(spark)

  #df = spark.read.format("binaryFile").load(
  #  "s3a://noaa-auv/main/NOAA-AUV/VIOLA/6000713538/FT_20241016_053320_3_BC0030VB0153.jpg"
  #)

  #df.show()
  #df.select("path").show(truncate=False)

  #image_data = df.select("content").collect()[0][0]

  #image = Image.open(BytesIO(image_data))
  #image.show()


  df = (
    spark.read
    .format("binaryFile")
    .load(PATH)
    .filter("path LIKE '%.jpg'")
  )

  df = df.withColumn("id", F.monotonically_increasing_id())

  df.show(5)

  def process_batch(rows):
    print(f"Processing batch of {len(rows)} images")

  BATCH_SIZE = 20
  start = 0

  while True:
    batch_df = df.filter(
      (F.col("id") >= start) &
      (F.col("id") < start + BATCH_SIZE)
    )

    rows = batch_df.select("content", "path").collect()

    if not rows:
      break

    # process batch
    process_batch(rows)

    start += BATCH_SIZE


  #rows = (
  #  df.select("content", "path")
  #    .rdd.takeSample(False, N)
  #)

  #sample_df = (
  #  df.orderBy(F.rand()).limit(N)
  #)

  #rows = sample_df.select('content').toLocalIterator()
  #images = []
  #for row in rows:
  #    img = Image.open(BytesIO(row["content"])).convert("RGB")
  #    img = img.resize(THUMB_SIZE)
  #    img = ImageOps.expand(img, border=BORDER_SIZE, fill=BORDER_COLOR)
  #    images.append(img)


  #def process_image(row):
  #  from PIL import Image, ImageOps
  #  from io import BytesIO
  #  import io

  #  img = Image.open(BytesIO(row.content)).convert("RGB")
  #  img = img.resize(THUMB_SIZE)
  #  img = ImageOps.expand(img, border=BORDER_SIZE,
  #                                fill=BORDER_COLOR)
  #  buf = io.BytesIO()
  #  img.save(buf, format='JPEG', quality=85)
  #  return buf.getvalue()

  #rows_iter = sample_df.rdd.map(process_image).toLocalIterator()
  ##images = [Image.open(BytesIO(row)) for row in rows_iter]
  #images = []
  #for b in rows_iter:
  #  images.append(Image.open(BytesIO(b)))

  #n_images = len(images)
  #n_rows = math.ceil(n_images / N_COLS)

  #n_images = len(images)
  #n_rows = math.ceil(n_images / N_COLS)

  #tile_w, tile_h = images[0].size

  #mosaic_w = N_COLS * tile_w + (N_COLS + 1) * SPACING
  #mosaic_h = n_rows * tile_h + (n_rows + 1) * SPACING

  #mosaic = Image.new("RGB", (mosaic_w, mosaic_h), color=(255, 255, 255))

  #for idx, img in enumerate(images):
  #    row = idx // N_COLS
  #    col = idx % N_COLS

  #    x = SPACING + col * (tile_w + SPACING)
  #    y = SPACING + row * (tile_h + SPACING)

  #    mosaic.paste(img, (x, y))

  #mosaic.show()

  #print("Total images:", df.count())

  #df.select("length").describe().show()
  #df.summary().show()

  #rows = df.sample(0.01).collect()

  #images = []
  #for row in rows:
  #  img = Image.open(BytesIO(row["content"])).convert("RGB")
  #  img = img.resize(THUMB_SIZE)
  #  img = ImageOps.expand(img, border=BORDER_SIZE, fill=BORDER_COLOR)
  #  images.append(img)

  #n_images = len(images)
  #n_rows = math.ceil(n_images / N_COLS)



if __name__ == "__main__":
  main()
