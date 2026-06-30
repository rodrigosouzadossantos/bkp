import glob
import json

import cv2 as cv

# Caminhos dos arquivos e diretórios
image_dir = 'Completo'
output_image_dir = 'Completo-Crop-V2'

# Tabela de coordenadas de corte
crop_table = {

    # DOF
    'AB_CHIab23_049': {'y_up': 175, 'y_down': 770},
    'AB_CHIab23_050': {'y_up': 175, 'y_down': 770},
    'SACna23_055': {'y_up': 175, 'y_down': 770},

    # DOF subsea
    'CH_SKCch22_343': {'y_up': 170, 'y_down': 720},
    'CH_SKCch23_699': {'y_up': 170, 'y_down': 720},
    'GP_SKCgp22_304': {'y_up': 170, 'y_down': 720},
    'GP_SKCgp23_501': {'y_up': 170, 'y_down': 720},
    'SKCna23_414': {'y_up': 170, 'y_down': 720},
    'UEH_PNA-1ESDV-MIS-MRL-01': {'y_up': 170, 'y_down': 720},

    # DOF subsea - invertido
    'GP_SRgp23_070': {'y_up': 185, 'y_down': 760},

    # DOF subsea - invertido - V2
    'RO_SFro23_307': {'y_up': 300, 'y_down': 780},

    # DOF subsea - invertido - V3
    'COMco24_025': {'y_up': 190, 'y_down': 700},
    'COMll24_033': {'y_up': 190, 'y_down': 700},
    'COMll24-033': {'y_up': 190, 'y_down': 500},
    'COMmls24_010': {'y_up': 190, 'y_down': 700},
    'SOLjub24-079': {'y_up': 190, 'y_down': 700},
    'SOLjub24-080': {'y_up': 190, 'y_down': 700},

    # CI
    'CH_BBch23_116': {'y_up': 230, 'y_down': 630},
    'CH_BBch23_119': {'y_up': 230, 'y_down': 630},
    'TUP_DEKtup23_167': {'y_up': 230, 'y_down': 630},
    'TUP_DEKtup23_170': {'y_up': 230, 'y_down': 630},
    'TUP_DEKtup23_176': {'y_up': 230, 'y_down': 630},
    'TUP_DEKtup23_179': {'y_up': 230, 'y_down': 630},
    'TUP_DEKtup23-169': {'y_up': 230, 'y_down': 630},
    'BGbuz23_170': {'y_up': 230, 'y_down': 630},
    'BGtup23-096': {'y_up': 230, 'y_down': 630},
    'BGtup23-114': {'y_up': 230, 'y_down': 630},
    'BGtup23-115': {'y_up': 230, 'y_down': 630},
    'BGtup23-117': {'y_up': 230, 'y_down': 630},
    'BGtup23-119': {'y_up': 230, 'y_down': 630},
    'BGtup23-123': {'y_up': 230, 'y_down': 630},
    'BGtup23-125': {'y_up': 230, 'y_down': 630},
    'BGtup23-126': {'y_up': 230, 'y_down': 630},
    'BGtup23-128': {'y_up': 230, 'y_down': 630},
    'BGtup23-132': {'y_up': 230, 'y_down': 630},
    'BGtup23-134': {'y_up': 230, 'y_down': 630},
    'BGtup23-135': {'y_up': 230, 'y_down': 630},
    'GP_BBgp23_113': {'y_up': 230, 'y_down': 630},

    # CI - menor
    'TUP_DEKtup23_100': {'y_up': 100, 'y_down': 270},
    'TUP_DEKtup23_101': {'y_up': 100, 'y_down': 270},
    'TUP_DEKtup23_107': {'y_up': 100, 'y_down': 270},
    'BGbuz23_146': {'y_up': 100, 'y_down': 270},
    'BGbuz23_154': {'y_up': 100, 'y_down': 270},
    'BGbuz23_160': {'y_up': 100, 'y_down': 270},
    'BGbuz23_164': {'y_up': 100, 'y_down': 270},
    'BGbuz23_165': {'y_up': 100, 'y_down': 270},
    'BGbuz23_169': {'y_up': 100, 'y_down': 270},
    'BGbuz23_173': {'y_up': 100, 'y_down': 270},
    'BGtup23_098': {'y_up': 100, 'y_down': 270},
    'DEKtup23-159': {'y_up': 100, 'y_down': 270},
    'WBbuz23-091': {'y_up': 100, 'y_down': 270},

    # CI - menor - 2
    'JGtup23_167': {'y_up': 60, 'y_down': 330},
    'JGtup23-164': {'y_up': 60, 'y_down': 330},
    'JGtup23-166': {'y_up': 60, 'y_down': 330},

    # CI - maior
    'BGbuz23_171': {'y_up': 220, 'y_down': 650},
    'BGbuz23_172': {'y_up': 220, 'y_down': 650},
    'BGtup23-136': {'y_up': 220, 'y_down': 650},
    'TUP_DEKtup23_123': {'y_up': 220, 'y_down': 650},
    'TUP_DEKtup23_160': {'y_up': 220, 'y_down': 650},

    # CI - maior - 2
    'BSch23-121': {'y_up': 150, 'y_down': 750},

    # CI - maior - 3
    'GP_BBgp23_127': {'y_up': 230, 'y_down': 620},

    # Oceaneering
    'CH_CMch23_198': {'y_up': 175, 'y_down': 830},
    'CMch23-197': {'y_up': 175, 'y_down': 830},
    'CMna23_201': {'y_up': 175, 'y_down': 830},
    'GP_CMgp23_206': {'y_up': 175, 'y_down': 830},

    # OceanPact
    'RO_AAro23_206': {'y_up': 120, 'y_down': 850},
    'RO_AAro23_260': {'y_up': 120, 'y_down': 850},

    # OceanPact - encima
    'RO_AAro23_323': {'y_up': 190, 'y_down': 750},
    'RO_AAro23_329': {'y_up': 190, 'y_down': 750},
    'GA_PNA-1CABIÚNAS 20': {'y_up': 190, 'y_down': 750},
    'PDTna24_002': {'y_up': 190, 'y_down': 750},

    # OceanPact - menor
    'GA_PLAEM-NA-01PNA-1': {'y_up': 100, 'y_down': 390},

    # OceanPact - maior
    'PDTna22_017': {'y_up': 200, 'y_down': 700},

    # i-Tech
    'VL_AAvl20_116': {'y_up': 160, 'y_down': 730},

    # Belov
    'GL_PCH1_MSGL_AN': {'y_up': 220, 'y_down': 750},

    # Belov - menor
    'KL_PGP1_PNA1': {'y_up': 60, 'y_down': 340},
    'KL_PNA1_PNA2': {'y_up': 60, 'y_down': 340},

    # Belov - menor - 2
    'KL_PNA_1MSIPG_NA1': {'y_up': 60, 'y_down': 260},
    'KL_PNA-1MSIPG-NA-1': {'y_up': 60, 'y_down': 260},
    'O_PCH-1PNA-1-B 12 SEM RS': {'y_up': 60, 'y_down': 260},
    'UEH_PCH-1CJ-4_PCH-1(MSGL-AN) SEM RS': {'y_up': 60, 'y_down': 260},

    # Belov - menor - 3
    'O_PNA-2PNA-1 B 10': {'y_up': 70, 'y_down': 410},

    # SIRGAS
    'GP_CGgp20_158': {'y_up': 100, 'y_down': 310},

    # Oceânica
    'LL_SUB9ll23_107': {'y_up': 160, 'y_down': 770},
    'SUB9buz23_038': {'y_up': 160, 'y_down': 770},
    'SUB9buz23_078': {'y_up': 160, 'y_down': 770},
    'SUB9buz23_079': {'y_up': 160, 'y_down': 770},
    'SUB9buz23_081': {'y_up': 160, 'y_down': 770},
    'SUB9buz23_083': {'y_up': 160, 'y_down': 770},
    'SUB9buz23_084': {'y_up': 160, 'y_down': 770},
    'SUB9buz23-072': {'y_up': 160, 'y_down': 770},
    'SUB9buz23-073': {'y_up': 160, 'y_down': 770},
    'SUB9buz23-075': {'y_up': 160, 'y_down': 770},
    'SUB9tup24-008': {'y_up': 160, 'y_down': 770},

    # Oceânica - menor
    'SUB9buz23_021': {'y_up': 160, 'y_down': 340},

    # Oceânica - menor - 2
    'SUB9buz23_026': {'y_up': 60, 'y_down': 350},
    'SUB9buz23_039': {'y_up': 60, 'y_down': 350},
    'SUB9buz23_040': {'y_up': 60, 'y_down': 350},
    'SUB9buz23_042': {'y_up': 60, 'y_down': 350},
    'SUB9buz23_046': {'y_up': 60, 'y_down': 350},
    'SUB9buz23_049': {'y_up': 60, 'y_down': 350},
    'SUB9buz23_064': {'y_up': 60, 'y_down': 350},
    'SUB9buz23_066': {'y_up': 60, 'y_down': 350},
    'SUB9buz23_082': {'y_up': 60, 'y_down': 350},
    'SUBbuz23_051': {'y_up': 60, 'y_down': 350},
    'SUBbuz23_052': {'y_up': 60, 'y_down': 350},
    'SUBbuz23_060': {'y_up': 60, 'y_down': 350},

    # Oceânica - menor - 3
    'SUB9buz23_085': {'y_up': 70, 'y_down': 350},

    # n/a
    'O_PNA1_PGP1B_16_sem_rs': {'y_up': 80, 'y_down': 320},
    'TGL_PNA-2MSGL-NA': {'y_up': 110, 'y_down': 490},
    'UH_PGP-18-GP-029 SEM RS': {'y_up': 120, 'y_down': 230},

}


