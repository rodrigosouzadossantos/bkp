import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon


def read_contour_annotations(file_path):
    with open(file_path, 'r') as file:
        lines = file.readlines()

    annotations = []
    current_object = []
    for line in lines:
        if line.strip():
            data = line.strip().split()
            if len(data) == 1:  # Nova classe
                if current_object:
                    annotations.append(current_object)
                    current_object = []
            else:
                class_index = int(data[0])
                points = [(float(data[i]), float(data[i + 1])) for i in range(1, len(data), 2)]
                current_object.append((class_index, points))
    if current_object:  # Adiciona a última anotação
        annotations.append(current_object)

    return annotations


def plot_contours(image_path, annotations):
    image = plt.imread(image_path)
    fig, ax = plt.subplots()
    ax.imshow(image)

    for obj in annotations:
        for class_index, points in obj:
            x = [point[0] * image.shape[1] for point in points]
            y = [point[1] * image.shape[0] for point in points]

            # Ajusta os valores dos pontos para não ultrapassarem os limites da imagem
            x = [max(0, min(image.shape[1] - 1, px)) for px in x]
            y = [max(0, min(image.shape[0] - 1, py)) for py in y]

            ax.plot(x + [x[0]], y + [y[0]], linewidth=2,
                    color='r')  # Adiciona o ponto inicial no final para fechar o contorno

    plt.axis('off')
    plt.show()

if __name__ == '__main__':

    # Path do arquivo de texto com as anotações dos contornos
    annotations_file_path = 'Segmentadas-Niveis-Suto/Facil/0UI5KKDFpZ.txt'

    # Path da imagem correspondente
    image_file_path = 'Segmentadas-Niveis-Suto/Facil/0UI5KKDFpZ.png'

    # Lê as anotações do arquivo
    annotations = read_contour_annotations(annotations_file_path)

    # Plota os contornos na imagem
    plot_contours(image_file_path, annotations)
