# Segmentação de Dutos

> Nessa pasta, estão contidos todos os arquivos referentes ao projeto ambiental, voltado a tarefa de segmentação de dutos.

### Histórico

- Versão 1
  - Foram usadas 1100 imagens obtidas pela Petrobrás, onde as imagens tinham uma segmentação (polygon e complex polygon) de um ou mais dutos nas imagens.
  - Foi optado por treinar a YOLOv8, com 500 epochs
  - Os resultados foram medianos, e após uma analise mais aprofundada, notou-se que o dataset continha anotações incorretas e imagens muito complexas.
- Versão 2
  - Foi optado por separar as imagens em níveis de dificuldade, sendo eles: fácil, médio, difícil e remoção (imagens que não seriam utilizadas)
  - Após a separação, ficaram 143 (fácil), 171 (médio), 246 (difícil) e 406 (remoção)
  - Para aumento de dataset, foram obtidas mais 609 imagens
  - Essas imagens foram segmentadas, sendo apenas do tipo polygon
  - Após a segmentação, foi repetido o processo de separação de níveis, onde o resultado foi: 142 (fácil), 239 (médio), 219 (difícil) e 9 (remoção)
  - Ao total o dataset foi juntado, resultando em:
    *  285 - fácil
    *  410 - médio
    *  465 - difícil
    *  415 - remoção

### Arquivos
  - clean_images.py : utilizado para movimentar as imagens, jsons e txt entre as pastas
  - json_to_yolo.py : conversor do formato .json ao formato yolo, para treinamento do modelo
  - plot_yolo_annotation.py : visualizador das anotações YOLO com sua respectiva imagem
  - plot_json_annotation.ipynb : visualizador das anotações json com sua respectiva imagem
  - separate_levels.py : ferramenta construída para separar as imagens nos níveis comentados acima
  - train_yolov8.ipynb : treinamento da YOLOv8
  - duto.yaml : arquivo de configurações da YOLOv8
  - Treinamentos - Segmentacção - Duto.pdf : resultados obtidos nos treinamentos em níveis - v2

### Pastas
  - pesos
    *  v1: pesos dos modelos treinados sem nível
    *  v2: pesos dos modelos treinados com nível
 




