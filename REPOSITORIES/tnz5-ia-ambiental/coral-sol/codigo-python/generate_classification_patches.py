import os

from PIL import Image
from shapely.geometry import Polygon, box

input_dir = 'Coral-YOLO-V4-Lote1,2,3\\images'
annotation_dir = 'Coral-YOLO-V4-Lote1,2,3\\labels'
output_dir_positivo = 'Dataset-Class\\positivo'
output_dir_negativo = 'Dataset-Class\\negativo'
crop_size = 256

os.makedirs(output_dir_positivo, exist_ok=True)
os.makedirs(output_dir_negativo, exist_ok=True)


def load_annotations(annotation_path, image_width, image_height):
    annotations = []
    with open(annotation_path, 'r') as file:
        for line in file.readlines():
            parts = line.strip().split()
            class_id = int(parts[0])
            points = [(float(parts[i]) * image_width, float(parts[i + 1]) * image_height) for i in
                      range(1, len(parts), 2)]
            annotations.append((class_id, Polygon(points)))
    return annotations


def is_coral_sol_in_crop(crop_box, annotations):
    crop_polygon = box(*crop_box)
    for (class_id, polygon) in annotations:
        if crop_polygon.intersects(polygon):
            return True
    return False


if __name__ == '__main__':

    for filename in os.listdir(input_dir):
        image_path = os.path.join(input_dir, filename)
        annotation_path = os.path.join(annotation_dir, os.path.splitext(filename)[0] + '.txt')

        if not os.path.exists(annotation_path):
            continue

        image = Image.open(image_path)
        width, height = image.size
        annotations = load_annotations(annotation_path, width, height)

        for i in range(0, width, crop_size):
            for j in range(0, height, crop_size):
                crop_box = (i, j, i + crop_size, j + crop_size)
                crop = image.crop(crop_box)

                if is_coral_sol_in_crop(crop_box, annotations):
                    crop.save(os.path.join(output_dir_positivo, f'{filename}_{i}_{j}.png'))
                else:
                    crop.save(os.path.join(output_dir_negativo, f'{filename}_{i}_{j}.png'))
