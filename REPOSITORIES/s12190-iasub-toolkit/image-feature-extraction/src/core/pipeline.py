from core.context import build_context
from core.metrics import Metrics
from core.logging import get_logger

import time
from pyspark.sql import Row

logger = get_logger()


def process_partition(features, max_retries=0):
  def _inner(iterator):
    from core.profiler_instance import PROFILER

    metrics = Metrics()

    for row in iterator:
      for attempt in range(max_retries + 1):

        try:

          ctx = build_context(row)
          result = {"path": ctx["path"]}

          for f in features:
              start = time.time()
              try:
                result.update(f.extract(ctx))
                metrics.inc(f"{f.name}_ok")
              except Exception as e:
                metrics.inc(f"{f.name}_fail")
                logger.warning(
                  f"{f.name} failed: {e}"
                )
                raise RuntimeError(
                  f"Feature '{f.name}' failed: {e}"
                ) from e
              finally:
                PROFILER.record(
                  f.name,
                  time.time() - start
                )

          yield Row(**result)

          metrics.inc("rows_ok")
          break

        except Exception as e:

          if attempt < max_retries:
            metrics.inc("retries")
          else:
            metrics.inc("rows_fail")
            logger.error(f"Row failed after retries: {e} - {row.path}")

            #print(f">>> Exception ... {e} - {row.path}")
            #yield Row(**{f.name: None for f in features})


    from core.profiler_instance import PROFILER

    logger.info({
      "feature_profile": PROFILER.snapshot()
    })

    logger.info(
      f"Partition metrics: {metrics.report()}"
    )

  return _inner
