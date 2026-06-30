import boto3
import os
import nvidia.dali.pipeline as pipeline
import nvidia.dali.fn as fn

os.environ['CURL_CA_BUNDLE'] = ''

def read_s3_with_dali(bucket, key, local_cache_dir="./cache"):
    """Lê imagem de S3 com estrutura que DALI espera"""
    
    s3_client = boto3.client('s3')
    
    # Criar estrutura: cache/class_0/image.jpg
    # DALI espera: file_root/class_name/files
    class_dir = os.path.join(local_cache_dir, "images")
    os.makedirs(class_dir, exist_ok=True)
    
    # Baixar arquivo
    filename = os.path.basename(key)
    filepath = os.path.join(class_dir, filename)
    
    data = s3_client.get_object(Bucket=bucket, Key=key)
    with open(filepath, 'wb') as f:
        f.write(data['Body'].read())
    
    print(f"✓ Arquivo baixado: {filepath}")
    print(f"✓ Diretório cache: {local_cache_dir}")
    print(f"✓ Arquivos em cache/images: {os.listdir(class_dir)}")
    
    # Pipeline com DALI
    pipe = pipeline.Pipeline(batch_size=1, num_threads=1, device_id=0)
    
    with pipe:
        # file_root aponta para ./cache (pai das subpastas)
        images, labels = fn.readers.file(
            file_root=local_cache_dir,
            random_shuffle=False
        )
        images = fn.decoders.image(images, device="mixed")
        pipe.set_outputs(images, labels)
    
    pipe.build()
    outputs = pipe.run()
    
    print(f"✓ Imagem processada com DALI!")
    print(f"✓ Shape: {outputs[0].shape()}")
    print(f"✓ Label: {outputs[1]}")
    return outputs[0]

if __name__ == "__main__":
    result = read_s3_with_dali(
        bucket='analise-dados',
        key='projeto-ia-submarina/ia-frente-ambiental/NOAA-AUV/VIOLA/6000713538/FT_20241016_021430_0_BC0030VB0153.jpg'
    )

