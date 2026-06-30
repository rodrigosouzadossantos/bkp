from pyspark.sql import functions as F


# =========================================================
# 1. Ensure ingestion_state table exists (Iceberg)
# =========================================================
def ensure_ingestion_state_table(spark):
  spark.sql("""
  CREATE TABLE IF NOT EXISTS lakefs.ingestion_state (
    dataset STRING,
    cruise STRING,
    dive STRING,
    status STRING,
    attempt INT,
    start_time TIMESTAMP,
    end_time TIMESTAMP,
    row_count BIGINT,
    error STRING
  )
  USING iceberg
  """)


# =========================================================
# 2. Mark dataset as running
# =========================================================
def mark_running(spark, ds):
  ensure_ingestion_state_table(spark)

  spark.sql(f"""
  INSERT INTO lakefs.ingestion_state
  VALUES (
    '{ds['name']}',
    '{ds['cruise']}',
    '{ds['dive']}',
    'running',
    0,
    current_timestamp(),
    NULL,
    NULL,
    NULL
  )
  """)


# =========================================================
# 3. Mark success
# =========================================================
def mark_success(spark, ds, row_count):
  ensure_ingestion_state_table(spark)

  spark.sql(f"""
  UPDATE lakefs.ingestion_state
  SET status = 'success',
      end_time = current_timestamp(),
      row_count = {row_count}
  WHERE dataset = '{ds['name']}'
    AND cruise = '{ds['cruise']}'
    AND dive = '{ds['dive']}'
  """)


# =========================================================
# 4. Mark failure
# =========================================================
def mark_failed(spark, ds, error):
  ensure_ingestion_state_table(spark)

  safe_error = str(error).replace("'", "''")  # escape SQL quotes

  spark.sql(f"""
  UPDATE lakefs.ingestion_state
  SET status = 'failed',
      end_time = current_timestamp(),
      error = '{safe_error}'
  WHERE dataset = '{ds['name']}'
    AND cruise = '{ds['cruise']}'
    AND dive = '{ds['dive']}'
  """)
