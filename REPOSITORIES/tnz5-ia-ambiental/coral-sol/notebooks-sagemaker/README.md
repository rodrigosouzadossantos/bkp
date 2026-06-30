# Coral-Sol - Notebooks usados no Sagemaker

> Nessa pasta, estão contidos todos os jupyter notebooks usados no Sagemaker.

### Pastas

- analise-modelo-MSOV1
    - density.ipynb: Código utilizado para avaliar a densidade de coral, usando o modelo de coral e duto.
    - model_metrics.ipynb: Código utilizado para fazer a inferência do modelo de coral e duto, para analisar as
      métricas e resultados do modelo de coral.
- predicoes-modelo-class-V1
    - analize_model.ipynb: Código usado para avaliar o modelo V1 de classificação de coral-sol, no dataset legado da
      PUC.
- predicoes-modelo-qualidade
    - image_quality.ipynb: Inferência do modelo de qualidade em um conjunto de imagen de coral-sol.
- predicoes-MSOV1
    - prediction_model-mergulho.ipynb: Notebook usado para analisar a predição do modelo MSO-V1 em imagens de mergulho (
      sem
      anotação).
    - prediction_model_vs_expert-com-revisão.ipynb: Notebook usado para comparar predição do modelo MSO-V1 com as
      anotações
      revisadas do Lote 4 (18 imagens).
    - prediction_model_vs_expert-mergulho.ipynb: Notebook usado para comparar predição do modelo MSO-V1 com as anotações
      em
      imagens de mergulho (15 imagens).
    - prediction_model_vs_expert-sem-revisão.ipynb: Notebook usado para analisar a predição do modelo MSO-V1 nas imagens
      do
      Lote 4 e 5 (sem revisão).
- provas-de-fogo-MSOV1
    - prova-de-fogo-v1.ipynb: Notebook usado para gerar vídeo com sobreposição da máscara predita pelo modelo de Coral +
      Gráfico de predição (binária) ao longo do tempo do vídeo.
    - prova-de-fogo-v2.ipynb: Notebook usado para gerar vídeo com sobreposição dos contornos preditos pelo modelo de
      Coral +
      Gráficos e CSV com as probabilidades dos contornos.
- treinamento-densenet121
    - train_model.ipynb: Treinamento e avaliação geral do modelo treinado com Densenet121.
- treinamento-yolov8
    - train_coral_v1.ipynb: Treinamento da YOLOv8 (versão genérica).
    - coral.yaml: Arquivo de configurações da YOLOv8 (versão genérica).