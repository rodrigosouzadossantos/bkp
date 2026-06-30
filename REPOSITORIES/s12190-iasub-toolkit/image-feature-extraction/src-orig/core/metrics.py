import time
from collections import defaultdict


class Metrics:
  def __init__(self):
    self.counts = defaultdict(int)
    self.timings = defaultdict(float)

  def inc(self, key, n=1):
    self.counts[key] += n

  def timeit(self, key):
    class Timer:
      def __init__(inner, outer):
        inner.outer = outer

      def __enter__(inner):
        inner.start = time.time()

      def __exit__(inner, *args):
        inner.outer.timings[key] += time.time() - inner.start

    return Timer(self)

  def report(self):
    return {
      "counts": dict(self.counts),
      "timings": dict(self.timings),
    }
