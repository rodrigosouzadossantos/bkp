import json
import os


def normalize_points(points, image_width, image_height):
    return [(x / image_width, y / image_height) for x, y in points]


def convert_json_to_yolo_segmentation(json_file, output_dir):
    with open(json_file, 'r') as f:
        data = json.load(f)

    image_width = data['imageWidth']
    image_height = data['imageHeight']

    annotations = data['shapes']

    yolo_annotations = []
    seen_objects = set()  # Para verificar objetos duplicados
    seen_points = set()  # Para verificar pontos duplicados

    for annotation in annotations:
        points = annotation['points']

        if len(points) < 3:
            print(f"Object in {json_file} has less than 3 points, skipping.")
            continue

        # Transformar pontos em tuplas para checar duplicados
        points_tuple = tuple(map(tuple, points))

        if points_tuple in seen_objects:
            print(f"Duplicate object found in {json_file}, skipping.")
            continue

        seen_objects.add(points_tuple)

        class_id = 0
        normalized_points = normalize_points(points, image_width, image_height)

        # Verificação de pontos duplicados
        unique_points = []
        for point in normalized_points:
            if point in seen_points:
                print(f"Duplicate point found in {json_file}, skipping point {point}.")
                continue
            seen_points.add(point)
            unique_points.append(point)

        # Checar se restaram pelo menos 3 pontos únicos
        if len(unique_points) < 3:
            print(f"After removing duplicates, object in {json_file} has less than 3 points, skipping.")
            continue

        # Formato: class_id x1 y1 x2 y2 ... xn yn
        yolo_annotation = [str(class_id)] + [str(coord) for point in unique_points for coord in point]
        yolo_annotations.append(' '.join(yolo_annotation))

    if yolo_annotations:
        output_file = os.path.join(output_dir, os.path.splitext(os.path.basename(json_file))[0] + '.txt')
        with open(output_file, 'w') as f:
            f.write('\n'.join(yolo_annotations))
    else:
        print(f"No valid annotations found in {json_file}.")


def convert_all_json_in_directory(input_dir, output_dir):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    for filename in os.listdir(input_dir):
        if filename.endswith('.json'):
            json_file = os.path.join(input_dir, filename)
            print(f"Processing {json_file}")
            convert_json_to_yolo_segmentation(json_file, output_dir)


if __name__ == '__main__':

    input_dir = 'Objetos_128_Riser_V2'
    output_dir = 'Objetos_128_Riser_YOLO_V2'

    convert_all_json_in_directory(input_dir, output_dir)
