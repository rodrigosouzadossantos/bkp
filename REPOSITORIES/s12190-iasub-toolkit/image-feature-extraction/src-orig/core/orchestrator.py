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

  df.show( )
  print('#',df.count())

  # --------------------------------------------------
  # 2. TRANSFORM (FEATURE EXECUTION)
  # --------------------------------------------------
  t_transform = time.time()

  #compiled_features = [
  #  {"name": f.name, "extract": f.extract}
  #  for f in features
  #]

  #fraction = 100 / df.count()
  #rdd = ( df
  #  #.sample(fraction=fraction, seed=42)
  #  .select("path", "content")
  #  .rdd.mapPartitions(
  #    process_partition
  #  )
  #)

  #out = spark.createDataFrame(rdd, schema)

  from core.pandas_partition import pandas_partition

  compiled_features = [
    {"name": f.name, "extract": f.extract}
    for f in features
  ]

  out = (
    df
    #.sample(fraction=fraction, seed=42)
    .select("path", "content")
    .mapInPandas(
        pandas_partition(compiled_features),
        schema=schema
    )
  )

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

  row_count = out.count()
  #row_count = 0

  action_time = time.time() - t_action
  metrics.inc("action_ok")

  # --------------------------------------------------
  # 5. WRITE TO ICEBERG
  # --------------------------------------------------
  t_write = time.time()

  (
  #out.writeTo(f'lakefs.images.{ds["name"]}') \
  #  .using("iceberg") \
  #  .createOrReplace()
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
  out.show(10)
  return row_count
