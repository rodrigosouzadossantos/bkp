---
title: Notebook
marimo-version: 0.19.11
width: medium
auto_download:
- html
- ipynb
---

```python {.marimo}
import marimo as mo
```

```python {.marimo}
diagram = '''
graph LR
    A[Square Rect] -- Link text --> B((Circle))
    A --> C(Round Rect)
    B --> D{Rhombus}
    C --> D
'''
mo.mermaid(diagram)
```

```python {.marimo}
import cv2
import PIL
import torch
import torchvision
import ultralytics
import numpy as np

print(f"OpenCV: {cv2.__version__}")
print(f"Pillow: {PIL.__version__}")
print(f"Torch: {torch.__version__}")
print(f"Torchvision: {torchvision.__version__}")
print(f"Ultralytics (YOLO): {ultralytics.__version__}")
print(f"Numpy: {np.__version__}")
```