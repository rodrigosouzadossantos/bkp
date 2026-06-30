import os

import boto3
from botocore.exceptions import NoCredentialsError
from dotenv import load_dotenv

load_dotenv()
ACCESS_KEY = os.getenv('aws_access_key_id_30_prd')
SECRET_KEY = os.getenv('aws_secret_access_key_30_prd')

s3_client = boto3.client(
    's3',
    aws_access_key_id=ACCESS_KEY,
    aws_secret_access_key=SECRET_KEY
)


def upload_files(directory, bucket_name, s3_base_path):
    """
    Função para fazer upload de arquivos de um diretório para um bucket S3.

    :param directory: Caminho do diretório base que contém os arquivos
    :param bucket_name: Nome do bucket S3 para onde os arquivos serão enviados
    :param s3_base_path: Caminho base dentro do bucket S3 onde os arquivos serão armazenados
    """
    for root, dirs, files in os.walk(directory):
        for file in files:
            file_path = os.path.join(root, file)
            relative_path = os.path.relpath(file_path, directory).replace("\\", "/")
            s3_key = os.path.join(s3_base_path, relative_path).replace("\\", "/")
            try:
                s3_client.upload_file(file_path, bucket_name, s3_key)
                print(f'File {file_path} uploaded as {s3_key}')
            except FileNotFoundError:
                print(f'The file {file_path} was not found')
            except NoCredentialsError:
                print('Credentials not available')


if __name__ == "__main__":
    bucket_name = 'analise-dados'
    s3_base_path = 'projeto-ia-submarina/ia-frente-ambiental/GroundTruth'

    directories = [
        'CSV-Versions',
        'Prediction-Versions'
    ]

    for directory in directories:
        upload_files(directory, bucket_name, s3_base_path)
