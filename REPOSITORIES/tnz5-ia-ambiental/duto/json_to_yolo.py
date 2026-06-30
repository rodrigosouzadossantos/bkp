import glob
import json

from shapely.geometry import Polygon


def adjust_point(x, y, width, height):
    # Verifica se as coordenadas estão dentro dos limites da imagem
    x = min(max(x, 0), width)
    y = min(max(y, 0), height)
    return x, y


def complex_to_individual_polygons(points):
    # Transforma os pontos em um polígono Shapely
    complex_polygon = Polygon(points)

    # Se o polígono não for válido, retorna uma lista vazia
    if not complex_polygon.is_valid:
        return []

    # Separa o polígono complexo em polígonos individuais (caso ele seja composto de buracos)
    individual_polygons = [complex_polygon]
    for interior in complex_polygon.interiors:
        individual_polygons.append(Polygon(interior))

    return individual_polygons


def json_to_annotation(json_data):
    annotations = json_data["shapes"]
    image_width = json_data["imageWidth"]
    image_height = json_data["imageHeight"]
    annotation_lines = []

    for annotation in annotations:
        if annotation["shape_type"] == "polygon":
            polygon_path = annotation["points"]
            annotation_line = str(0)

            for point in polygon_path:
                x = min(max(point[0] / image_width, 0), 1)
                y = min(max(point[1] / image_height, 0), 1)
                annotation_line += f" {x} {y}"

            annotation_lines.append(annotation_line)

        elif "complex_polygon" == annotation["shape_type"]:
            complex_polygon_path = annotation["complex_polygon"]["path"]
            class_id = annotation["slot_names"][0]  # Assume apenas uma classe por objeto

            for subpath in complex_polygon_path:
                complex_polygon_points = [(point["x"], point["y"]) for point in subpath]
                individual_polygons = complex_to_individual_polygons(complex_polygon_points)

                for polygon in individual_polygons:
                    annotation_line = class_id
                    for p in polygon.exterior.coords:
                        x, y = adjust_point(p[0] / image_width, p[1] / image_height, 1, 1)
                        annotation_line += f" {x} {y}"
                    annotation_lines.append(annotation_line)

    return annotation_lines


if __name__ == '__main__':

    for filename in glob.glob("Segmentadas-Niveis-Suto/**/**.json"):
        with open(filename) as json_file:
            data = json.load(json_file)

        annotations = json_to_annotation(data)

        output_file_path = filename.replace("json", "txt")
        with open(output_file_path, "w") as output_file:
            for annotation_line in annotations:
                output_file.write(annotation_line + "\n")
