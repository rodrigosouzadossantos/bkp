from pyspark.sql import SparkSession

# Initialize Spark Session
spark = SparkSession.builder \
    .appName("HelloWorld") \
    .getOrCreate()

print("\n" + "="*30)
print("HELLO WORLD FROM LOCAL SPARK!")
print("="*30 + "\n")

spark.stop()

