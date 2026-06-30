from pyspark.sql import SparkSession
import time

spark = SparkSession.builder \
    .master("spark://NOCPU162535.localdomain:7077") \
    .appName("compare-test") \
    .getOrCreate()

start = time.time()

rdd = spark.sparkContext.parallelize(range(100_000_000), 8)

result = rdd.map(lambda x: (x % 100, x * x)).count()

print("Result:", result)
print("Time (Spark):", time.time() - start)

spark.stop()
