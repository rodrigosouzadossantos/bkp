import os
import shutil

from PIL import Image

# Diretório onde estão as imagens
diretorio_imagens = 'Completo - All/Completo-Crop-V2'

# Pasta destino para cada categoria
pasta_rizer = 'Estruturas/Rizer'
pasta_outros = 'Estruturas/Outros'

# Cria as pastas de destino se não existirem
os.makedirs(pasta_rizer, exist_ok=True)
os.makedirs(pasta_outros, exist_ok=True)

# Lista de imagens no diretório
imagens = [
    imagem
    for imagem in os.listdir(diretorio_imagens)
    if (imagem.endswith('.png') or imagem.endswith('.jpg'))
       and imagem not in os.listdir(pasta_rizer)
       and imagem not in os.listdir(pasta_outros)
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

    if categoria == 'r':
        destino = os.path.join(pasta_rizer, imagem)
    elif categoria == 'o':
        destino = os.path.join(pasta_outros, imagem)

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
        tecla = input("Digite a tecla ('r' para rizer, 'o' para outros): ").strip().lower()

        if tecla in ['r', 'o']:
            copiar_imagem(imagens[indice_imagem_atual], tecla)
            proxima_imagem()
        else:
            print("Tecla inválida. Digite 'r', 'o'.")
