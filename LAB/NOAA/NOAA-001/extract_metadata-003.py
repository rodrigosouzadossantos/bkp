from pyspark.sql import SparkSession
from pyspark.sql.functions import col
import re

# ----------------------------
# Spark session (XML enabled)
# ----------------------------
spark = (
    SparkSession.builder
    .appName("Exif Flatten")
    .config("spark.jars.packages", "com.databricks:spark-xml_2.12:0.18.0")
    .getOrCreate()
)

# ----------------------------
# LOAD DATA (XML is mandatory)
# ----------------------------
# If your input is XML:
df = (
    spark.read.format("xml")
    .option("rowTag", "root")   # adjust if needed
    .load("input.xml")
)

# ----------------------------
# PRINT SCHEMA (NO SHOW)
# ----------------------------
print("\n========== SCHEMA ==========\n")
df.printSchema()

# ----------------------------
# FIXED KEY SPLITTER
# supports ":" OR "_"
# ----------------------------
def split_key(key: str):
    # split on ":" or "_"
    return [p for p in re.split(r"[:_]", key) if p]


# ----------------------------
# FLATTEN FUNCTION (STRUCT SAFE)
# ----------------------------
def flatten_df(df):
    complex_fields = True

    while complex_fields:
        complex_fields = False
        cols = []

        for field in df.schema.fields:
            name = field.name
            dtype = field.dataType

            # STRUCT → expand
            if str(dtype).startswith("StructType"):
                complex_fields = True
                expanded = [
                    col(f"{name}.{child.name}").alias(f"{name}_{child.name}")
                    for child in dtype.fields
                ]
                cols.extend(expanded)

            else:
                cols.append(col(name))

        df = df.select(*cols)

    return df


# ----------------------------
# FLATTEN DATAFRAME
# ----------------------------
flat_df = flatten_df(df)

# ----------------------------
# OPTIONAL: CLEAN COLUMN NAMES
# (handles ":" and "_" normalization)
# ----------------------------
def normalize_columns(df):
    for c in df.columns:
        new_name = re.sub(r"[:]", "_", c)
        df = df.withColumnRenamed(c, new_name)
    return df

flat_df = normalize_columns(flat_df)

# ----------------------------
# FINAL SCHEMA ONLY OUTPUT
# ----------------------------
print("\n========== FLATTENED SCHEMA ==========\n")
flat_df.printSchema()
