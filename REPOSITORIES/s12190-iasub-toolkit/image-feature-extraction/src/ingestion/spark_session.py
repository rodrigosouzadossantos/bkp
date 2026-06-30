from pyspark.sql import SparkSession

import os
import re

_env_pattern = re.compile(r"\$\{env:([^}]+)\}|\$\{([^}]+)\}")

def resolve_env(value: str) -> str:
  def replacer(match):
    env1, env2 = match.groups()
    var = env1 or env2
    return os.environ.get(var, "")
  return _env_pattern.sub(replacer, value)


def strip_inline_comment(line: str) -> str:
  in_quote = False
  result = []

  for char in line:
    if char in ("'", '"'):
      in_quote = not in_quote
    if char == "#" and not in_quote:
      break
    result.append(char)

  return "".join(result).strip()


def load_conf(path="config/spark.conf") -> dict:
  confs = {}
  with open(path) as f:
    for line in f:
      line = line.strip()
      if not line or line.startswith("#"):
        continue
      line = strip_inline_comment(line)
      if "=" not in line:
        continue
      k, v = line.split("=", 1)
      confs[k.strip()] = resolve_env(
        v.strip().strip("'\"")
      )
  return confs


def create_spark():
  confs = load_conf()

  builder = SparkSession.builder #.appName("image-iceberg")

  for k, v in confs.items():
    builder = builder.config(k, v)

  return builder.getOrCreate()
  #return builder.master("local[32]").getOrCreate()
