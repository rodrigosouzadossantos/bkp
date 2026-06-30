from pyspark.sql import SparkSession
from pyspark.sql.functions import col
import time

spark = SparkSession.builder \
    .appName("df-join") \
    .master("spark://NOCPU162535.localdomain:7077") \
    .getOrCreate()

start = time.time()

df1 = spark.range(0, 5_000_000).withColumnRenamed("id", "key").withColumn("a", col("key") * 2)
df2 = spark.range(0, 5_000_000).withColumnRenamed("id", "key").withColumn("b", col("key") * 3)

joined = df1.join(df2, "key")

print(joined.count())

print("Spark DF join time:", time.time() - start)

spark.stop()
