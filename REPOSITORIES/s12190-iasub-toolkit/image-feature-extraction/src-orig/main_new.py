import yaml

from ingestion.spark_session import create_spark
from core.registry import load_features
from core.schema import build_schema
from core.pipeline import process_partition


PATH = 's3a://noaa-auv/main/NOAA-AUV/ESPADARTE/6000702270/COM20240425/'


def main():
  spark = create_spark()

  config = yaml.safe_load(open("config/config.yaml"))

  features = load_features(config)
  schema = build_schema(features)

  #df = (
  #  spark.read
  #  .format("binaryFile")
  #  .option("recursiveFileLookup", "true")
  #  .option("pathGlobFilter", "*.tif")
  #  .load(PATH)
  #)

  #rdd = (
  #  df.select("path", "content")
  #  .rdd.mapPartitions(process_partition(features, schema))
  #)

  #df_out = spark.createDataFrame(rdd, schema)

  #df_out.writeTo("lakefs.images.espadarte") \
  #  .using("iceberg") \
  #  .createOrReplace()


if __name__ == "__main__":
  main()
