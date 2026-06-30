import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import argparse
import os

def safe_eval(x):
    if isinstance(x, str) and x.strip().startswith("[") and x.strip().endswith("]"):
        try:
            l = eval(x, {"__builtins__": None, "np": np}, {})
            return [float(i) for i in l]
        except Exception:
            return []
    return []

def plot_confidence(csv_path, threshold, space, label_interval, ma_window, output_dir):
    df = pd.read_csv(csv_path)
    df["time"] = pd.to_datetime(df["time"], format="%M:%S")
    df["scores_list"] = df["scores_list"].apply(safe_eval)
    df["confidence"] = df["scores_list"].apply(lambda x: x[0] if x else None)
    videos = df["video"].unique()
    x_ticks = []
    x_labels = []
    x_pos = 0
    x_indexes = []
    video_names = []

    for v in videos:
        video_df = df[df["video"] == v]
        n = len(video_df)
        indexes = list(range(x_pos, x_pos + n))
        x_indexes.extend(indexes)
        for i, t in enumerate(video_df["time"].dt.strftime("%H:%M:%S").tolist()):
            if i % label_interval == 0:
                x_ticks.append(x_pos + i)
                x_labels.append(t)
        video_names.append((x_pos + n // 2, v))
        x_pos += n
        x_indexes.extend([x_pos + i for i in range(space)])
        x_pos += space

    confidence_values = []
    confidence_ma_values = []
    for v in videos:
        video_df = df[df["video"] == v]
        confidence_values.extend([c * 100 if c is not None else np.nan for c in video_df["confidence"].tolist()])
        confidence_ma_values.extend([c * 100 if c is not None else np.nan for c in video_df["confidence"].rolling(window=ma_window, min_periods=1).mean().tolist()])
        confidence_values.extend([np.nan] * space)
        confidence_ma_values.extend([np.nan] * space)

    os.makedirs(output_dir, exist_ok=True)

    plt.figure(figsize=(12, 5))
    plt.plot(x_indexes, [threshold * 100] * len(x_indexes), label="Linha de corte", linestyle="--", color="orange")
    plt.plot(x_indexes, confidence_values, label="Confiança", marker="o", color="orange")
    plt.ylim(0.0, 100.0)
    plt.xlabel("Tempo do vídeo")
    plt.ylabel("Confiança (%)")
    plt.xticks(x_ticks, x_labels, rotation=90, fontsize=8)
    for pos, name in video_names:
        plt.text(pos, 103, name, ha="center", va="bottom", fontsize=9, color="orange")
    plt.legend()
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, "grafico_confiança.png"))
    plt.close()

    plt.figure(figsize=(12, 5))
    plt.plot(x_indexes, [threshold * 100] * len(x_indexes), label="Linha de corte", linestyle="--", color="orange")
    plt.plot(x_indexes, confidence_ma_values, label=f"Confiança atenuada pela média móvel (janela={ma_window})", marker="o", color="orange")
    plt.ylim(0.0, 100.0)
    plt.xlabel("Tempo do vídeo")
    plt.ylabel("Confiança (%)")
    plt.xticks(x_ticks, x_labels, rotation=90, fontsize=8)
    for pos, name in video_names:
        plt.text(pos, 103, name, ha="center", va="bottom", fontsize=9, color="orange")
    plt.legend()
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, "grafico_media_movel.png"))
    plt.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv_path", type=str, required=True)
    parser.add_argument("--threshold", type=float, default=0.5)
    parser.add_argument("--space", type=int, default=5)
    parser.add_argument("--label_interval", type=int, default=30)
    parser.add_argument("--ma_window", type=int, default=5)
    parser.add_argument("--output_dir", type=str, required=True)
    args = parser.parse_args()
    plot_confidence(args.csv_path, args.threshold, args.space, args.label_interval, args.ma_window, args.output_dir)