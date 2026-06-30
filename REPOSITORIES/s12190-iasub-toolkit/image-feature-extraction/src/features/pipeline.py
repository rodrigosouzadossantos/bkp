import importlib
import pkgutil
import inspect

from features.base import FeatureExtractor
import features


def load_feature_pipeline():
  pipeline = []

  for _, module_name, _ in pkgutil.iter_modules(features.__path__):
    module = importlib.import_module(f"features.{module_name}")

    for name, obj in inspect.getmembers(module, inspect.isclass):
      if issubclass(obj, FeatureExtractor) and obj is not FeatureExtractor:
        pipeline.append(obj())

  return pipeline
