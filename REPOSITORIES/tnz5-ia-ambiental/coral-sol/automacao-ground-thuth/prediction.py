import glob
import json
import os
import string
from datetime import datetime

import cv2
import matplotlib.pyplot as plt
import numpy as np
import torch
import torchvision
from ultralytics import YOLO

# Constants
DUCT_CLASS_ID = 0
CORAL_CLASS_ID = 0
CORAL_COLOR_HEX = "#2ca02c"  # Color for coral
BACKGROUND_COLOR_HEX = "#ffffff"  # Color for background

# Convert hex colors to BGR
CORAL_COLOR_BGR = tuple(int(CORAL_COLOR_HEX.lstrip('#')[i:i+2], 16) for i in (4, 2, 0))
BACKGROUND_COLOR_BGR = tuple(int(BACKGROUND_COLOR_HEX.lstrip('#')[i:i+2], 16) for i in (4, 2, 0))

# Models
easy_duct_model = YOLO('../Pesos-Modelos_de_Segmentação_de_Duto/best_facil.pt')
medium_duct_model = YOLO('../Pesos-Modelos_de_Segmentação_de_Duto/best_medio.pt')
hard_duct_model = YOLO('../Pesos-Modelos_de_Segmentação_de_Duto/best_dificil.pt')
coral_model = YOLO('../Pesos-Modelo_de_Segmentação_de_Coral_Baseline/best.pt')


def prediction_duct(img: np.ndarray) -> tuple:
    original_height, original_width = img.shape[:2]
    for model in [easy_duct_model, medium_duct_model, hard_duct_model]:
        duct_results = model(img, verbose=False)
        best_result = process_results(duct_results)
        if best_result:
            break

    if best_result and best_result.masks is not None:
        masks = best_result.masks.data
        boxes = best_result.boxes.data
        classes = boxes[:, 5]
        scores = boxes[:, 4]

        duct_indices = torch.where(classes == DUCT_CLASS_ID)[0]
        duct_boxes = boxes[duct_indices]
        duct_masks = masks[duct_indices]

        if len(duct_boxes) > 0:
            nms_indices = torchvision.ops.nms(duct_boxes[:, :4], scores[duct_indices], iou_threshold=0.2)
            duct_boxes = duct_boxes[nms_indices]
            duct_masks = duct_masks[nms_indices]
            final_duct_mask = torch.any(duct_masks, dim=0).int() * 255
        else:
            final_duct_mask = torch.zeros((original_height, original_width), dtype=torch.uint8)
    else:
        final_duct_mask = torch.zeros((original_height, original_width), dtype=torch.uint8)

    final_duct_mask_np = final_duct_mask.cpu().numpy()
    resized_final_duct_mask = cv2.resize(final_duct_mask_np, (original_width, original_height),
                                         interpolation=cv2.INTER_NEAREST)
    return resized_final_duct_mask, torch.from_numpy(resized_final_duct_mask).int()


def process_results(results: list) -> any:
    for result in results:
        if result.masks is not None:
            return result
    return None


def prediction_coral(img: np.ndarray) -> tuple:
    original_height, original_width = img.shape[:2]
    coral_results = coral_model(img, verbose=False)
    coral_best_result = process_results(coral_results)

    if coral_best_result and coral_best_result.masks is not None:
        masks = coral_best_result.masks.data
        boxes = coral_best_result.boxes.data
        classes = boxes[:, 5]
        scores = boxes[:, 4]

        coral_indices = torch.where((classes == CORAL_CLASS_ID) & (scores > 0.5))[0]
        coral_boxes = boxes[coral_indices]
        coral_masks = masks[coral_indices]
        coral_scores = scores[coral_indices]

        if len(coral_boxes) > 0:
            nms_indices = torchvision.ops.nms(coral_boxes[:, :4], coral_scores, iou_threshold=0.2)
            coral_masks = coral_masks[nms_indices]
            final_coral_mask = torch.any(coral_masks, dim=0).int() * 255
        else:
            final_coral_mask = torch.zeros((original_height, original_width), dtype=torch.uint8)
    else:
        final_coral_mask = torch.zeros((original_height, original_width), dtype=torch.uint8)

    final_coral_mask_np = final_coral_mask.cpu().numpy()
    resized_final_coral_mask = cv2.resize(final_coral_mask_np, (original_width, original_height),
                                          interpolation=cv2.INTER_NEAREST)
    centered_mask = np.zeros((original_height, original_width), dtype=np.uint8)
    y_offset = (original_height - resized_final_coral_mask.shape[0]) // 2
    x_offset = (original_width - resized_final_coral_mask.shape[1]) // 2
    if (y_offset >= 0 and x_offset >= 0 and
            y_offset + resized_final_coral_mask.shape[0] <= original_height and
            x_offset + resized_final_coral_mask.shape[1] <= original_width):
        centered_mask[y_offset:y_offset + resized_final_coral_mask.shape[0],
        x_offset:x_offset + resized_final_coral_mask.shape[1]] = resized_final_coral_mask
    else:
        centered_mask = resized_final_coral_mask.copy()

    return centered_mask, torch.from_numpy(centered_mask).int()


