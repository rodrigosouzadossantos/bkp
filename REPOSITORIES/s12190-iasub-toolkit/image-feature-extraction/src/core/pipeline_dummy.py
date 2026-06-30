#from core.context import build_context
from core.metrics import Metrics
from core.logging import get_logger

import time
from pyspark.sql import Row

logger = get_logger()


def process_partition(features, max_retries=2, batch_size=8):

  def _inner(iterator):
    print( f'>>> ROWS')
    count = 0
    for row in iterator:
      count += 1
      # Note: Printing every row will flood your logs in Spark
      print(f'>>>#{count}')

    yield Row({})


  return _inner

