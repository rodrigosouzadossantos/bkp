from pyspark.sql import SparkSession

spark = SparkSession.builder \
    .master("spark://NOCPU162535.localdomain:7077") \
    .appName("stress-test") \
    .getOrCreate()

rdd = spark.sparkContext.parallelize(range(10_000_000), 8)

print(rdd.map(lambda x: x % 10).count())

spark.stop()
