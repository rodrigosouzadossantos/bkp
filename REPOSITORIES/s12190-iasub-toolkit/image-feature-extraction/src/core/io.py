def load_dataset_df(spark, path, cfg):
  reader = spark.read.format(cfg["read"]["file_format"])

  if cfg["read"].get("recursive"):
    reader = reader.option("recursiveFileLookup", "true")

  if cfg["read"].get("glob_filter"):
    reader = reader.option("pathGlobFilter", cfg["read"]["glob_filter"])

  return reader.load(path)
