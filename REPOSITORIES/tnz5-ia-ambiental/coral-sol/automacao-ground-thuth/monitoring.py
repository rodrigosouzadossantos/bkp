import glob
import json
import os
from datetime import datetime
from typing import Optional

import pandas as pd


def get_annotated_image_path(json_path: str, download_path: str) -> Optional[str]:
    """
    Retrieves the path of the annotated image corresponding to the given JSON path.

    Args:
        json_path (str): The path to the JSON file.
        download_path (str): The base download path where images are stored.

    Returns:
        Optional[str]: The path to the annotated image if found, otherwise None.
    """
    subfolder = json_path.split("\\")[-2]
    annotation_files = glob.glob(
        os.path.join(download_path, "annotations", "consolidated-annotation", "output", "*.png")
    )

    for image_file in annotation_files:
        image_id = image_file.split("\\")[-1].split("_")[0]
        if image_id == subfolder:
            return image_file
    return None


def get_worker(data: dict) -> str:
    """
    Retrieves the worker name based on the worker's identity data.

    Args:
        data (dict): The JSON data containing worker information.

    Returns:
        str: The name of the worker if found, otherwise "Unknown".
    """
    workers = {
        "e4f814b8-4061-706d-5d2c-b354c59a5936": "Pedro",
        "4458b4d8-4071-7022-9dad-7c31f202f1ff": "Walace",
        "f4f80408-8031-704c-0441-40af03aea9ad": "Suzane",
        "f498c458-c0d1-7011-35f2-b0ec0e0475ed": "Lucca",
        "2488f468-d0a1-7051-e21a-f864016ac21e": "Geronimo",
        "9448e4b8-2071-703f-7ca8-9011224bb46b": "Andrea",
        "c408a408-a0f1-700f-9de0-9a353ca2c50d": "Fransisco",
        "74a8d4e8-4011-70cc-b2cb-bdc77caab284": "Viviane"
    }
    sub = data["answers"][0]["workerMetadata"]["identityData"]["sub"]
    return workers.get(sub, "Unknown")


def generate_csv(download_path: str, save_path: str) -> None:
    """
    Generates a CSV file from JSON files in the specified download path.

    Args:
        download_path (str): The base path where JSON files are stored.
        save_path (str): The path where the generated CSV file will be saved.

    Returns:
        None
    """
    df = pd.DataFrame(columns=[
        "workerName", "acceptanceTime", "submissionTime",
        "timeSpentInSeconds", "annotated_image_path"
    ])

    json_files = glob.glob(os.path.join(download_path, "annotations", "worker-response", "**", "**", "*.json"))

    for filename in json_files:
        with open(filename, 'r') as file:
            data = json.load(file)

            new_row = {
                "workerName": get_worker(data),
                "acceptanceTime": data["answers"][0].get("acceptanceTime", ""),
                "submissionTime": data["answers"][0].get("submissionTime", ""),
                "timeSpentInSeconds": data["answers"][0].get("timeSpentInSeconds", 0),
                "annotated_image_path": get_annotated_image_path(filename, download_path) or "",
            }

            df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)

    timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    csv_filename = os.path.join(save_path, f"worker_responses_{timestamp}.csv")

    df.to_csv(csv_filename, index=False, encoding="utf-8")
    print(f"CSV file '{csv_filename}' has been saved successfully.")


if __name__ == '__main__':
    prefix = 'imagens-lote-4-5/rotulacao-lotes-4-5'

    today_date = datetime.today().strftime('%Y-%m-%d')
    folder_data = os.path.join("Bucket-Output-Versions", prefix.split("/")[0], today_date)
    folder_save = os.path.join("CSV-Versions", prefix.split("/")[0], today_date)

    os.makedirs(folder_save, exist_ok=True)

    generate_csv(folder_data, folder_save)
