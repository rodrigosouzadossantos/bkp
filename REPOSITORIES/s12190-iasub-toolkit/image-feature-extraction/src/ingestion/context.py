import numpy as np
import cv2

def build_context(row):
  content = row.content

  nparr = np.frombuffer(content, np.uint8)
  img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

  if img is None:
    raise ValueError("Invalid image")

  return {
    "path": row.path,
    "content": content,
    "img": img,
    "gray": cv2.cvtColor(img, cv2.COLOR_BGR2GRAY),
  }
