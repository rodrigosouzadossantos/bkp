import pandas as pd
import argparse
import numpy as np

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv_path", type=str, required=True)
    parser.add_argument("--output_file", type=str, required=True)
    args = parser.parse_args()

    df = pd.read_csv(args.csv_path)

    q1_north = df["north"].quantile(0.25)
    q3_north = df["north"].quantile(0.75)
    iqr_north = q3_north - q1_north
    lower_north = q1_north - 1.5 * iqr_north
    upper_north = q3_north + 1.5 * iqr_north

    q1_east = df["east"].quantile(0.25)
    q3_east = df["east"].quantile(0.75)
    iqr_east = q3_east - q1_east
    lower_east = q1_east - 1.5 * iqr_east
    upper_east = q3_east + 1.5 * iqr_east

    df = df[
        (df["north"] >= lower_north) & (df["north"] <= upper_north) &
        (df["east"] >= lower_east) & (df["east"] <= upper_east)
    ]

    df["Nome do vídeo"] = df["video"]
    df["Tempo do vídeo"] = df["time"]
    df["Coordenada North"] = df["north"].astype(int)
    df["Coordenada East"] = df["east"].astype(int)
    df["Descrição do evento"] = "Coral"

    def safe_eval(x):
        if isinstance(x, str) and x.strip().startswith("[") and x.strip().endswith("]"):
            try:
                l = eval(x, {"__builtins__": None, "np": np}, {})
                return [float(i) for i in l]
            except Exception:
                return []
        return []

    def format_percent(l):
        if not isinstance(l, list) or len(l) == 0:
            return ""
        return ", ".join([f"{v*100:.2f}%" for v in l])

    df["Scores do modelo"] = df["scores_list"].apply(safe_eval).apply(format_percent)
    df = df[df["Scores do modelo"].apply(lambda x: len(x) > 0)]

    tabela = df[
        [
            "Nome do vídeo",
            "Tempo do vídeo",
            "Coordenada North",
            "Coordenada East",
            "Descrição do evento",
            "Scores do modelo",
        ]
    ]
    tabela.to_csv(args.output_file, index=False)