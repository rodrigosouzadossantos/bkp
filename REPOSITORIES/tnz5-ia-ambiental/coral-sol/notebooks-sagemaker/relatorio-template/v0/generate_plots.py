import os
import cv2
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import argparse

def parse_scores(scores_str):
    scores_str = str(scores_str).strip("[]").replace(" ", "")
    if not scores_str:
        return np.array([])
    parts = [s for s in scores_str.split(",") if s]
    if not parts or all([p == '' for p in parts]):
        return np.array([])
    return np.array([float(x) for x in parts])

def save_plot(original_img, combined_mask, scores, video_name, col_timestamp, output_dir):
    if np.any(scores > 0.5):
        img_contour = original_img.copy()
        for idx, score in enumerate(scores):
            if score > 0.5:
                mask = (combined_mask == (idx + 1)).astype(np.uint8) * 255
                contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                for contour in contours:
                    if len(contour) >= 3:
                        cv2.drawContours(img_contour, [contour], -1, (255, 0, 255), 6)
                        M = cv2.moments(contour)
                        if M["m00"] != 0:
                            cX = int(M["m10"] / M["m00"])
                            cY = int(M["m01"] / M["m00"])
                        else:
                            cX, cY = contour[0][0]
                        prob_text = f"{score:.2f}"
                        cv2.putText(
                            img_contour, prob_text, (cX, cY), cv2.FONT_HERSHEY_SIMPLEX,
                            2, (255, 0, 255), 3, cv2.LINE_AA,
                        )
        plt.figure(figsize=(12, 6))
        plt.suptitle(
            f"Trecho do vídeo analisado: {video_name}\nTempo do vídeo: {col_timestamp}",
            fontsize=16, fontweight="bold", y=0.98,
        )
        ax1 = plt.subplot(1, 2, 1)
        ax1.imshow(original_img)
        ax1.set_title("Quadro original", fontsize=14, pad=8)
        ax1.axis("off")
        ax2 = plt.subplot(1, 2, 2)
        ax2.imshow(img_contour)
        ax2.set_title("Contorno feito pelo modelo de IA \n com confiança acima da linha de corte", fontsize=14, pad=8)
        ax2.axis("off")
        plt.subplots_adjust(top=0.92, bottom=0.01, left=0.01, right=0.99, wspace=0.04)
        os.makedirs(output_dir, exist_ok=True)
        plot_filename = (
            f"{video_name}_{col_timestamp.replace(':', '-').replace(' ', '_')}.png"
        )
        plt.savefig(os.path.join(output_dir, plot_filename), bbox_inches="tight")
        plt.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv_path", type=str, required=True)
    parser.add_argument("--output_dir", type=str, required=True)
    args = parser.parse_args()

    df = pd.read_csv(args.csv_path)
    for _, row in df.iterrows():
        frame = np.load(row["cropped_frame_path"])
        combined_mask = np.load(row["mask_path"])
        scores = parse_scores(row["scores_list"])
        save_plot(
            frame, combined_mask, scores, row["video"], row["time"], args.output_dir,
        )