def adjust_annotation(annotation, top_offset, bottom_offset, original_height, image_path, sem_anot):
    """ Ajusta a anotação conforme os deslocamentos y para segmentação (polygon) """
    adjusted_objects = []
    seen_objects = set()

    for obj in annotation['shapes']:
        adjusted_polygon = []
        seen_points = set()

        for point in obj['points']:
            new_y = point[1] - top_offset
            if new_y < 0:
                new_y = 0
            elif new_y > (top_offset + bottom_offset):
                new_y = top_offset + bottom_offset

            adjusted_point = (point[0], new_y)

            if adjusted_point not in seen_points:
                seen_points.add(adjusted_point)
                adjusted_polygon.append(adjusted_point)

        # Verifica se todos os pontos ajustados têm o mesmo valor de y
        y_values = [p[1] for p in adjusted_polygon]
        if len(set(y_values)) > 1:
            obj['points'] = list(map(list, adjusted_polygon))  # Converte de volta para lista de listas
            obj_tuple = (tuple(map(tuple, adjusted_polygon)), obj['label'])
            if obj_tuple not in seen_objects:
                seen_objects.add(obj_tuple)
                adjusted_objects.append(obj)

    if len(adjusted_objects) == 0:
        print("imagem sem anotação")
        print(image_path)
        sem_anot += 1

    annotation['shapes'] = adjusted_objects
    return annotation, sem_anot


