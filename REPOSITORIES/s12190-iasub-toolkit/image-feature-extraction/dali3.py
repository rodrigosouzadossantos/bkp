import boto3
import os
import shutil
import nvidia.dali.pipeline as pipeline
import nvidia.dali.fn as fn

os.environ['CURL_CA_BUNDLE'] = ''

def read_s3_with_dali(bucket, key, local_cache_dir="./cache"):
    """Lê imagem de S3 com estrutura que DALI espera"""

    s3_client = boto3.client('s3')

    # Criar estrutura: cache/0/image.jpg (DALI precisa de subdir com classe)
    class_dir = os.path.join(local_cache_dir, "0")
    os.makedirs(class_dir, exist_ok=True)

    # Baixar arquivo
    filename = os.path.basename(key)
    filepath = os.path.join(class_dir, filename)

    data = s3_client.get_object(Bucket=bucket, Key=key)
    with open(filepath, 'wb') as f:
        f.write(data['Body'].read())

    print(f"✓ Arquivo baixado: {filepath}")
    print(f"✓ Estrutura: {local_cache_dir}/0/{filename}")

    # Processar com DALI
    pipe = pipeline.Pipeline(batch_size=1, num_threads=1, device_id=0)

    with pipe:
        # file_root aponta para o diretório PAI (não a subdir)
        images, labels = fn.readers.file(
          file_root=local_cache_dir
          #file_root='s3://noaa-auv/main/NOAA-AUV/VIOLA/6000713538/'
        )
        images = fn.decoders.image(images, device="mixed")
        pipe.set_outputs(images, labels)

    pipe.build()
    outputs = pipe.run()

    print(f"✓ Imagem processada: {outputs[0].shape()}")
    print(f"✓ Label: {outputs[1]}")
    return outputs[0]

if __name__ == "__main__":
    result = read_s3_with_dali(
        bucket='noaa-auv',
        key='main/NOAA-AUV/VIOLA/6000713538/FT_20241016_021430_0_BC0030VB0153.jpg'
    )
