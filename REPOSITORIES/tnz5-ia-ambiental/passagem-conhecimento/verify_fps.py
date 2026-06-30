import os
import sys
import cv2

if len(sys.argv) < 2:
    print('Informe o caminho da pasta como argumento.')
    exit()

folder_path = sys.argv[1]
video_files = [f for f in os.listdir(folder_path) if f.lower().endswith(('.mp4', '.avi', '.mov', '.mkv'))]
if not video_files:
    print('Nenhum vídeo encontrado.')
    exit()
video_path = os.path.join(folder_path, video_files[0])
cap = cv2.VideoCapture(video_path)
fps = int(cap.get(cv2.CAP_PROP_FPS))
cap.release()
print(f'FPS do vídeo: {fps}')
print(f'FPS recomendado (a cada 3 segundos): {fps * 3}')