def find_folder(image_name, crop_table):
    for crop in crop_table.items():
        if crop[0] in image_name:
            return crop[1]['y_up'], crop[1]['y_down']

    return 0, 0


def process_images_and_annotations(image_dir, crop_table):
    erros = []
    erros_type = []
    sem_anot = 0
    for image_name in glob.glob(image_dir + "\\**.jpg"):

        try:
            # Encontra os valores de y_up e y_down para remover overlay
            y_up, y_down = find_folder(image_name, crop_table)

            # Caminhos completos para imagem e anotação
            image_path = image_name.split("\\")[-1]
            annotation_path = image_name.replace("jpg", "json")

            # Carregar imagem usando OpenCV
            img = cv.imread(image_name)
            original_height, original_width = img.shape[:2]

            # Definir a área de corte (cima e baixo)
            cropped_img = img[y_up:y_down + y_up, :]
            cropped_image_path = output_image_dir + "\\" + image_path

            # Salvar a imagem recortada com a máxima qualidade
            cv.imwrite(cropped_image_path, cropped_img, [cv.IMWRITE_JPEG_QUALITY, 100])

            # Carregar anotação
            with open(annotation_path, 'r') as f:
                annotation = json.load(f)

            # Ajustar anotação
            adjusted_annotation, sem_anot = adjust_annotation(annotation, y_up, y_down, original_height, image_path,
                                                              sem_anot)

            # Salvar a anotação ajustada
            adjusted_annotation_path = output_image_dir + "\\" + annotation_path.split("\\")[-1]
            with open(adjusted_annotation_path, 'w') as f:
                json.dump(adjusted_annotation, f, indent=4)
        except Exception as exp:
            erros.append(image_name)
            erros_type.append(exp)

    print(erros)
    print(erros_type)

    print("Imagens sem anotação: " + str(sem_anot))


if __name__ == '__main__':
    # Executar o processamento
    process_images_and_annotations(image_dir, crop_table)
