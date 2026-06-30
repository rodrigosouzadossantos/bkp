# Coral-Sol - Códigos usados localmente (Python)

> Nessa pasta, estão contidos todos os arquivos referentes aos códigos rodados localmente em python, normalmente usados
> para tarefas mais genéricas, como cortar imagens, mover arquivos e plotar anotações.

### Arquivos

- crop_overlay.py: Utilizado para cortar o overlay das imagens a partir da pasta fonte, de maneira customizada por OS ou
  Empresa.
- crop_train.py: Utilizado para cortar as imagens e anotações em 128x128 pixels, com as respectivas tratativas.
- json_to_yolo.py: Utilizado para converter as anotações .json para o formato YOLO (.txt).
- plot_json.py: Visualizador das anotações JSON com sua respectiva imagem.
- plot_yolo_annotation.py: Visualizador das anotações YOLO com sua respectiva imagem.
- remove_duplicates.py: Utilizado para a análise de imagens duplicadas e remoção das mesmas no dataset.
- separate_levels.py: Ferramenta construída para separar as imagens em duto ou outras estruturas (versão genérica).
- generate_classification_data_augmentation.py.py: Utilizado para fazer data augmentation em um conjunto de dados (
  aumentado em 3 vezes o tamanho original).
- generate_classification_dataset.py.py: Utilizado para gerar o dataset de classificação, gerando as pastas de train,
  test e val.
- generate_classification_patches.py.py: Utilizado para gerar patches a partir das imagens originasi dos Lotes 1, 2 e 3,
  separando em positivo e negativo de acordo com a anotação de segmentação.