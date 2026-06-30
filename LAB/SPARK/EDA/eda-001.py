from pyspark.sql import SparkSession
import numpy as np
import cv2
import xml.etree.ElementTree as ET
from pyspark.sql import Row


# =========================================================
# 1. SPARK SESSION
# =========================================================

#spark = (
#    SparkSession.builder
#    .appName("subsea-eda-local")
#    .config("spark.sql.shuffle.partitions", "200")
#    .config("spark.driver.memory", "4g")
#    .getOrCreate()
#)

# AWS profile based auth
spark = (
  SparkSession.builder
    .appName("subsea-eda-s3-profile")
    .config("spark.default.parallelism", "50")
    .config("spark.driver.memory", "4g")
    .config("spark.driver.extraClassPath",
            "/opt/spark/jars/*")
    .config("spark.executor.extraClassPath",
            "/opt/spark/jars/*")
    .config("spark.sql.files.maxPartitionBytes", "64MB")
    .config("spark.sql.shuffle.partitions", "50")
    .config("spark.hadoop.fs.s3a.impl",
            "org.apache.hadoop.fs.s3a.S3AFileSystem")
    .config("spark.hadoop.fs.s3a.aws.credentials.provider",
            "com.amazonaws.auth.DefaultAWSCredentialsProviderChain")
    .config("spark.hadoop.fs.s3a.path.style.access", "true")

    .getOrCreate()
)

# =========================================================
# 2. LOAD IMAGES
# =========================================================

#DATA_PATH = "/mnt/SGO/sub/hidrografia/"

#df = spark.read.format("binaryFile") \
#    .option("recursiveFileLookup", "true") \
#    .load(DATA_PATH)

DATA_PATH = (
  "s3a://analise-dados/"
  "projeto-ia-submarina/ia-frente-ambiental/"
  "NOAA-AUV/VIOLA/6000713538/"
)

df = (
  spark.read.format("binaryFile")
    #.option("recursiveFileLookup", "true")
    .option("pathGlobFilter", "*.jpg")
    .load(DATA_PATH)
)

# =========================================================
# 3. XML EXTRACTION
# =========================================================
def extract_xml(raw_bytes: bytes):
  try:
    text = raw_bytes.decode("utf-8", errors="ignore")

    start = text.find("<image")
    end = text.find("</image>")

    if start == -1 or end == -1:
        return None

    xml_str = text[start:end + 8]
    return ET.fromstring(xml_str)

  except Exception:
    return None


def parse_xml(xml):
  if xml is None:
    return None

  try:
    pos = xml.find(".//Position")
    coords = pos.find(".//Coords")
    depth = pos.find(".//Depth")
    direction = pos.find(".//Direction")

    return {
      "lat": float(coords.attrib.get("lat")),
      "lon": float(coords.attrib.get("long")),
      "depth": float(depth.attrib.get("depth")),
      "altitude": float(depth.attrib.get("altitude")),
      "pitch": float(direction.attrib.get("pitch")),
      "roll": float(direction.attrib.get("roll")),
      "yaw": float(direction.attrib.get("yaw")),
    }

  except Exception:
    return None


# =========================================================
# 4. IMAGE FEATURE EXTRACTION
# =========================================================
def extract_features(img):
  gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

  brightness = float(np.mean(gray))
  contrast = float(np.std(gray))
  blur = float(cv2.Laplacian(gray, cv2.CV_64F).var())

  entropy = float(-np.sum((gray / 255.0) * np.log2((gray / 255.0) + 1e-6)))

  b, g, r = cv2.mean(img)[:3]
  color_ratio = float(b / (r + g + 1e-6))

  return brightness, contrast, blur, entropy, color_ratio


# =========================================================
# 5. PARTITION PROCESSING (CORE LOGIC)
# =========================================================
def process_partition(rows):
  for row in rows:
    try:
      raw = row.content

      # ---------------------------
      # decode image
      # ---------------------------
      img_array = np.frombuffer(raw, np.uint8)
      img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)

      if img is None:
          continue

      h, w, _ = img.shape

      brightness, contrast, blur, entropy, color_ratio = extract_features(img)

      # ---------------------------
      # metadata
      # ---------------------------
      xml = extract_xml(raw)
      meta = parse_xml(xml)

      if meta is None:
        meta = {
          "lat": None,
          "lon": None,
          "depth": None,
          "altitude": None,
          "pitch": None,
          "roll": None,
          "yaw": None,
        }

      yield Row(
        path=row.path,
        width=w,
        height=h,
        brightness=brightness,
        contrast=contrast,
        blur=blur,
        entropy=entropy,
        blue_ratio=color_ratio,
        lat=meta["lat"],
        lon=meta["lon"],
        depth=meta["depth"],
        altitude=meta["altitude"],
        pitch=meta["pitch"],
        roll=meta["roll"],
        yaw=meta["yaw"],
      )

    except Exception:
      continue


# =========================================================
# 6. RUN SPARK PIPELINE
# =========================================================
rdd = df.select("path", "content").rdd.repartition(200)

features_rdd = rdd.mapPartitions(process_partition)

features_df = spark.createDataFrame(features_rdd)


# =========================================================
# 7. EDA
# =========================================================
features_df.cache()

print("\n=== BASIC STATS ===")
features_df.describe().show()

print("\n=== DEPTH SUMMARY ===")
features_df.select(
  "depth", "brightness", "contrast", "blur"
).summary().show()

print("\n=== SAMPLE DATA ===")
features_df.show(10, truncate=False)


# =========================================================
# 8. SAVE LOCALLY
# =========================================================
OUT_DIR = "./output/subsea_eda"

features_df.write.mode("overwrite").parquet(OUT_DIR + "/parquet")
features_df.write.mode("overwrite").csv(OUT_DIR + "/csv", header=True)

print(f"\nSaved to: {OUT_DIR}")


# =========================================================
# 9. SIMPLE CLUSTERING PREVIEW
# =========================================================
from pyspark.ml.feature import VectorAssembler
from pyspark.ml.clustering import KMeans

vec = VectorAssembler(
  inputCols=["brightness", "contrast", "blur", "depth"],
  outputCol="features"
)

data = vec.transform(features_df).na.drop()

kmeans = KMeans(k=5, seed=42)
model = kmeans.fit(data)

clusters = model.transform(data)

print("\n=== CLUSTER SAMPLE ===")
clusters.select("path", "prediction").show(20, False)


# =========================================================
# DONE
# =========================================================
spark.stop()
