import logging

from pyspark import TaskContext


class SparkPartitionFilter(logging.Filter):
  def filter(self, record):
    tc = TaskContext.get()

    record.partition_id = tc.partitionId() if tc else -1
    record.stage_id = tc.stageId() if tc else -1
    record.task_attempt = tc.taskAttemptId() if tc else -1

    return True

def get_logger():
  logger = logging.getLogger("image_feature_pipeline")
  logger.setLevel(logging.INFO)

  if not logger.handlers:
    handler = logging.StreamHandler()
    #handler = logging.FileHandler("python.log")

    formatter = logging.Formatter(
      "%(asctime)s [stage=%(stage_id)s partition=%(partition_id)s attempt=%(task_attempt)s] %(message)s"
    )

    handler.setFormatter(formatter)
    handler.addFilter(SparkPartitionFilter())

    logger.addHandler(handler)

  return logger
