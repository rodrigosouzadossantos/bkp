import os
import hashlib
import shutil


def calculate_md5(file_path, chunk_size=4096):
    md5 = hashlib.md5()
    with open(file_path, 'rb') as f:
        while chunk := f.read(chunk_size):
            md5.update(chunk)
    return md5.hexdigest()


def move_duplicates(source_folder, destination_folder):
    if not os.path.exists(destination_folder):
        os.makedirs(destination_folder)

    seen_hashes = {}
    for root, dirs, files in os.walk(source_folder):
        for file_name in files:
            file_path = os.path.join(root, file_name)
            file_hash = calculate_md5(file_path)

            if file_hash in seen_hashes:
                duplicate_path = os.path.join(destination_folder, file_name)
                shutil.move(file_path, duplicate_path)
                # shutil.move(file_path.replace("jpg","json"), duplicate_path)

                print(f'Movendo duplicata: {file_path} -> {duplicate_path}')
            else:
                seen_hashes[file_hash] = file_path


# Substitua os caminhos das pastas aqui
source_folder = 'Segmentacao-Coral-1-Organizado'
destination_folder = 'Segmentacao-Coral-1-Duplicatas'

move_duplicates(source_folder, destination_folder)
