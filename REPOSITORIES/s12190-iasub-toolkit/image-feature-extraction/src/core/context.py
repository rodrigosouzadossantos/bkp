import numpy as np
import cv2


def build_context(row):

  nparr = np.frombuffer(row.content, np.uint8)
  img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

  if img is None:
    raise ValueError(f"Invalid image {row.path}")

  return {
    "path": row.path,
    "content": row.content,
    #"img": img,
    #"gray": cv2.cvtColor(img, cv2.COLOR_BGR2GRAY),
    "_cache": {}
  }


def get_gray(ctx):
  if "gray" not in ctx["_cache"]:
    ctx["_cache"]["gray"] = cv2.cvtColor(ctx["img"], cv2.COLOR_BGR2GRAY)

  return ctx["_cache"]["gray"]
