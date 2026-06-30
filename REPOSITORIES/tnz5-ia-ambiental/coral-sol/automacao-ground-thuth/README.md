# Orquestrador de CSV e Predições - AWS Ground Thuth

## ANTES DE EXECUTAR O CÓDIGO:

- Crie a seguinte estrutura de pastas:
  ```
  GT
  ├───Bucket-Input-Versions
  ├───Bucket-Output-Versions
  ├───CSV-Versions
  └───Prediction-Versions
   ```
- As pasta de imagens originais usadas nos jobs, ficará em Bucket-Input-Versions.
- As pastas de imagens anotadas usadas nos jobs, ficará em Bucket-Output-Versions, versionado por data.
- Os CSVs de monitoramento ficam em CSV-Versions, versionado por data.
- As imagens já anotadas, são inferidas pelo modelo MSO-V1 e salvas em Prediction-Versions, versionado por data. 
- Crie um arquivo .env, que deve ter:
    ```
        [Chaves da conta - AWS-DSM56649-SBX]
        aws_access_key_id=XXXXXXXXXXXXXXXX
        aws_secret_access_key=YYYYYYYYYYYYYYYYYYYYYY
        aws_session_token=ZZZZZZZZZZZZZZZZZZZZZ
        [Chaves da conta - AWS-00030-PRD]
        aws_access_key_id_30_prd=AAAAAAAAAAAAAAAAAAAAAAAAAA
        aws_secret_access_key_30_prd=BBBBBBBBBBBBBBBBBBBBBBB
    ```
- Crie uma .venv com as bibliotecas que estão no arquivo requirements.txt
    - OBS: você deve se certificar que o path para a sua venv esteja configurado na linha 16 do arquivo orquestrator.py:

          venv_dir = r'.venv'

## EXECUÇÃO DO ORQUESTRADOR

- A lógica do orchestrator.py é:
    - Obtem o path da sua .venv, que já deve ter as bibliotecas padrões configuradas (se for preciso, use o
      requeriments.txt). Após verificar se a .venv existe, ele executa os outros arquivos python de forma linear.
- Primeiro, ele irá executar o arquivo get_data_s3.py
    - Lembre-se: configurar as variáveis a seguir
   ```
       output_bucket_name = 's3-dsm-groundtruth-output-637423571944-us-east-1'
       input_bucket_name = 's3-dsm-groundtruth-input-637423571944-us-east-1'
       prefix_output = 'imagens-lote-4-5/rotulacao-lotes-4-5'
       prefix_input = 'imagens-lote-4-5'
   ```
    - input_bucket_name: path do bucket, onde está as imagens originais do job.
    - output_bucket_name: path do bucket, onde está salvo as anotações do job.
    - prefix_input: path interno do bucket, onde está as imagens originais do job.
    - prefix_output: path interno do bucket, onde está salvo as anotações do job.
    - OBS: Ele baixa as imagens originais apenas UMA vez, e baixa as anotações UMA VEZ NO DIA.
- Segundo, será executado o monitoring.py
    - Lembre-se de configurar a variável a seguir:
    ```
      prefix = 'imagens-lote-4-5/rotulacao-lotes-4-5'
    ```
    - prefix: path interno do bucket, onde está salvo as anotações do job.
    - Nesse código, ele vai montar um CSV com as seguintes informações:
        - workerName: nome do anotador.
        - acceptanceTime: dia e hora que o anotador começou a anotar a imagem.
        - submissionTime: dia e hora que o anotador finalizou a anotação da imagem.
        - timeSpentInSeconds: tempo que o anotador levou para anotar a imagem.
        - annotated_image_path: path da imagem anotada.
- Terceiro, será executado o arquivo prediction.py
    - Lembre-se de configurar as variáveis a seguir:
    ```
       prefix_output = 'imagens-lote-4-5/rotulacao-lotes-4-5'
       prefix_input = 'imagens-lote-4-5'
    ```
    - prefix_input: path interno do bucket, onde está as imagens originais do job.
    - prefix_output: path interno do bucket, onde está salvo as anotações do job.
    - Nesse código, ele executará os modelos de segmentação de duto e o modelo de segmentação de coral-sol, calcula a
      intersecção das máscaras e gera uma imagem jpg mostrando a comparação entre a anotação do especialista e os
      resultados obtidos pelo modelo.
- Quarto e último arquivo
    - Nesse código, será enviado tudo que está nas pastas CSV-Versions e Prediction-Versions para nossa conta da AWS,
      versionado por data.

## TODO:
- [ ] Automação completa do orquestrador
- [ ] Refatoração do Código
- [ ] Passar variável mutáveis para variáveis de linha de comando

