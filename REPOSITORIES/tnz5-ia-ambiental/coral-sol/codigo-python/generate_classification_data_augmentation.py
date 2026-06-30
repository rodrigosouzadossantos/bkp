import os

from tensorflow.keras.preprocessing.image import ImageDataGenerator
from tensorflow.keras.preprocessing.image import img_to_array, load_img

positive_dir = 'Dataset-Class\\positivo'
augmented_dir = 'Dataset-Class\\positivo_aumentado'
os.makedirs(augmented_dir, exist_ok=True)
datagen = ImageDataGenerator(
    rotation_range=40,
    horizontal_flip=True,
    brightness_range=[0.8, 1.2],
    fill_mode='nearest'
)

if __name__ == '__main__':

    for filename in os.listdir(positive_dir):
        if filename.endswith('.jpg') or filename.endswith('.png'):
            image_path = os.path.join(positive_dir, filename)
            image = load_img(image_path)
            x = img_to_array(image)
            x = x.reshape((1,) + x.shape)

            i = 0
            for batch in datagen.flow(x, batch_size=1,
                                      save_to_dir=augmented_dir,
                                      save_prefix=filename[:-4],
                                      save_format='png'):
                i += 1
                if i >= 3:
                    break
