import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.ticker import ScalarFormatter
import argparse

def parse_scores(scores_str):
    scores_str = str(scores_str).strip("[]").replace(" ", "")
    if not scores_str:
        return np.array([])
    parts = [s for s in scores_str.split(",") if s]
    if not parts or all([p == "" for p in parts]):
        return np.array([])
    return np.array([float(x) for x in parts])

def remove_outliers(df):
    Q1 = df[["north", "east"]].quantile(0.25)
    Q3 = df[["north", "east"]].quantile(0.75)
    IQR = Q3 - Q1
    mask = ~(
        (df["north"] < (Q1["north"] - 1.5 * IQR["north"]))
        | (df["north"] > (Q3["north"] + 1.5 * IQR["north"]))
        | (df["east"] < (Q1["east"] - 1.5 * IQR["east"]))
        | (df["east"] > (Q3["east"] + 1.5 * IQR["east"]))
    )
    return df[mask].reset_index(drop=True)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv_path", type=str, required=True)
    parser.add_argument("--output_file", type=str, required=True)
    args = parser.parse_args()

    df = pd.read_csv(args.csv_path)
    df = df[df["north"].notnull() & df["east"].notnull()]
    df = remove_outliers(df)
    df["has_coral"] = df["scores_list"].apply(lambda x: np.any(parse_scores(x) > 0.5))

    fig, ax = plt.subplots(figsize=(14, 8), facecolor="white")
    ax.scatter(df["east"], df["north"], color="blue", s=8, label="Pontos")
    ax.plot(
        df["east"],
        df["north"],
        color="black",
        linewidth=0.8,
        alpha=0.2,
        label="Trajetória",
    )

    ax.scatter(
        df.iloc[0]["east"],
        df.iloc[0]["north"],
        color="green",
        s=80,
        marker="o",
        label="Start",
        zorder=5,
    )
    ax.scatter(
        df.iloc[-1]["east"],
        df.iloc[-1]["north"],
        color="red",
        s=80,
        marker="X",
        label="End",
        zorder=5,
    )
    ax.scatter(
        df[df["has_coral"]]["east"],
        df[df["has_coral"]]["north"],
        color="gold",
        s=180,
        marker="*",
        label="Coral (>0.5)",
        edgecolor="black",
        linewidth=1.5,
        zorder=10,
    )

    x_min, x_max = df["east"].min(), df["east"].max()
    y_min, y_max = df["north"].min(), df["north"].max()
    x_pad = (x_max - x_min) * 0.45
    y_pad = (y_max - y_min) * 0.45
    ax.set_xlim(x_min - x_pad, x_max + x_pad)
    ax.set_ylim(y_min - y_pad, y_max + y_pad)
    ax.grid(True, which="both", linestyle="--", linewidth=0.5, color="gray")
    ax.set_facecolor("white")
    ax.set_xlabel("East (m)")
    ax.set_ylabel("North (m)")
    ax.set_title("Mapa da Operação + Presença de Coral-Sol")
    ax.legend()

    x_formatter = ScalarFormatter(useMathText=False)
    x_formatter.set_scientific(False)
    x_formatter.set_useOffset(False)
    ax.xaxis.set_major_formatter(x_formatter)

    y_formatter = ScalarFormatter(useMathText=False)
    y_formatter.set_scientific(False)
    y_formatter.set_useOffset(False)
    ax.yaxis.set_major_formatter(y_formatter)

    ax.ticklabel_format(style="plain", axis="both")
    plt.tight_layout()
    plt.savefig(args.output_file, dpi=300)