from pyspark.sql import SparkSession

def load_conf(path="config/spark.conf") -> dict:
  confs = {}
  with open(path) as f:
    for line in f:
      line = line.strip()
      if not line or line.startswith("#"):
        continue
      if "=" not in line:
        continue
      k, v = line.split("=", 1)
      confs[k.strip()] = v.strip().strip("'\"")
  return confs

def create_spark():
  confs = load_conf()

  builder = SparkSession.builder.appName("image-iceberg")

  for k, v in confs.items():
    builder = builder.config(k, v)

  return builder.master("local[*]").getOrCreate()
