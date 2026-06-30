import os
import shutil
import matplotlib.image as mpimg
import matplotlib.pyplot as plt
import cv2
from PIL import Image

# Diretório onde estão as imagens
diretorio_imagens = 'Segmentadas-Duto-2006'

# Pasta destino para cada categoria
pasta_facil = 'Segmentadas-Niveis-Suto/Facil'
pasta_medio = 'Segmentadas-Niveis-Suto/Medio'
pasta_dificil = 'Segmentadas-Niveis-Suto/Dificil'
pasta_remover = 'Segmentadas-Niveis-Suto/Remocao'

# Cria as pastas de destino se não existirem
os.makedirs(pasta_facil, exist_ok=True)
os.makedirs(pasta_medio, exist_ok=True)
os.makedirs(pasta_dificil, exist_ok=True)
os.makedirs(pasta_remover, exist_ok=True)

# Lista de imagens no diretório
imagens = [
    imagem
    for imagem in os.listdir(diretorio_imagens)
    if (imagem.endswith('.png') or imagem.endswith('.jpg'))
       and imagem not in os.listdir(pasta_facil)
       and imagem not in os.listdir(pasta_medio)
       and imagem not in os.listdir(pasta_dificil)
       and imagem not in os.listdir(pasta_remover)
]

# Índice da imagem atual
indice_imagem_atual = 0

# Função para exibir imagem
def exibir_imagem(indice):
    imagem_atual = imagens[indice]
    img_path = os.path.join(diretorio_imagens, imagem_atual)
    img = Image.open(img_path)
    img.show()
    return imagem_atual


# Função para copiar imagem para a pasta correspondente
def copiar_imagem(imagem, categoria):
    img_path = os.path.join(diretorio_imagens, imagem)
    txt_path = img_path.replace("png", "json").replace("jpg", "json")

    if categoria == 'f':
        destino = os.path.join(pasta_facil, imagem)
    elif categoria == 'm':
        destino = os.path.join(pasta_medio, imagem)
    elif categoria == 'd':
        destino = os.path.join(pasta_dificil, imagem)
    elif categoria == 'r':
        destino = os.path.join(pasta_remover, imagem)

    shutil.copyfile(img_path, destino)
    destino_txt = destino.replace("png", "json").replace("jpg", "json")
    if os.path.exists(txt_path):
        shutil.copyfile(txt_path, destino_txt)

# Função para exibir a próxima imagem
def proxima_imagem():
    global indice_imagem_atual
    indice_imagem_atual += 1
    if indice_imagem_atual < len(imagens):
        exibir_imagem(indice_imagem_atual)
    else:
        print("Todas as imagens foram classificadas!")
        exit(0)  # Encerra o script após classificar todas as imagens

if __name__ == '__main__':
    # Exibir a primeira imagem
    if imagens:
        exibir_imagem(indice_imagem_atual)
    else:
        print("Não há imagens no diretório.")
        exit(0)  # Encerra o script se não houver imagens para processar

    while True:
        # Recebe a tecla digitada pelo usuário
        tecla = input("Digite a tecla ('f' para fácil, 'm' para médio, 'd' para difícil, 'r' para remover): ").strip().lower()

        if tecla in ['f', 'm', 'd', 'r']:
            copiar_imagem(imagens[indice_imagem_atual], tecla)
            proxima_imagem()
        else:
            print("Tecla inválida. Digite 'f', 'm', 'd' ou 'r'.")
