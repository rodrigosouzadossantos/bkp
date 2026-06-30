import cv2
import numpy as np

def apply_clahe(image):
    lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=2.0)
    l2 = clahe.apply(l)
    return cv2.merge((l2, a, b))

def apply_retinex(image):
    img = image.astype(np.float32) + 1.0
    log_img = np.log(img)
    blur = cv2.GaussianBlur(img, (0,0), sigmaX=30)
    log_blur = np.log(blur + 1.0)
    retinex = log_img - log_blur
    retinex = cv2.normalize(retinex, None, 0, 255, cv2.NORM_MINMAX)
    return retinex.astype(np.uint8)

def preprocess(image, method):
    if method == "raw":
        return image
    elif method == "clahe":
        return apply_clahe(image)
    elif method == "retinex":
        return apply_retinex(image)
    else:
        raise ValueError(f"Unknown preprocessing method: {method}")
