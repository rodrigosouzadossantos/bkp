from .ingestion.spark_session import create_spark


def main():
  spark = create_spark()
  spark.sparkContext.setLogLevel("ERROR")

  print('__INIT__')

  print('>> spark.version: ', spark.version)
  print('>> hadoop.util.VersionInfo: ', spark._jvm.org.apache.hadoop.util.VersionInfo.getVersion())
  print('>> spark.jars', spark.sparkContext._conf.get("spark.jars"))

  df = spark.table("lakefs.test.viola")
  
  df.printSchema()

  df.show()

  #spark.read.table('lakefs.db.my_table').show()

  #spark.read.table('lakefs.noaa.auv.image.metadata').show()
  #spark.read.text("s3a://iceberg/main/").show()

  #spark.sql("DESCRIBE EXTENDED lakefs.noaa.auv.image.metadata").select('col_name','data_type').show( 100, truncate=False)

  #spark.sql("""
  #  SELECT * 
  #  FROM lakefs.noaa.auv.image.metadata.snapshots
  #""").show(truncate=False)

  #spark.sql("""
  #  SELECT *
  #  FROM lakefs.noaa.auv.image.metadata.files
  #""").show(truncate=False)



  #spark.sql("DESCRIBE EXTENDED lakefs.db.my_table").show(truncate=False)

  #spark.sql("""
  #  SELECT * 
  #  FROM lakefs.db.my_table.snapshots
  #""").show(truncate=False)

  #spark.sql("""
  #  SELECT *
  #  FROM lakefs.db.my_table.files
  #""").show(truncate=False)






  #data = [(1, "Alice-01"), (2, "Bob-02")]
  #df = spark.createDataFrame(data, ["id", "name"])

  #df.writeTo("lakefs.db.my_table") \
  #  .using("iceberg") \
  #  .createOrReplace()



  print('__DONE__')


if __name__ == "__main__":
  main()
