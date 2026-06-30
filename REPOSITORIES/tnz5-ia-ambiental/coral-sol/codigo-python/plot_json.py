import glob
import json
import os

import cv2
import numpy as np

if __name__ == '__main__':


    # Criar pasta para salvar as imagens com anotações
    output_folder = 'Objetos_128_Rizer_Plots\\'
    os.makedirs(output_folder, exist_ok=True)

    # Contar imagens se anotação
    not_anot = []
    errors = []

    # Iterar sobre os arquivos na pasta
    j = 0
    for filename in glob.glob("Objetos_128_Rizer\\**"):
        if filename.endswith('.json'):

            try:
                # Caminho do arquivo JSON
                json_path = filename
                with open(json_path) as f:
                    data = json.load(f)

                # Determinar o caminho da imagem com base no nome do arquivo JSON
                image_name = os.path.splitext(filename)[0]
                image_extensions = ['.jpg', '.png', '.JPG']
                image_path = None
                for ext in image_extensions:
                    temp_image_path = os.path.join(image_name + ext)
                    if os.path.exists(temp_image_path):
                        image_path = temp_image_path
                        break

                # Se nenhum arquivo de imagem for encontrado, passar para o próximo arquivo JSON
                if image_path is None:
                    print(f"Imagem correspondente não encontrada para o arquivo JSON: {filename}")
                    continue

                # Carregar a imagem
                img = cv2.imread(image_path)

                # Iterar sobre as anotações no arquivo JSON
                i = 0
                for annotation in data['shapes']:

                    '''if annotation["name"] != "Duto_polygon":
                        continue'''

                    # Verificar se a anotação é do tipo complex_polygon
                    if 'complex_polygon' in annotation:
                        # Carregar os pontos do polígono complexo da anotação atual
                        complex_polygon = annotation['complex_polygon']['path']

                        # Criar uma imagem em branco para desenhar o polígono
                        mask = np.zeros_like(img)

                        # Plotar o polígono complexo
                        for polygon_points in complex_polygon:
                            pts = np.array([[point['x'], point['y']] for point in polygon_points], np.int32)
                            pts = pts.reshape((-1, 1, 2))
                            cv2.polylines(mask, [pts], isClosed=True, color=(255, 0, 0), thickness=1)

                        # Adicionar a máscara à imagem original
                        img = cv2.addWeighted(img, 0.5, mask, 0.5, 0)
                        i += 1
                    else:
                        # Carregar os pontos do polígono
                        polygon_points = annotation.get('points', [])

                        # Carregar a bounding box
                        '''bbox = annotation.get('polygon', {}).get('bounding_box', {})
                        x, y, w, h = bbox.get('x', 0), bbox.get('y', 0), bbox.get('w', 0), bbox.get('h', 0)

                        # Desenhar a bounding box na imagem
                        cv2.rectangle(img, (int(x), int(y)), (int(x + w), int(y + h)), (0, 0, 255), 1)'''

                        # Converter os pontos do polígono para o formato adequado para o OpenCV
                        points = np.array([[int(pt[0]), int(pt[1])] for pt in polygon_points], np.int32)
                        points = points.reshape((-1, 1, 2))

                        # Desenhar o polígono na imagem
                        cv2.polylines(img, [points], isClosed=True, color=(0, 0, 255), thickness=3)
                        i += 1

                if i == 0:
                    not_anot.append(filename)
                    # Salvar a imagem com as anotações
                output_path = os.path.join(output_folder, image_name + '_annotated.jpg').replace(
                    "Objetos_128_Rizer\\",
                    "")
                cv2.imwrite(output_path, img)
                print(output_path)

                if j > 1000:
                    break
                j = j + 1

            except Exception as exp:
                print(exp)
                errors.append(filename)

    print(len(not_anot))
    print(not_anot)

    print(len(errors))
    print(errors)
