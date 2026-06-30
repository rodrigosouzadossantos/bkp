import tensorflow as tf
from tensorflow.keras.models import load_model, Model
from tensorflow.keras.applications.densenet import preprocess_input
from tensorflow.image import resize
import pandas as pd
import numpy as np
import cv2
import os


def get_model(models_path: str)-> Model:
    """
        Carrega o modelo treinado
        Parametros:
            models_path: caminho absoluto do arquivo .h5 do modelo treinado
        Retorno: O modelo
    """
    tf.compat.v1.logging.set_verbosity(tf.compat.v1.logging.FATAL)    
    model = load_model(models_path, compile=False)
    return model

def get_dataframe_class(class_csv_path: str)-> list:
    """
        Transforma as colunas de um dataframe em uma lista de classes
        Parametros:
            class_csv_path: caminho absoluto do arquivo csv
        Retorno: lista de classes
        
    """
    class_df = pd.read_csv(class_csv_path)
    class_values = class_df.columns
    sequence = pd.Series(class_values)
    list_class = sequence.tolist()
    return list_class


def load_classes_to_predict(columns_to_rename: list, columns_renamed: list, training_file_class: str)-> list:
    """
       Faz a leitura do arquivo que contem todas as classes usadas no treinamento e renomeia as classes que precisam ser renomeadas
       Parametros:
           columns_to_rename: lista com o nome das colunas do dataframe que serão renomeadas
           training_file_class: lista que contém as classes utilizadas no treinamento do modelo
       Retorno: lista de classes
    """
    inspection_classes = pd.read_csv(training_file_class)
    try:
        inspection_classes = inspection_classes['Classes']
    except:
        inspection_classes = inspection_classes.columns[1::]

    for col_idx, col in enumerate(columns_to_rename):
        inspection_classes = np.array([columns_renamed[col_idx] if item == col else item for item in inspection_classes])
    return inspection_classes

def get_list_names_images(dataframe_teste: pd.DataFrame)-> list:
    """
        Paga a primeira coluna do dataframe que refere-se aos nomes das imagens
        Parametros:
            dataframe_teste: Dataframe que contém o nome das imagens na primeira coluna
        Retorno: Uma lista com o os nomes das imagens
    """
    list_images_names = dataframe_teste.iloc[:, 0].values
    return list_images_names

def preprocessing_image_to_predict(image_path: str, IMG_SIZE: tuple)-> np.ndarray:  
    """
        Faz a leitura da imagem e realiza o pré-processamento própria da DenseNet e interpolação linear para o resize da imagem
        Parametros:
            image_path: caminho absoluto da imagem que será pré-processada
            IMG_SIZE: tupla com Altura e Largura da imagem no formato (Altura, Largura)
        Retorno: Imagem convertido para um array numpy
    """
    tf.compat.v1.logging.set_verbosity(tf.compat.v1.logging.FATAL)   
    image = cv2.imread(image_path)
    image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    image = cv2.resize(image, IMG_SIZE, interpolation=cv2.INTER_LINEAR)
    image = preprocess_input(image)
    image = np.expand_dims(image, 0)
    return image

def jaccard_distance(y_true: np.ndarray, y_pred: np.ndarray)-> np.ndarray:
    """
        Calcula a distância de Jaccard. A distância de Jaccard é calculada como 1 - (interseção / união). Isso resulta em uma métrica que varia de 0 a 1, 
        onde 0 indica uma correspondência perfeita entre y_true e y_pred, e 1 indica nenhuma correspondência. Quanto menor o valor, mais similaridade entre as matrizes.
        Parametros:
            y_true: matriz que contém as classes verdadeiras
            y_pred: matriz que contém as classes previstas
        Retorno: Matriz de similaridade com valores entre 0 e 1
    """
    intersection = K.sum(K.abs(y_true * y_pred), axis=-1)
    union = K.sum(y_true, axis=-1) + K.sum(y_pred, axis=-1) - intersection
    return 1 - (intersection / union)

def predict_images(model: Model, model_shape: list, class_test: list, images_names: list, images_folder_path: str)-> (list, list):
    """
        Realiza a predição para cada imagem de uma lista de imagens
        Parametros:
            model: modelo treinado
            model_shape: lista com informações referentes ao modelo
            class_test: lista de classes
            images_names: lista com os nomes das imagens para teste
            images_folder_path: caminho absoluto da pasta onde estão localizadas as imagens de teste
        Retorno: Uma lista com as probabilidades de cada classe (valores entre 0 e 1) para cada imagem e uma lista com as classes com probabilidade maior que 0.5 para cada imagem
    """
    inferences = []
    score_inferences = [['nome'] + class_test.tolist()]
    count = 0
    print(score_inferences)
    
    for image_name in images_names:
        image_path = os.path.join(images_folder_path, image_name)
       
        if os.path.isfile(image_path):
            print(image_name)            
            image = preprocessing_image_to_predict(image_path, (model_shape[1], model_shape[2]))

            preds_result = model.predict(image)
            score_inferences.append([image_name] + preds_result[0].tolist())

            preds_result = preds_result >= 0.5
            inferences.append([image_name] + class_test[preds_result[0]].tolist())
        else:
            print('A imagem', image_path, 'não existe na pasta.')
            count += 1
    print('Total de imagens não encontradas: ', str(count))
    
    return inferences, score_inferences

def generate_dataframe_inference_crisp(list_inferences: list)-> pd.core.frame.DataFrame:
    """
        Constroi um daframe com o resultados da inferencia, no qual cada coluna representa uma classe. Caso a classe esteja presente na imagem, recebe 1, caso contrário, recebe 0
        Parametros:
            inferences: lista resultante da predição do modelo para as imagens
        Retorno: Dataframe com todas as classes. Classes com valores 0 significa a ausencia da classe e 1, a presença da classe na imagem
    """
    # Get all unique classes
    all_classes = set()
    for item in list_inferences:
        all_classes.update(item[1:])
        
    dataframe_inference = {
    'Image': [item[0] for item in list_inferences]
    }
    
    # Initialize the columns for each class with 0
    for class_name in all_classes:
        dataframe_inference[class_name] = [0] * len(list_inferences)
        
    for i, item in enumerate(list_inferences):
        for class_name in item[1:]:
            dataframe_inference[class_name][i] = 1
    
    return pd.DataFrame(dataframe_inference)

def generate_dataframe_inference(list_score_inferences: list)-> pd.core.frame.DataFrame:
    """
        Controi um dataframe com a probabilidade de cada classe estar presente nas imagens 
        Parametros:
            list_score_inferences: lista com todas as classes e suas respectivas probabilidades para cada imagem utilzada no teste
        Retorno: Dataframe com as classes e suas respectivas probabilidades 
    """
    
    dataframe_score_inference = pd.DataFrame(list_score_inferences)
    dataframe_score_inference.columns = dataframe_score_inference.iloc[0]
    dataframe_score_inference = dataframe_score_inference[1:]
    return dataframe_score_inference