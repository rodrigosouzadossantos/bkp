from nvidia.dali.pipeline import pipeline_def
import nvidia.dali.fn as fn
import nvidia.dali.types as types
import boto3
import os
from tempfile import TemporaryDirectory

# Configurar credenciais
os.environ['AWS_PROFILE'] = 'lakefs'
os.environ['AWS_REGION'] = 'sa-east-1'
os.environ['AWS_ENDPOINT_URL_S3'] = 'http://localhost:8000'

def download_s3_file(bucket, key, local_path):
    """Baixa arquivo de S3 para caminho local"""
    s3_client = boto3.client(
        's3',
        region_name=os.environ['AWS_REGION'],
        endpoint_url=os.environ['AWS_ENDPOINT_URL_S3']
    )
    s3_client.download_file(bucket, key, local_path)

@pipeline_def
def s3_pipeline(data_dir):
    # Usar caminho local (arquivo já baixado)
    jpegs, labels = fn.readers.file(
        file_root=data_dir,
        random_shuffle=True,
        name="Reader",
    )
    images = fn.decoders.image(jpegs, device="mixed")
    return images

def run_test():
    try:
        # 1. Baixar arquivo do S3 para local temp
        with TemporaryDirectory() as tmpdir:
            local_file = os.path.join(tmpdir, "image.jpg")
            
            download_s3_file(
                bucket="analise-dados",
                key='projeto-ia-submarina/ia-frente-ambiental/NOAA-AUV/VIOLA/6000713538/FT_20241016_050342_0_BC0030VB0153.jpg', #"main/NOAA-AUV/VIOLA/6000713538/FT_20241016_021430_0_BC0030VB0153.jpg",
                local_path=local_file
            )
            
            # 2. Executar pipeline com arquivo local
            pipe = s3_pipeline(data_dir=local_file, batch_size=32, num_threads=2, device_id=0)
            pipe.build()
            outputs = pipe.run()
            
            print("DALI Test Success!")
            
    except Exception as e:
        print(f"DALI Test Failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    run_test()

