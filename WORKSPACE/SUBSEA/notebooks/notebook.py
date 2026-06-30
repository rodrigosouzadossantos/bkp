import marimo

__generated_with = "0.19.11"
app = marimo.App(width="medium", auto_download=["html", "ipynb"])


@app.cell
def _():
    import marimo as mo

    return (mo,)


@app.cell
def _(mo):
    diagram = '''
    graph LR
        A[Square Rect] -- Link text --> B((Circle))
        A --> C(Round Rect)
        B --> D{Rhombus}
        C --> D
    '''
    mo.mermaid(diagram)
    return


@app.cell
def _():
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
    return


if __name__ == "__main__":
    app.run()
