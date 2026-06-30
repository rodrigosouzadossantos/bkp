import cv2
import numpy as np
from skimage.measure import shannon_entropy

def laplacian_variance(image):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    return cv2.Laplacian(gray, cv2.CV_64F).var()

def edge_density(image):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 100, 200)
    return edges.mean()

def brightness_stats(image):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    return gray.mean(), gray.std()

def saturation_stats(image):
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    s = hsv[:, :, 1]
    return s.mean(), s.std()

def entropy(image):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    return shannon_entropy(gray)

def extract_features(image) -> dict:

    feats = {}

    try:
        b_mean, b_std = brightness_stats(image)
        feats["brightness_mean"] = float(b_mean)
        feats["brightness_std"] = float(b_std)
        feats["missing_brightness"] = False
    except:
        feats["brightness_mean"] = None
        feats["brightness_std"] = None
        feats["missing_brightness"] = True

    try:
        s_mean, s_std = saturation_stats(image)
        feats["saturation_mean"] = float(s_mean)
        feats["saturation_std"] = float(s_std)
        feats["missing_saturation"] = False
    except:
        feats["saturation_mean"] = None
        feats["saturation_std"] = None
        feats["missing_saturation"] = True

    # Single-value features
    for name, func in {
        "laplacian_var": laplacian_variance,
        "edge_density": edge_density,
        "entropy": entropy,
    }.items():
        try:
            val = func(image)
            feats[name] = float(val)
            feats[f"missing_{name}"] = False
        except:
            feats[name] = None
            feats[f"missing_{name}"] = True

    # Subsea extras
    try:
        feats["contrast"] = float(np.std(image))
        feats["dark_ratio"] = float(np.mean(image < 30))
        feats["bright_ratio"] = float(np.mean(image > 220))
    except:
        feats["contrast"] = None
        feats["dark_ratio"] = None
        feats["bright_ratio"] = None

    return feats

