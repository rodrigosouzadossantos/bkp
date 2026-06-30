from tkinter import Tk, Label
from PIL import Image, ImageTk
import os

IMAGE_LIST = "images.txt"
CHECKPOINT = "checkpoint.txt"

RIGHT_FILE = "right.txt"
LEFT_FILE = "left.txt"

# ----------------------------
# load images
# ----------------------------

with open(IMAGE_LIST) as f:
    images = [line.strip() for line in f if line.strip()]

# ----------------------------
# restore checkpoint
# ----------------------------

index = 0

if os.path.exists(CHECKPOINT):
    with open(CHECKPOINT) as f:
        try:
            index = int(f.read().strip())
        except:
            index = 0

# history of actions for undo
history = []

# ----------------------------
# ui
# ----------------------------

root = Tk()

label = Label(root)
label.pack()

# ----------------------------
# helpers
# ----------------------------

def save_checkpoint():
    with open(CHECKPOINT, "w") as f:
        f.write(str(index))

def append_line(file, text):
    with open(file, "a") as f:
        f.write(text + "\n")

def remove_last_line(file):
    if not os.path.exists(file):
        return

    with open(file, "r") as f:
        lines = f.readlines()

    if lines:
        lines = lines[:-1]

    with open(file, "w") as f:
        f.writelines(lines)

def current_image():
    return images[index]

# ----------------------------
# image display
# ----------------------------

def show_image():
    global index

    if index < 0:
        index = 0

    if index >= len(images):
        print("DONE")

        if os.path.exists(CHECKPOINT):
            os.remove(CHECKPOINT)

        root.quit()
        return

    path = current_image()

    try:
        img = Image.open(path)
    except Exception as e:
        print("Failed:", path, e)
        next_image()
        return

    img.thumbnail((1400, 1000))

    tk_img = ImageTk.PhotoImage(img)

    label.config(image=tk_img)
    label.image = tk_img

    root.title(
        f"{index+1}/{len(images)} : {os.path.basename(path)}"
    )

# ----------------------------
# navigation
# ----------------------------

def next_image():
    global index
    index += 1
    save_checkpoint()
    show_image()

# ----------------------------
# actions
# ----------------------------

def mark_right(event):
    path = current_image()

    append_line(RIGHT_FILE, path)

    history.append((index, RIGHT_FILE))

    next_image()

def mark_left(event):
    path = current_image()

    append_line(LEFT_FILE, path)

    history.append((index, LEFT_FILE))

    next_image()

def skip(event):
    history.append((index, None))
    next_image()

# ----------------------------
# undo
# ----------------------------

def undo(event):
    global index

    if not history:
        return

    prev_index, file = history.pop()

    # remove last saved mark
    if file is not None:
        remove_last_line(file)

    index = prev_index

    save_checkpoint()
    show_image()

# ----------------------------
# quit
# ----------------------------

def quit_app(event):
    save_checkpoint()
    print(f"Checkpoint saved at image {index}")
    root.quit()

# ----------------------------
# keys
# ----------------------------

root.bind("<Right>", mark_right)
root.bind("<Left>", mark_left)

# skip
root.bind("<Up>", skip)

# undo/back
root.bind("<Down>", undo)

# quit safely
root.bind("q", quit_app)

# ----------------------------

show_image()

root.mainloop()
