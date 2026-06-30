from tkinter import Tk, Label
from PIL import Image, ImageTk
import os
import glob

IMAGE_DIR = "/mnt/AWS/projeto-ia-submarina/ia-frente-ambiental/NOAA-AUV/VIOLA/6000713538"
#IMAGE_DIR = './images'

## supported extensions
#patterns = ["*.jpg", "*.jpeg", "*.png", "*.webp"]
#
#images = []
#for p in patterns:
#    images.extend(glob.glob(os.path.join(IMAGE_DIR, p)))
#
#images.sort()

with open("images.txt") as f:
    images = [line.strip() for line in f if line.strip()]

index = 0

root = Tk()
root.title("Image sorter")

label = Label(root)
label.pack()

def save(name, file):
    with open(file, "a") as f:
        f.write(name + "\n")

def show_image():
    global index

    if index >= len(images):
        print("Done")
        root.quit()
        return

    path = images[index]

    img = Image.open(path)

    # resize for screen
    img.thumbnail((1200, 900))

    tk_img = ImageTk.PhotoImage(img)

    label.config(image=tk_img)
    label.image = tk_img

    root.title(f"{index+1}/{len(images)} - {os.path.basename(path)}")

def next_image():
    global index
    index += 1
    show_image()

def right(event):
    path = images[index]
    save(os.path.basename(path), "right.txt")
    next_image()

def left(event):
    path = images[index]
    save(os.path.basename(path), "left.txt")
    next_image()

def skip(event):
    next_image()


def main():
  root.bind("<Right>", right)
  root.bind("<Left>", left)
  root.bind("<Up>", skip)

  show_image()
  root.mainloop()


if __name__ == "__main__":
    main()
