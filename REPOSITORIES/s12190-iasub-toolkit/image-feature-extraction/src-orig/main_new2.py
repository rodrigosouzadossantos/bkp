import yaml

from ingestion.spark_session import create_spark

from core.registry import load_features
from core.schema import build_schema
from core.pipeline import process_partition
from core.orchestrator import build_plan, run_dataset
from core.state import (
  mark_running,
  mark_success,
  mark_failed
)

from core.logging import get_logger

logger = get_logger()


# =========================================================
# Retry wrapper (dataset-level)
# =========================================================
def run_with_retry(spark, ds, features, schema, fn, max_retries=3):
  import time

  for attempt in range(max_retries):
    try:
      logger.info(f"Starting dataset={ds['name']} attempt={attempt + 1}")

      mark_running(spark, ds)

      rows = fn()

      mark_success(spark, ds, rows)

      return rows

    except Exception as e:
      logger.error(f"Dataset failed: {ds['name']} error={e}")

      if attempt == max_retries - 1:
        mark_failed(spark, ds, str(e))
        raise

      time.sleep(5 * (attempt + 1))


# =========================================================
# MAIN ENTRYPOINT
# =========================================================
def main():

  # -----------------------------------------
  # Load configuration
  # -----------------------------------------
  config = yaml.safe_load(open("config/config.yaml"))

  # -----------------------------------------
  # Build feature pipeline
  # -----------------------------------------
  features = load_features(config)
  schema = build_schema(features)

  # -----------------------------------------
  # Build dataset execution plan
  # -----------------------------------------
  plan = build_plan(config)

  results = []

  # -----------------------------------------
  # Sequential dataset execution (safe mode)
  # -----------------------------------------
  spark = create_spark()

  for ds in plan:

    def job():
      return run_dataset(
        spark=spark,
        ds=ds,
        features=features,
        schema=schema,
        process_partition=process_partition(features)
      )

    rows = run_with_retry(
      spark=spark,
      ds=ds,
      features=features,
      schema=schema,
      fn=job
    )

    results.append({
      "dataset": ds["name"],
      "rows": rows
    })

    logger.info(f"Finished dataset={ds['name']} rows={rows}")

  # -----------------------------------------
  # Final summary
  # -----------------------------------------
  logger.info("PIPELINE COMPLETED")
  logger.info(results)


# =========================================================
# ENTRY
# =========================================================
if __name__ == "__main__":
  main()
