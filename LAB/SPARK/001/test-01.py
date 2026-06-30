from pyspark.sql import SparkSession

spark = SparkSession.builder \
    .appName("SparkTest") \
    .master("spark://NOCPU162535.localdomain:7077") \
    .getOrCreate()

data = [1, 2, 3, 4, 5, 6]

rdd = spark.sparkContext.parallelize(data, 3)

result = rdd.map(lambda x: x * x).collect()

print("Squares:", result)

spark.stop()
