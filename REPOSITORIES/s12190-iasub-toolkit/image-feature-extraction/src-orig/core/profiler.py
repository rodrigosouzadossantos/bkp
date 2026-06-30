from collections import defaultdict
import threading


class FeatureProfiler:
  """
  Global thread-safe profiler for feature execution cost.
  Aggregates across all Spark partitions.
  """

  def __init__(self):
    self.lock = threading.Lock()
    self.total_time = defaultdict(float)
    self.count = defaultdict(int)

  def record(self, feature_name: str, duration: float):
    with self.lock:
      self.total_time[feature_name] += duration
      self.count[feature_name] += 1

  def snapshot(self):
    with self.lock:
      return {
        k: {
          "total_time": self.total_time[k],
          "count": self.count[k],
          "avg_time": self.total_time[k] / max(self.count[k], 1),
        }
        for k in self.total_time
      }

  def slowest(self, top_k=10):
    data = self.snapshot()
    return sorted(
      data.items(),
      key=lambda x: x[1]["total_time"],
      reverse=True
    )[:top_k]
