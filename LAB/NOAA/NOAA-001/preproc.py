import cv2
import numpy as np
import matplotlib.pyplot as plt

# 1. Denoising (Gaussian/Bilateral)
def denoise_image(image, method='gaussian', kernel_size=5):
    if method == 'gaussian':
        return cv2.GaussianBlur(image, (kernel_size, kernel_size), 0)
    elif method == 'bilateral':
        return cv2.bilateralFilter(image, 9, 75, 75)
    else:
        return image

# 2. Red Channel Compensation
def boost_red_channel(image, factor=1.5):
    img = image.copy().astype(np.float32)
    img[:,:,0] = np.clip(img[:,:,0] * factor, 0, 255)
    return img.astype(np.uint8)

# 3. Simple Dehazing (Dark Channel Prior)
def dark_channel(image, size=15):
    min_img = cv2.erode(np.min(image, axis=2), np.ones((size, size)))
    return min_img

def dehaze(image, omega=0.95, t0=0.1, size=15):
    norm_img = image.astype(np.float32) / 255
    dark = dark_channel(norm_img, size)
    A = np.max(norm_img[dark >= np.percentile(dark, 99)])
    t = 1 - omega * dark
    t = np.clip(t, t0, 1)
    J = np.empty_like(norm_img)
    for c in range(3):
        J[:,:,c] = (norm_img[:,:,c] - A) / t + A
    J = np.clip(J * 255, 0, 255).astype(np.uint8)
    return J

# 4. Advanced White Balance (Gray World)
def gray_world(image):
    img = image.astype(np.float32)
    avgR = np.mean(img[:,:,0])
    avgG = np.mean(img[:,:,1])
    avgB = np.mean(img[:,:,2])
    avg = (avgR + avgG + avgB) / 3
    img[:,:,0] = np.clip(img[:,:,0] * (avg/avgR), 0, 255)
    img[:,:,1] = np.clip(img[:,:,1] * (avg/avgG), 0, 255)
    img[:,:,2] = np.clip(img[:,:,2] * (avg/avgB), 0, 255)
    return img.astype(np.uint8)

# 5. Contrast Enhancement (CLAHE on HSV V channel)
def clahe_hsv(image):
    hsv = cv2.cvtColor(image, cv2.COLOR_RGB2HSV)
    h, s, v = cv2.split(hsv)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
    v_clahe = clahe.apply(v)
    hsv_clahe = cv2.merge((h, s, v_clahe))
    image_clahe = cv2.cvtColor(hsv_clahe, cv2.COLOR_HSV2RGB)
    return image_clahe

# 6. Retinex Enhancement (Simple MSR)
def simple_msr(image, scales=[15, 101, 301]):
    img = image.astype(np.float32) + 1.0
    retinex = np.zeros_like(img)
    for scale in scales:
        blur = cv2.GaussianBlur(img, (scale, scale), 0)
        retinex += np.log10(img) - np.log10(blur + 1)
    retinex = retinex / len(scales)
    retinex = cv2.normalize(retinex, None, 0, 255, cv2.NORM_MINMAX)
    return retinex.astype(np.uint8)

# 7. GAN-based Enhancement (Placeholder)
def gan_enhance(image):
    # GAN model inference
    return image

# 8. Sharpening (Unsharp Mask)
def sharpen_image(image):
    gaussian = cv2.GaussianBlur(image, (9, 9), 10.0)
    sharpened = cv2.addWeighted(image, 1.5, gaussian, -0.5, 0)
    return sharpened

# 9. Normalization (to [0, 1])
def normalize_image(image):
    return image.astype(np.float32) / 255.0

# 10. Quality Assessment (UIQM Placeholder)
def quality_assessment(image):
    # Placeholder: UIQM requires external library
    # Example: return uiqm(image)
    return "UIQM score: [requires external library]"

# --- Full Pipeline Function ---
def preprocess_pipeline(image_path, 
                       denoise_method='gaussian', 
                       red_boost=1.5, 
                       use_dehaze=True, 
                       use_retinex=False, 
                       use_gan=False):
    img = cv2.imread(image_path)
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    img = denoise_image(img, method=denoise_method)
    img = boost_red_channel(img, factor=red_boost)
    if use_dehaze:
        img = dehaze(img)
    img = gray_world(img)
    img = clahe_hsv(img)
    if use_retinex:
        img = simple_msr(img)
    if use_gan:
        img = gan_enhance(img)
    img = sharpen_image(img)
    img = normalize_image(img)
    score = quality_assessment(img)
    return img, score

# --- Example Usage ---
if __name__ == "__main__":
    image_path = "image-001-orig.jpg"
    processed_img, score = preprocess_pipeline(
        image_path,
        denoise_method='bilateral', # or 'gaussian'
        red_boost=2.0,
        use_dehaze=True,
        use_retinex=False,
        use_gan=False
    )
    print(score)
    plt.imshow(processed_img)
    plt.title("Fully Preprocessed Undersea Image")
    plt.axis('off')
    plt.show()
