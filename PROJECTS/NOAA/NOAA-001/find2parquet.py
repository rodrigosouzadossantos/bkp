import polars as pl
import os

df = pl.read_csv(
    "6000713538.txt",
    has_header=False
  ).rename({"column_1": "path"})

df = df.with_columns(
  pl.col("path")
    .map_elements(os.path.basename)
    .alias("image_id")
)

df.write_parquet("6000713538.parquet", compression="zstd")