def create_color_mask(image: np.ndarray, target_color: tuple, threshold: int = 10) -> np.ndarray:
    lower_bound = np.array(target_color) - threshold
    upper_bound = np.array(target_color) + threshold
    mask = cv2.inRange(image, lower_bound, upper_bound)
    return mask


def save_images(image_original: np.ndarray, img: np.ndarray, intersection_mask: np.ndarray, folder_save: str,
                path_annotated_img: str) -> None:
    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

    plt.figure(figsize=(20, 14))
    plt.subplot(1, 2, 1)
    plt.title('Expert Annotation')
    plt.imshow(img_rgb)
    plt.axis('off')
    plt.gca().set_aspect('equal', adjustable='box')

    model_img_copy = image_original.copy()
    if intersection_mask.any():
        contours, _ = cv2.findContours(intersection_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        cv2.drawContours(model_img_copy, contours, -1, (255, 0, 0), thickness=3)

    plt.subplot(1, 2, 2)
    plt.title('Model Annotation')
    plt.imshow(model_img_copy)
    plt.axis('off')
    plt.gca().set_aspect('equal', adjustable='box')

    plt.tight_layout()
    plt.savefig(os.path.join(folder_save, os.path.basename(path_annotated_img)))
    plt.close()


def sanitize_filename(filename: str) -> str:
    valid_chars = f"-_.() {string.ascii_letters}{string.digits}"
    sanitized_filename = ''.join(c if c in valid_chars else '_' for c in filename)
    return sanitized_filename


def load_json_files(folder_output_data: str) -> tuple:
    json_output_files = glob.glob(
        os.path.join(folder_output_data, "annotations", "consolidated-annotation", "consolidation-response", "**",
                     "*.json"))

    json_input_files = glob.glob(
        os.path.join(folder_output_data, "annotations", "consolidated-annotation", "consolidation-request", "**",
                     "*.json"))

    return json_output_files, json_input_files


def match_and_process_json_files(json_output_files: list, json_input_files: list, folder_input_data: str,
                                 images_files: str, folder_save: str, inter_path: str) -> None:
    for json_out in json_output_files:
        with open(json_out, 'r') as file:
            data_out = json.load(file)
            datasetObjectId = data_out[0]["datasetObjectId"]
            for json_in in json_input_files:
                with open(json_in, 'r') as file:
                    data_in = json.load(file)
                    if datasetObjectId == data_in[0]["datasetObjectId"]:
                        break

            s3Uri = data_in[0]["dataObject"]["s3Uri"].split("/")[-1]
            path_img_original = os.path.join(folder_input_data, s3Uri)
            image_original = cv2.imread(path_img_original)

            # Annotation
            path_annotated_img = os.path.join(images_files, sanitize_filename(data_out[0]["consolidatedAnnotation"]
                                                                              ["content"][inter_path + "-ref"].split(
                "/")[-1]))
            image_segmentation = cv2.imread(path_annotated_img)

            # Create binary mask based on target color
            mask = create_color_mask(image_segmentation, CORAL_COLOR_BGR)

            # Find contours on the mask, considerando todos os contornos (incluindo buracos)
            contours, _ = cv2.findContours(mask, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE)
            overlay_original = image_original.copy()
            cv2.drawContours(overlay_original, contours, -1, (255, 0, 255), 3)  # Magenta contour

            # Model
            resized_final_duct_mask, resized_final_duct_mask_tensor = prediction_duct(image_original)
            resized_final_coral_mask, resized_final_coral_mask_tensor = prediction_coral(image_original)
            intersection_mask = (
                (resized_final_coral_mask_tensor & resized_final_duct_mask_tensor).int()).cpu().numpy().astype(np.uint8)

            # Save Images
            save_images(cv2.cvtColor(image_original, cv2.COLOR_BGR2RGB), overlay_original, intersection_mask,
                        folder_save, path_img_original)


if __name__ == '__main__':
    prefix_output = 'imagens-lote-4-5/rotulacao-lotes-4-5'
    prefix_input = 'imagens-lote-4-5'

    today_date = datetime.today().strftime('%Y-%m-%d')
    folder_input_data = os.path.join("Bucket-Input-Versions", prefix_input.split("/")[0])
    folder_output_data = os.path.join("Bucket-Output-Versions", prefix_output.split("/")[0], today_date)
    folder_save = os.path.join("Prediction-Versions", prefix_output.split("/")[0], today_date)
    os.makedirs(folder_save, exist_ok=True)

    json_output_files, json_input_files = load_json_files(folder_output_data)
    images_files = os.path.join(folder_output_data, "annotations", "consolidated-annotation", "output")
    inter_path = prefix_output.split("/")[-1]

    match_and_process_json_files(json_output_files, json_input_files, folder_input_data, images_files,
                                 folder_save, inter_path)