import hashlib

def deterministic_sample(image_id, mod=1000, threshold=10):
    h = int(hashlib.md5(image_id.encode()).hexdigest(), 16)
    return (h % mod) < threshold
