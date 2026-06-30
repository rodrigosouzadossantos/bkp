import importlib
import pkgutil
import inspect

import features
from features.base import FeatureExtractor


def load_features(config: dict):
  enabled = set(config.get("features", []))
  instances = []

  for _, module_name, _ in pkgutil.iter_modules(features.__path__):
    module = importlib.import_module(f"features.{module_name}")

    for _, cls in inspect.getmembers(module, inspect.isclass):
      if (
        issubclass(cls, FeatureExtractor)
        and cls is not FeatureExtractor
      ):
        obj = cls()

        if enabled and obj.name not in enabled:
          continue

        if obj.enabled:
          instances.append(obj)

  instances.sort(key=lambda x: x.order)
  return instances
