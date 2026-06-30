from pyspark.sql.types import StructType, StructField, StringType


def build_schema(features):
  fields = [
    StructField("path", StringType(), True),
    #StructField("dataset", StringType(), True),
    #StructField("cruise", StringType(), True),
    #StructField("dive", StringType(), True),
  ]

  for f in features:
    for col, dtype in f.schema().items():
      fields.append(StructField(col, dtype, True))

  return StructType(fields)
