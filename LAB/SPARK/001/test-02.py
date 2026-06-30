from pyspark.sql import SparkSession

spark = SparkSession.builder \
    .appName("DataFrameTest") \
    .master("spark://NOCPU162535.localdomain:7077") \
    .getOrCreate()

df = spark.createDataFrame([
    ("Alice", 1),
    ("Bob", 2),
    ("Charlie", 3)
], ["name", "value"])

df = df.withColumn("double", df["value"] * 2)

df.show()

spark.stop()
