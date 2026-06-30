import os
import re
import traceback
from datetime import timedelta
import cv2
import numpy as np
import pandas as pd
import torch
import torchvision
import easyocr
import time
from ultralytics import YOLO
from tqdm import tqdm
import argparse
import sys

def get_video_timestamp(frame_idx, fps):
    seconds = frame_idx / fps
    m = int(seconds // 60)
    s = int(seconds % 60)
    return f"{m:02}:{s:02}"

def process_results(results):
    for result in results:
        if result.masks is not None:
            return result
    return None

def safe_filename(s):
    return re.sub(r"[^A-Za-z0-9_\-]", "_", s).strip("_")

def long_path(path):
    if os.name == "nt":
        path = os.path.abspath(path)
        if not path.startswith("\\\\?\\"):
            path = "\\\\?\\" + path
    return path

def prediction_coral(img, model):
    original_height, original_width = img.shape[:2]
    coral_results = model(img, verbose=False)
    coral_best_result = process_results(coral_results)
    if coral_best_result and coral_best_result.masks is not None:
        masks = coral_best_result.masks.data
        boxes = coral_best_result.boxes.data
        scores = boxes[:, 4]
        if len(masks) > 0:
            nms_indices = torchvision.ops.nms(
                boxes[:, :4], scores, iou_threshold=0.2
            )
            masks_nms = masks[nms_indices].cpu().numpy()
            scores_nms = scores[nms_indices].cpu().numpy()
        else:
            masks_nms = np.zeros((0, original_height, original_width), dtype=np.uint8)
            scores_nms = []
    else:
        masks_nms = np.zeros((0, original_height, original_width), dtype=np.uint8)
        scores_nms = []
    masks_resized = [
        cv2.resize(
            (m * 255).astype(np.uint8),
            (original_width, original_height),
            interpolation=cv2.INTER_NEAREST,
        )
        for m in masks_nms
    ]
    return masks_resized, scores_nms

def combine_masks(masks):
    if len(masks) == 0:
        return np.zeros((0, 0), dtype=np.uint8)
    h, w = masks[0].shape
    combined = np.zeros((h, w), dtype=np.uint8)
    for idx, m in enumerate(masks):
        combined[m > 127] = idx + 1
    return combined

def crop_frame(frame):
    height, _, _ = frame.shape
    mid = height // 2
    top = max(0, mid - int(0.34 * height))
    bottom = min(height, mid + int(0.34 * height))
    cropped_frame = frame[top:bottom, :]
    return cropped_frame, top, bottom

def extract_data(frame, x, y, w, h):
    roi = frame[y : y + h, x : x + w]

    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
    lower = np.array([15, 70, 70])
    upper = np.array([45, 255, 255])
    mask = cv2.inRange(hsv, lower, upper)
    mask = cv2.bilateralFilter(mask, 9, 75, 75)
    kernel = np.ones((2,2), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=1)
    mask = cv2.medianBlur(mask, 3)
    
    reader = easyocr.Reader(["en"], verbose=False)
    result = reader.readtext(mask)
    north, east = None, None
    if len(result) >= 2:
        match_north = re.search(r"-?\d+", result[0][1])
        match_east = re.search(r"-?\d+", result[1][1])
        north = int(match_north.group()) if match_north else None
        east = int(match_east.group()) if match_east else None
    return north, east

def generate_predictions(video, model, out_frames, out_masks, out_scores, frame_skip, x, y, w, h):
    results = []
    cap = cv2.VideoCapture(video)
    if not cap.isOpened():
        print(f"Erro ao abrir vídeo: {video}")
        return []
    frame_rate = cap.get(cv2.CAP_PROP_FPS)
    num_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    video_name = os.path.basename(video).split(".")[0]
    for prediction_index in range(0, num_frames, frame_skip):
        try:
            cap.set(cv2.CAP_PROP_POS_FRAMES, prediction_index)
            ret, frame = cap.read()
            if not ret:
                break
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            cropped_frame, top, bottom = crop_frame(frame_rgb)
            masks, scores = prediction_coral(cropped_frame, model)
            combined_mask = combine_masks(masks)
            current_timestamp = get_video_timestamp(prediction_index, frame_rate)
            north, east = extract_data(frame_rgb, x, y, w, h)
            base_id = safe_filename(f"{video_name}_{current_timestamp}")
            frame_path = os.path.join(out_frames, f"{base_id}.npy")
            masks_path = os.path.join(out_masks, f"{base_id}.npy")
            scores_path = os.path.join(out_scores, f"{base_id}.npy")
            np.save(long_path(frame_path), cropped_frame)
            np.save(long_path(masks_path), combined_mask)
            np.save(long_path(scores_path), np.array(scores))
            results.append(
                {
                    "video": video_name,
                    "time": current_timestamp,
                    "north": north,
                    "east": east,
                    "scores_list": list(scores),
                    "cropped_frame_path": frame_path,
                    "mask_path": masks_path,
                }
            )
        except Exception as e:
            print(f"Erro no frame {prediction_index} do vídeo {video_name}: {e}")
            traceback.print_exc()
    cap.release()
    return results

def run_inference(videos, out_frames, out_masks, out_scores, model_path, frame_skip, x, y, w, h):
    model = YOLO(model_path)
    df_inference = []
    for video in tqdm(videos, desc="Processando vídeos"):
        result = generate_predictions(video, model, out_frames, out_masks, out_scores, frame_skip, x, y, w, h)
        df_inference.extend(result)
    df = pd.DataFrame(df_inference)
    return df

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--operacao", type=str, required=True, help="Diretório dos vídeos")
    parser.add_argument("--out_frames", type=str, default="frames", help="Diretório para frames")
    parser.add_argument("--out_masks", type=str, default="masks", help="Diretório para masks")
    parser.add_argument("--out_scores", type=str, default="scores", help="Diretório para scores")
    parser.add_argument("--out_csv", type=str, default="resultados_inferencia_1", help="Path de saída do CSV")
    parser.add_argument("--model_path", type=str, default="coral_yolov11_segm_4c_V5.pt", help="Caminho do modelo YOLO")
    parser.add_argument("--frame_skip", type=int, required=True, help="Quantidade de frames a pular")
    parser.add_argument("--x", type=int, required=True, help="Coordenada x do ROI")
    parser.add_argument("--y", type=int, required=True, help="Coordenada y do ROI")
    parser.add_argument("--w", type=int, required=True, help="Largura do ROI")
    parser.add_argument("--h", type=int, required=True, help="Altura do ROI")
    args = parser.parse_args()

    os.makedirs(args.out_frames, exist_ok=True)
    os.makedirs(args.out_masks, exist_ok=True)
    os.makedirs(args.out_scores, exist_ok=True)
    videos = [
        os.path.join(args.operacao, v)
        for v in os.listdir(args.operacao)
        if v.lower().endswith((".mp4", ".avi", ".mkv"))
    ]
    videos = sorted(videos)

    start_time = time.time()
    df_inference = run_inference(
        videos,
        args.out_frames,
        args.out_masks,
        args.out_scores,
        args.model_path,
        args.frame_skip,
        args.x,
        args.y,
        args.w,
        args.h
    )
    end_time = time.time()
    total_seconds = int(end_time - start_time)
    minutos = total_seconds // 60
    segundos = total_seconds % 60
    print(f"Tempo total de execução: {minutos} minutos e {segundos} segundos")
    sys.stdout.flush()
    if not df_inference.empty:
        try:
            df_inference.to_csv(
                args.out_csv, index=False, encoding="utf-8"
            )
            print("\nResultados da inferência salvos em: " + args.out_csv)
        except Exception as e:
            print(f"\nErro ao salvar resultados_inferencia_1.csv: {e}")
            traceback.print_exc()
    else:
        print("\nNenhuma inferência foi realizada.")