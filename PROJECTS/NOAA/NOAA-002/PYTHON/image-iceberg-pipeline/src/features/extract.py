import numpy as np

def compute_basic_features(img):
    return {
        "luminance_mean": float(np.mean(img)),
        "luminance_std": float(np.std(img)),
    }
