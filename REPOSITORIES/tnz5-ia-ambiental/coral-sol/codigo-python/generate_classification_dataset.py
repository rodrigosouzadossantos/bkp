import os
import shutil
import csv
from sklearn.model_selection import train_test_split

# Diretórios base
augmented_positive_dir = 'Dataset-Class\\positivo_aumentado'
negative_dir = 'Dataset-Class\\negativo'
base_output_dir = 'Dataset-Classificacao-Patchs-V1'
train_dir = os.path.join(base_output_dir, 'train')
val_dir = os.path.join(base_output_dir, 'val')
test_dir = os.path.join(base_output_dir, 'test')

# Cria a estrutura de diretórios
os.makedirs(os.path.join(train_dir, 'positivo'), exist_ok=True)
os.makedirs(os.path.join(train_dir, 'negativo'), exist_ok=True)
os.makedirs(os.path.join(val_dir, 'positivo'), exist_ok=True)
os.makedirs(os.path.join(val_dir, 'negativo'), exist_ok=True)
os.makedirs(os.path.join(test_dir, 'positivo'), exist_ok=True)
os.makedirs(os.path.join(test_dir, 'negativo'), exist_ok=True)


def rename_files_and_save_csv(directory, output_csv):
    """
    Renomeia os arquivos em um diretório para nomes mais curtos, garantindo exclusividade.
    Salva um arquivo CSV com a correspondência entre nomes antigos e novos.

    Args:
    - directory (str): Caminho do diretório onde estão os arquivos a serem renomeados.
    - output_csv (str): Caminho do arquivo CSV onde será salva a correspondência.
    """
    file_mapping = []  # Lista para armazenar correspondências

    for i, filename in enumerate(os.listdir(directory)):
        if filename.endswith('.jpg') or filename.endswith('.png'):
            old_path = os.path.join(directory, filename)
            extension = '.png' if filename.endswith('.png') else '.jpg'
            new_name = f"image_{i}{extension}"
            new_path = os.path.join(directory, new_name)
            os.rename(old_path, new_path)  # Renomeia o arquivo
            file_mapping.append((filename, new_name))  # Salva a correspondência

    # Salva a correspondência em um arquivo CSV
    with open(output_csv, mode='w', newline='', encoding='utf-8') as csvfile:
        csvwriter = csv.writer(csvfile)
        csvwriter.writerow(['Nome Antigo', 'Nome Novo'])
        csvwriter.writerows(file_mapping)

    print(f"Arquivos renomeados e correspondência salva em {output_csv}")


def split_and_copy_files(file_list, source_dir, class_label):
    """
    Divide os arquivos em treino, validação e teste, e os copia para os diretórios correspondentes.

    Args:
    - file_list (list): Lista de arquivos.
    - source_dir (str): Diretório de origem dos arquivos.
    - class_label (str): Rótulo da classe ('positivo' ou 'negativo').
    """
    train_files, test_files = train_test_split(file_list, test_size=0.3, random_state=42)
    val_files, test_files = train_test_split(test_files, test_size=0.5, random_state=42)

    for file in train_files:
        dest_dir = os.path.join(train_dir, class_label)
        shutil.copy(os.path.join(source_dir, file), os.path.join(dest_dir, file))
    for file in val_files:
        dest_dir = os.path.join(val_dir, class_label)
        shutil.copy(os.path.join(source_dir, file), os.path.join(dest_dir, file))
    for file in test_files:
        dest_dir = os.path.join(test_dir, class_label)
        shutil.copy(os.path.join(source_dir, file), os.path.join(dest_dir, file))


if __name__ == '__main__':
    # Renomeia arquivos e salva mapeamento em CSV
    rename_files_and_save_csv(augmented_positive_dir, 'positive_file_mapping.csv')
    rename_files_and_save_csv(negative_dir, 'negative_file_mapping.csv')

    # Lista de arquivos renomeados
    positive_files = [f for f in os.listdir(augmented_positive_dir) if f.endswith('.jpg') or f.endswith('.png')]
    negative_files = [f for f in os.listdir(negative_dir) if f.endswith('.jpg') or f.endswith('.png')]

    # Verificação dos caminhos e arquivos
    print(f'Positive files: {len(positive_files)}')
    print(f'Negative files: {len(negative_files)}')

    # Divide os arquivos e copia para treino, validação e teste
    split_and_copy_files(positive_files, augmented_positive_dir, 'positivo')
    split_and_copy_files(negative_files, negative_dir, 'negativo')

    print("Renomeação e separação do dataset concluídas.")
