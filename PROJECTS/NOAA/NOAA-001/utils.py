import hashlib

def deterministic_sample(image_id: str, mod: int, threshold: int) -> bool:
    h = int(hashlib.md5(image_id.encode()).hexdigest(), 16)
    return (h % mod) < threshold
