import os
import signal
import sys
from pathlib import Path
from multiprocessing import Pool
from typing import List, Dict, Any

from tqdm import tqdm
import exiftool
import pandas as pd
from PIL import Image
import numpy as np
import cv2
from skimage.filters import sobel
from skimage.measure import shannon_entropy

# -------------------------------
# GLOBALS
# -------------------------------
STOP_REQUESTED = False
BATCH_SIZE = 500
TMP_DIR = "tmp_batches"

# -------------------------------
# SIGNAL HANDLER
# -------------------------------
def handle_signal(sig, frame):
    global STOP_REQUESTED
    print("\nReceived signal, stopping gracefully...")
    STOP_REQUESTED = True

signal.signal(signal.SIGINT, handle_signal)
signal.signal(signal.SIGTERM, handle_signal)

# -------------------------------
# EXIFTOOLS BATCH
# -------------------------------
def extract_exif_batch(paths: List[str], tags: List[str] = None) -> List[Dict[str, Any]]:
    """Extract EXIF metadata using ExifTool in batch mode."""
    if tags is None:
        tags = []
    results = []
    with exiftool.ExifTool() as et:
        meta_list = et.get_metadata_batch(paths)
    for meta in meta_list:
        out = {t: meta.get(f"EXIF:{t}") for t in tags}
        out["SourceFile"] = meta.get("SourceFile")
        results.append(out)
    return results

# -------------------------------
# VECTORIAL IMAGE FEATURES
# -------------------------------
def compute_features_batch(image_paths: List[str]) -> List[Dict[str, Any]]:
    results = []
    for path in image_paths:
        try:
            img = Image.open(path).convert("RGB")
            arr = np.array(img)

            gray = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)
            hsv = cv2.cvtColor(arr, cv2.COLOR_RGB2HSV)
            s = hsv[:, :, 1]

            results.append({
                "SourceFile": path,
                "brightness_mean": float(np.mean(gray)),
                "brightness_std": float(np.std(gray)),
                "saturation_mean": float(np.mean(s)),
                "saturation_std": float(np.std(s)),
                "laplacian_var": float(cv2.Laplacian(gray, cv2.CV_64F).var()),
                "edge_density": float(np.mean(sobel(gray))),
                "entropy": float(shannon_entropy(gray))
            })
        except Exception as e:
            print(f"⚠️ Failed {path}: {e}")
            results.append({"SourceFile": path, "skipped": True})
    return results

# -------------------------------
# MERGE EXIF + FEATURES
# -------------------------------
def process_batch(batch_paths: List[str]) -> List[Dict[str, Any]]:
    exif_tags = ["ExifImageWidth", "ExifImageHeight", "GPSLatitude", "GPSLongitude", "DateTimeOriginal"]
    exif_data = extract_exif_batch(batch_paths, tags=exif_tags)
    features_data = compute_features_batch(batch_paths)

    exif_dict = {row["SourceFile"]: row for row in exif_data}
    merged = []
    for feat in features_data:
        src = feat["SourceFile"]
        row = exif_dict.get(src, {})
        row.update(feat)
        merged.append(row)
    return merged

# -------------------------------
# BATCH WRITER
# -------------------------------
def write_batch(batch: List[Dict[str, Any]], tmp_dir: str):
    os.makedirs(tmp_dir, exist_ok=True)
    batch_df = pd.DataFrame(batch)
    batch_file = os.path.join(tmp_dir, f"batch_{len(os.listdir(tmp_dir))}.parquet")
    batch_df.to_parquet(batch_file, index=False)

# -------------------------------
# PIPELINE MAIN
# -------------------------------
def run_pipeline(image_paths: List[str], workers: int = 4):
    global STOP_REQUESTED
    batch = []
    processed, failed, skipped = 0, 0, 0
    total = len(image_paths)

    with Pool(processes=workers) as pool:
        results_iter = pool.imap_unordered(process_batch, [image_paths[i:i+BATCH_SIZE] 
                                                           for i in range(0, total, BATCH_SIZE)])
        with tqdm(total=total, desc="Processing images") as pbar:
            try:
                for res_batch in results_iter:
                    if STOP_REQUESTED:
                        print("Stop requested, terminating pool...")
                        pool.terminate()
                        break

                    if res_batch is None:
                        failed += len(batch)
                    else:
                        for r in res_batch:
                            if r.get("skipped"):
                                skipped += 1
                            else:
                                processed += 1
                        batch.extend(res_batch)

                    if len(batch) >= BATCH_SIZE:
                        write_batch(batch, TMP_DIR)
                        batch = []

                    pbar.update(len(res_batch))
            except KeyboardInterrupt:
                print("\nKeyboardInterrupt received. Terminating pool...")
                pool.terminate()
            finally:
                print("\nCleaning up workers...")
                pool.join()

                if batch:
                    print("Flushing remaining data...")
                    write_batch(batch, TMP_DIR)

    print("\nPARTIAL SUMMARY")
    print(f"Processed: {processed}")
    print(f"Failed: {failed}")
    print(f"Skipped: {skipped}")

    # Merge all parquet batches
    print("\nMerging partial outputs...")
    batch_files = [os.path.join(TMP_DIR, f) for f in os.listdir(TMP_DIR) if f.endswith(".parquet")]
    final_df = pd.concat([pd.read_parquet(f) for f in batch_files], ignore_index=True)
    final_path = "features.parquet"
    final_df.to_parquet(final_path, index=False)
    print(f"Features saved to {final_path}")
    print("Graceful shutdown complete")

# -------------------------------
# ENTRY POINT
# -------------------------------
if __name__ == "__main__":
    import glob
    # Example: replace with your dataset path
    dataset_dir = "/mnt/SGO/sub/hidrografia/01_auv/03_projeto_bc_2023/embarcacao_hibrida/02_skandi_commander/01_dados_aprovados/ordens_servico_002"
    image_paths = glob.glob(os.path.join(dataset_dir, "*.jpg"), recursive=True)
    run_pipeline(image_paths, workers=8)
