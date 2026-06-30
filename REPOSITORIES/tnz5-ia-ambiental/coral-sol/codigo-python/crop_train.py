import json
import os
import cv2
import numpy as np

# Caminhos para as pastas de imagens e anotações
image_folder = 'Estruturas/Rizer'
annotation_folder = 'Estruturas/Rizer'
output_folder = 'Objetos_128_Rizer'

os.makedirs(output_folder, exist_ok=True)

def load_image(image_path):
    return cv2.imread(image_path)

def load_annotation(annotation_path):
    with open(annotation_path) as f:
        data = json.load(f)
    return data

def create_mask(image, points):
    mask = np.zeros(image.shape[:2], dtype=np.uint8)
    cv2.fillPoly(mask, [points], 255)
    return mask

def extract_points_from_mask(mask):
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    return [contour.squeeze().tolist() for contour in contours if contour.size > 2]

def crop_and_save(image, mask, x, y, w, h, output_image_base_path, image_name, obj_index, crop_index, original_annotations):
    crop_info = []

    def has_significant_area(mask):
        num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(mask.astype(np.uint8), connectivity=8)
        for stat in stats[1:]:
            if stat[cv2.CC_STAT_AREA] > 0:
                return True
        return False

    def save_annotation(output_image_path, shapes, height, width, original_annotations):
        adjusted_annotations = {
            "version": original_annotations["version"],
            "flags": original_annotations["flags"],
            "shapes": shapes,
            "imagePath": os.path.basename(output_image_path),
            "imageHeight": height,
            "imageWidth": width
        }
        output_annotation_path = os.path.splitext(output_image_path)[0] + '.json'
        with open(output_annotation_path, 'w') as f:
            json.dump(adjusted_annotations, f, indent=4)

    if w <= 128 and h <= 128:
        left = max(x + w // 2 - 64, 0)
        top = max(y + h // 2 - 64, 0)

        if left + 128 > image.shape[1]:
            left = image.shape[1] - 128
        if top + 128 > image.shape[0]:
            top = image.shape[0] - 128

        left = max(left, 0)
        top = max(top, 0)

        cropped_image = image[top:top + 128, left:left + 128]
        cropped_mask = mask[top:top + 128, left:left + 128]

        if np.any(cropped_mask) and has_significant_area(cropped_mask):
            output_image_path = os.path.join(output_image_base_path,
                                             f"{image_name.replace('.jpg', '')}_obj_{obj_index}_crop_{crop_index}.png")
            cv2.imwrite(output_image_path, cropped_image)
            new_points_list = extract_points_from_mask(cropped_mask)
            shapes = []
            for new_points in new_points_list:
                shapes.append({
                    "label": original_annotations['shapes'][obj_index]["label"],
                    "points": new_points,
                    "group_id": original_annotations['shapes'][obj_index].get("group_id"),
                    "shape_type": original_annotations['shapes'][obj_index]["shape_type"],
                    "flags": original_annotations['shapes'][obj_index]["flags"]
                })
            save_annotation(output_image_path, shapes, 128, 128, original_annotations)
            crop_info.append((left, top, 128, 128, output_image_path, cropped_mask))

    else:
        subimages = []
        for sub_y in range(y, y + h, 128):
            for sub_x in range(x, x + w, 128):
                sub_left = max(sub_x, 0)
                sub_top = max(sub_y, 0)
                sub_right = min(sub_x + 128, image.shape[1])
                sub_bottom = min(sub_y + 128, image.shape[0])

                if sub_right - sub_left == 128 and sub_bottom - sub_top == 128:
                    subimage = image[sub_top:sub_bottom, sub_left:sub_right]
                    submask = mask[sub_top:sub_bottom, sub_left:sub_right]
                    subimages.append((subimage, sub_left, sub_top, submask))

        for idx, (subimage, sub_left, sub_top, submask) in enumerate(subimages):
            if np.any(submask) and has_significant_area(submask):
                output_image_path = os.path.join(output_image_base_path,
                                                 f"{image_name.replace('.jpg', '')}_obj_{obj_index}_crop_{crop_index + idx}.png")
                cv2.imwrite(output_image_path, subimage)
                new_points_list = extract_points_from_mask(submask)
                shapes = []
                for new_points in new_points_list:
                    shapes.append({
                        "label": original_annotations['shapes'][obj_index]["label"],
                        "points": new_points,
                        "group_id": original_annotations['shapes'][obj_index].get("group_id"),
                        "shape_type": original_annotations['shapes'][obj_index]["shape_type"],
                        "flags": original_annotations['shapes'][obj_index]["flags"]
                    })
                save_annotation(output_image_path, shapes, 128, 128, original_annotations)
                crop_info.append((sub_left, sub_top, 128, 128, output_image_path, submask))

    return crop_info

def process_images_and_annotations(image_folder, annotation_folder, output_folder):
    for image_name in os.listdir(image_folder):

        if "json" in image_name:
            continue

        image_path = os.path.join(image_folder, image_name)
        annotation_path = os.path.join(annotation_folder, image_name.replace('.jpg', '.json'))

        if not os.path.exists(annotation_path):
            continue

        image = load_image(image_path)
        annotations = load_annotation(annotation_path)
        original_width, original_height = image.shape[1], image.shape[0]
        crop_index = 0

        for i, ann in enumerate(annotations['shapes']):
            points = np.array(ann['points'], dtype=np.int32)
            mask = create_mask(image, points)
            x, y, w, h = cv2.boundingRect(mask)

            crop_info = crop_and_save(image, mask, x, y, w, h, output_folder, image_name, i, crop_index, annotations)
            crop_index += len(crop_info)  # Incrementar o índice de recorte com base na quantidade de recortes feitos

if __name__ == '__main__':
    process_images_and_annotations(image_folder, annotation_folder, output_folder)
