from pyspark.sql import SparkSession

spark = (
    SparkSession.builder
    .appName("EDA-S3")
    .config(
        "spark.jars.packages",
        "org.apache.hadoop:hadoop-aws:3.5.0,"
        "com.amazonaws:aws-java-sdk-bundle:1.12.262"
    )
    .getOrCreate()
)

print("Spark started with S3 support")

