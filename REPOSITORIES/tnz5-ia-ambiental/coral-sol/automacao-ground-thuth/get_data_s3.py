import os
import string
from datetime import datetime

import boto3
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
ACCESS_KEY = os.getenv('aws_access_key_id')
SECRET_KEY = os.getenv('aws_secret_access_key')
SESSION_TOKEN = os.getenv('aws_session_token')

# Initialize S3 client with credentials
s3_client = boto3.client(
    's3',
    aws_access_key_id=ACCESS_KEY,
    aws_secret_access_key=SECRET_KEY,
    aws_session_token=SESSION_TOKEN,
)


def sanitize_filename(filename: str) -> str:
    """
    Sanitizes a filename by replacing invalid characters with underscores.

    Args:
        filename (str): The original filename.

    Returns:
        str: The sanitized filename with invalid characters replaced by underscores.
    """
    valid_chars = f"-_.() {string.ascii_letters}{string.digits}"
    sanitized_filename = ''.join(c if c in valid_chars else '_' for c in filename)
    return sanitized_filename


def create_directory(path: str) -> None:
    """
    Creates a directory if it does not already exist.

    Args:
        path (str): The path of the directory to create.

    Returns:
        None
    """
    try:
        if not os.path.exists(path):
            os.makedirs(path, exist_ok=True)
            print(f'Directory created: {path}')
    except PermissionError as e:
        print(f'Permission denied while trying to create {path}: {e}')
    except Exception as e:
        print(f'Error creating directory {path}: {e}')


def download_objects(bucket_name: str, prefix: str, download_path: str) -> None:
    """
    Downloads objects from an S3 bucket to a local directory.

    Args:
        bucket_name (str): The name of the S3 bucket.
        prefix (str): The prefix path in the S3 bucket to download.
        download_path (str): The local directory to save the downloaded objects.

    Returns:
        None
    """
    paginator = s3_client.get_paginator('list_objects_v2')
    response_iterator = paginator.paginate(Bucket=bucket_name, Prefix=prefix)

    for response in response_iterator:
        if 'Contents' in response:
            for obj in response['Contents']:
                key = obj['Key']
                relative_path = os.path.relpath(key, prefix)
                sanitized_relative_path = os.path.join(
                    os.path.dirname(relative_path),
                    sanitize_filename(os.path.basename(relative_path))
                )
                download_file_path = os.path.join(download_path, sanitized_relative_path)

                print(f'Downloading {key} to {download_file_path}')

                try:
                    dir_path = os.path.dirname(download_file_path)
                    if not os.path.exists(dir_path):
                        os.makedirs(dir_path, exist_ok=True)
                        print(f'Directory created: {dir_path}')
                    s3_client.download_file(bucket_name, key, download_file_path)
                    print(f'Downloaded: {key}')
                except PermissionError as e:
                    print(f'Permission denied while trying to create {download_file_path}: {e}')
                except Exception as e:
                    print(f'Error downloading {key}: {e}')
        else:
            print("No contents found in the specified prefix")


def process_input_bucket(bucket_name: str, prefix: str, base_dir: str) -> None:
    """
    Processes an input S3 bucket by downloading its contents into a specified local directory,
    only if the directory does not already exist.

    Args:
        bucket_name (str): The name of the S3 bucket.
        prefix (str): The prefix path in the S3 bucket.
        base_dir (str): The base directory to save the downloaded objects.

    Returns:
        None
    """
    if not os.path.exists(base_dir):
        create_directory(base_dir)
        download_objects(bucket_name, prefix, base_dir)
    else:
        print(f"Directory {base_dir} already exists. Skipping download.")


def process_output_bucket(bucket_name: str, prefix: str, base_dir: str) -> None:
    """
    Processes an output S3 bucket by downloading its contents into a date-versioned local directory.

    Args:
        bucket_name (str): The name of the S3 bucket.
        prefix (str): The prefix path in the S3 bucket.
        base_dir (str): The base directory to save the downloaded objects.

    Returns:
        None
    """
    today_date = datetime.today().strftime('%Y-%m-%d')
    download_path = os.path.join(base_dir, today_date)
    create_directory(download_path)
    download_objects(bucket_name, prefix, download_path)


if __name__ == '__main__':
    output_bucket_name = 's3-dsm-groundtruth-output-637423571944-us-east-1'
    input_bucket_name = 's3-dsm-groundtruth-input-637423571944-us-east-1'
    prefix_output = 'imagens-lote-4-5/rotulacao-lotes-4-5'
    prefix_input = 'imagens-lote-4-5'

    input_base_dir = os.path.join("Bucket-Input-Versions", prefix_input)
    process_input_bucket(input_bucket_name, prefix_input, input_base_dir)

    output_base_dir = os.path.join("Bucket-Output-Versions", prefix_output.split("/")[0])
    process_output_bucket(output_bucket_name, prefix_output, output_base_dir)