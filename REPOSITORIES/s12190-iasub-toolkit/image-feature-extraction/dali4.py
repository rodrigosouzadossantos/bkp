import boto3
import os
import nvidia.dali.pipeline as pipeline
import nvidia.dali.fn as fn

os.environ['CURL_CA_BUNDLE'] = ''

def read_s3_with_dali_filelist(bucket, key, local_cache_dir="./cache"):
    """Usa arquivo de lista com caminhos"""

    s3_client = boto3.client('s3')
    os.makedirs(local_cache_dir, exist_ok=True)

    # Baixar arquivo
    filename = os.path.basename(key)
    filepath = os.path.join(local_cache_dir, filename)

    data = s3_client.get_object(Bucket=bucket, Key=key)
    with open(filepath, 'wb') as f:
        f.write(data['Body'].read())

    print(f"✓ Arquivo baixado: {filepath}")

    # Criar arquivo de lista
    filelist_path = os.path.join(local_cache_dir, "filelist.txt")
    abs_filepath = os.path.abspath(filepath)

    with open(filelist_path, 'w') as f:
        f.write(f"{abs_filepath} 0\n")  # formato: caminho label

    print(f"✓ Lista criada: {filelist_path}")

    # Pipeline com file_list
    pipe = pipeline.Pipeline(batch_size=1, num_threads=1, device_id=0)

    with pipe:
        images, labels = fn.readers.file(file_list=filelist_path)
        images = fn.decoders.image(images, device="mixed")
        pipe.set_outputs(images, labels)

    pipe.build()
    outputs = pipe.run()

    print(f"✓ Imagem processada: {outputs[0].shape()}")
    return outputs[0]

if __name__ == "__main__":
    result = read_s3_with_dali_filelist(
        bucket='analise-dados',
        key='projeto-ia-submarina/ia-frente-ambiental/NOAA-AUV/VIOLA/6000713538/FT_20241016_021430_0_BC0030VB0153.jpg'
    )

