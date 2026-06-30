from core.logging import get_logger
from core.profiler_instance import PROFILER
from core.metrics import Metrics

from core.io import load_dataset_df
from core.state import mark_running, mark_success, mark_failed

import time
from pyspark.sql import functions as F

logger = get_logger()


def build_plan(config):
  def build_dataset_path(ds):
    parts = []

    cruise = ds.get("cruise")
    if cruise is not None:
      parts.append(str(cruise))

    dive = ds.get("dive")
    if dive:
      parts.append(dive)

    return "/".join(parts) + "/"

  plan = []

  for d in config["datasets"]:
    base = config["paths"][d["name"]]

    path = f"{base}/{build_dataset_path(d)}"

    plan.append({
      "name": d["name"],
      "cruise": d["cruise"],
      "dive": d["dive"],
      "path": path,
      "cfg": d
    })

  return plan


def run_dataset(spark, ds, features, schema, process_partition):

  metrics = Metrics()
  t0 = time.time()

  logger.info(f"[DATASET START] {ds['name']} | cruise={ds.get('cruise')} dive={ds.get('dive')}")

  # --------------------------------------------------
  # 1. LOAD
  # --------------------------------------------------
  t_load = time.time()

  df = load_dataset_df(spark, ds["path"], ds["cfg"])

  load_time = time.time() - t_load
  metrics.inc("load_ok")

  logger.info({
      "stage": "load",
      "dataset": ds["name"],
      "load_time_sec": load_time
  })

  # --------------------------------------------------
  # 2. TRANSFORM (FEATURE EXECUTION)
  # --------------------------------------------------
  t_transform = time.time()

  #compiled_features = [
  #  {"name": f.name, "extract": f.extract}
  #  for f in features
  #]

  ##df.show( )

  #df_count = df.count()
  #fraction = 100 / df_count
  #df = df.sample(fraction=fraction, seed=42)

  ##print('>>> #',df_count)
  ##print('>>> #',df.count())

  from typing import Any, Dict, List, Tuple
  from pyspark.sql.types import (
      StructType,
      DataType,
      StructField,
      StringType,
      DoubleType,
      LongType,
      BooleanType,
      ArrayType,
  )

  def dict_to_schema(d, name):

      if isinstance(d, dict):

          return StructField(
              name,
              StructType([
                  dict_to_schema(v, k)
                  for k, v in d.items()
              ]),
              True
          )

      if isinstance(d, list):

          if len(d) == 0:
              return StructField(name, ArrayType(StringType()), True)

          first = d[0]

          if isinstance(first, dict):
              element_type = StructType([
                  dict_to_schema(v, k)
                  for k, v in first.items()
              ])
          else:
              element_type = StringType()

          return StructField(name, ArrayType(element_type), True)

      if isinstance(d, bool):
          dtype = BooleanType()

      elif isinstance(d, int):
          dtype = LongType()

      elif isinstance(d, float):
          dtype = DoubleType()

      else:
          dtype = StringType()

      return StructField(name, dtype, True)

  rdd = ( df
    .select("path", "content")
    .rdd.mapPartitions(
      process_partition
    )
  )


  import pyspark.sql.types as pst
  def infer_schema(rec):
    """infers dataframe schema for a record. Assumes every dict is a Struct, not a Map"""
    if isinstance(rec, dict):
      return StructType([
        StructField(key, infer_schema(value), True)
          for key, value in sorted(rec.items())
      ])
    elif isinstance(rec, list):
      if len(rec) == 0:
        raise ValueError("can't infer type of an empty list")
      elem_type = infer_schema(rec[0])
      for elem in rec:
        this_type = infer_schema(elem)
        if elem_type != this_type:
          raise ValueError("can't infer type of a list with inconsistent elem types")
      return ArrayType(elem_type)
    else:
      if isinstance(rec, bool):
        dtype = BooleanType()

      elif isinstance(rec, int):
        dtype = LongType()

      elif isinstance(rec, float):
        dtype = DoubleType()

      else:
        dtype = StringType()

      return StructField(name, dtype, True)


  def merge_structtypes(a, b):
    fields = {f.name: f for f in a.fields}

    for f in b.fields:
        if f.name not in fields:
            fields[f.name] = f

    return StructType(list(fields.values()))


  def infer_type(value):

    if isinstance(value, dict):

        struct = StructType()

        for k, v in value.items():
            struct = merge_structtypes(
                struct,
                StructType([StructField(k, infer_type(v), True)])
            )

        return struct

    elif isinstance(value, list):

        if not value:
            return ArrayType(StringType())

        elem_type = infer_type(value[0])

        for elem in value[1:]:
            next_type = infer_type(elem)

            if isinstance(elem_type, StructType) and isinstance(next_type, StructType):
                elem_type = merge_structtypes(elem_type, next_type)

        return ArrayType(elem_type)

    elif isinstance(value, bool):
        return BooleanType()

    elif isinstance(value, int):
        return LongType()

    elif isinstance(value, float):
        return DoubleType()

    else:
        return StringType()


  def compare(schema, data, path="root"):

      errors = []

      # STRUCT
      if isinstance(schema, StructType):

          if not isinstance(data, dict):
              errors.append(f"{path}: expected dict, got {type(data).__name__}")
              return errors

          schema_fields = {f.name: f for f in schema.fields}

          # missing fields
          for name, field in schema_fields.items():

              if name not in data:
                  errors.append(f"{path}.{name}: missing field")
                  continue

              errors.extend(
                  compare(field.dataType, data[name], f"{path}.{name}")
              )

          # extra fields
          for name in data.keys():
              if name not in schema_fields:
                  errors.append(f"{path}.{name}: extra field")

      # ARRAY
      elif isinstance(schema, ArrayType):

          if not isinstance(data, list):
              errors.append(f"{path}: expected list, got {type(data).__name__}")
              return errors

          for i, item in enumerate(data):
              errors.extend(
                  compare(schema.elementType, item, f"{path}[{i}]")
              )

      # PRIMITIVES
      else:

          expected = schema.simpleString()

          type_map = {
              "string": str,
              "bigint": int,
              "long": int,
              "double": float,
              "boolean": bool,
          }

          expected_type = type_map.get(expected)

          if data is not None and expected_type:

              if not isinstance(data, expected_type):
                  errors.append(
                      f"{path}: expected {expected}, got {type(data).__name__}"
                  )

      return errors

  #schema = StructType([
  #    dict_to_schema(v, k)
  #    for k, v in rdd.first().asDict(recursive=True).items()
  #  ])
  sample = rdd.first().asDict(recursive=True)
  schema = StructType([
    StructField(k, infer_type(v), True)
    for k, v in sample.items()
  ])

  #print(schema)
  #print(sample)

  #errors = compare(schema, sample)
  #for e in errors:
  #  print(f">>> COMPARE_ERROR: {e}")

  out = spark.createDataFrame( rdd,schema)
  #  rdd,
  #  StructType([
  #    dict_to_schema(v, k)
  #    for k, v in rdd.first().asDict(recursive=True).items()
  #  ])
  #)

  def _display(df):
     # Assumes 'self.df' is available within the class
     row = df.take(1)[0].asDict(recursive=True)
     lines = []

     def recurse(d, indent=0):
         for k, v in d.items():
             prefix = " |    " * indent + " |-- "
             if isinstance(v, dict):
                 lines.append(f"{prefix}{k}:")
                 recurse(v, indent + 1)
             else:
                 lines.append(f"{prefix}{k}: {v}")

     recurse(row)
     return "\n".join(lines)


  def display(df):

      row = df.take(1)[0].asDict(recursive=True)
      schema = df.schema

      lines = ["root"]

      def recurse(data, data_type, indent=1):

          pad = " |    " * indent

          if isinstance(data_type, StructType):

              for field in data_type.fields:

                  value = data.get(field.name) if isinstance(data, dict) else None

                  lines.append(f"{pad} |-- {field.name}: {type_name(field.dataType)} = {value_repr(value)}")

                  recurse(value, field.dataType, indent + 1)

          elif isinstance(data_type, ArrayType):

              if data is None:
                  lines.append(f"{pad} |-- element: null")
                  return

              for i, item in enumerate(data):

                  lines.append(f"{pad} |-- [{i}]: {type_name(data_type.elementType)}")

                  recurse(item, data_type.elementType, indent + 1)

          #else:
          #    lines.append(f"{pad}{value_repr(data)}")

      def type_name(dt):
          if isinstance(dt, StructType): return "struct"
          if isinstance(dt, ArrayType): return "array"
          if isinstance(dt, StringType): return "string"
          if isinstance(dt, LongType): return "long"
          if isinstance(dt, DoubleType): return "double"
          if isinstance(dt, BooleanType): return "boolean"
          return str(dt)

      def value_repr(v):
          if isinstance(v, (dict, list)):
              return ""  # handled recursively
          return v

      recurse(row, schema)

      return "\n".join(lines)



  #out.printSchema()
  #print(display(out))

  #out.show( 10,
  #  truncate=False,
  #  vertical=True
  #)

  ###
  #from core.pandas_partition import pandas_partition

  #compiled_features = [
  #  {"name": f.name, "extract": f.extract}
  #  for f in features
  #]

  #out = (
  #  df
  #  #.sample(fraction=fraction, seed=42)
  #  .select("path", "content")
  #  .mapInPandas(
  #      pandas_partition(compiled_features),
  #      schema=schema
  #  )
  #)

  transform_time = time.time() - t_transform
  metrics.inc("transform_ok")

  # --------------------------------------------------
  # 3. ENRICH METADATA
  # --------------------------------------------------
  #out = out \
  #  .withColumn("dataset", F.lit(ds["name"])) \
  #  .withColumn("cruise", F.lit(ds["cruise"])) \
  #  .withColumn("dive", F.lit(ds["dive"]))

  # --------------------------------------------------
  # 4. ACTION (TRIGGERS EXECUTION)
  # --------------------------------------------------
  t_action = time.time()

  #row_count = out.count()
  row_count = 0

  action_time = time.time() - t_action
  metrics.inc("action_ok")

  # --------------------------------------------------
  # 5. WRITE TO ICEBERG
  # --------------------------------------------------
  t_write = time.time()

  #(
  #out.writeTo(f'lakefs.images_test.{ds["name"]}') \
  #  .using("iceberg") \
  #  .createOrReplace()
  #)

  spark.sparkContext.setCheckpointDir("/tmp/chk")

  out = out.checkpoint(eager=True)

  print(">>> NumPartitions", out.rdd.getNumPartitions())

  #sizes = out.rdd.mapPartitions(lambda it: [sum(1 for _ in it)]).collect()
  #print(f"MIN: {min(sizes)}, MAX: {max(sizes)}, AVG: {sum(sizes)/len(sizes)}")

  table = f"lakefs.images_full.{ds['name']}"

  if not spark.catalog.tableExists(table):
    (
      out
        .coalesce(2048)
        .writeTo(table)
        .using("iceberg")
        #.tableProperty("write.format.default", "parquet")
        #.partitionedBy("cruise", "dive")   # example
        .create()
    )
  else:
    (
      out
        .coalesce(2048)
        .writeTo(table)
        .append()
    )

  write_time = time.time() - t_write
  metrics.inc("write_ok")

  # --------------------------------------------------
  # 6. FEATURE PROFILING SNAPSHOT
  # --------------------------------------------------
  feature_profile = PROFILER.snapshot()

  slowest_features = sorted(
      feature_profile.items(),
      key=lambda x: x[1]["total_time"],
      reverse=True
  )[:5]

  # --------------------------------------------------
  # 7. TOTAL TIME
  # --------------------------------------------------
  total_time = time.time() - t0

  # --------------------------------------------------
  # 8. LOGGING SUMMARY
  # --------------------------------------------------
  logger.info({
      "stage": "dataset_complete",
      "dataset": ds["name"],
      "row_count": row_count,
      "timings": {
          "load_sec": load_time,
          "transform_sec": transform_time,
          "action_sec": action_time,
          "write_sec": write_time,
          "total_sec": total_time
      },
      "metrics": metrics.report(),
      "slowest_features": slowest_features
  })

  # --------------------------------------------------
  # 9. RETURN
  # --------------------------------------------------
  return row_count
