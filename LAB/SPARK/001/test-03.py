from pyspark.sql import SparkSession

spark = SparkSession.builder \
    .appName("parallel-test") \
    .master("spark://NOCPU162535.localdomain:7077") \
    .getOrCreate()

rdd = spark.sparkContext.parallelize(range(1000000), 8)

print(rdd.map(lambda x: x * 2).sum())

spark.stop()
