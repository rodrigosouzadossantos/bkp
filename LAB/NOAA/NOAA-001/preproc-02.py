import cv2
import numpy as np
import matplotlib.pyplot as plt

def load_image(path):
    image = cv2.imread(path)
    return cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

def clahe_hsv(image):
    hsv = cv2.cvtColor(image, cv2.COLOR_RGB2HSV)
    h, s, v = cv2.split(hsv)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
    v = clahe.apply(v)
    hsv = cv2.merge((h, s, v))
    return cv2.cvtColor(hsv, cv2.COLOR_HSV2RGB)

def normalize_image(image):
    return image.astype(np.float32) / 255.0

if __name__ == "__main__":
    image_path = "image-001-orig.jpg"
    img = load_image(image_path)
    img = clahe_hsv(img)
    img = normalize_image(img)
    plt.imshow(img)
    plt.title("Simplified Undersea Enhancement")
    plt.axis('off')
    plt.show()
