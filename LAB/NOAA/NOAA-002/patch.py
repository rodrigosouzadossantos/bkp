import geopandas as gpd
import rasterio
from rasterio.windows import Window
from rasterio.transform import rowcol
from PIL import Image
import os
from tqdm import tqdm


def clean_label(label):
    return "-".join(
        str(label)
        .strip()
        .upper()
        .split()
    )


gdf = gpd.read_file("/tmp/class_esp/CLASS_ESP_MODEL_IA.shp")

mapping = {}
with open("espadarte.list") as f:
    for line in f:
        path = line.strip()
        mapping[path.split("/")[-1]] = path

OUT_DIR = "patches"
os.makedirs(OUT_DIR, exist_ok=True)

PATCH_SIZE = 256
PAD = PATCH_SIZE // 2

for i, row in tqdm(gdf.iterrows(), total=len(gdf)):

    img_name = row["NOME_FOTO"]
    img_path = mapping.get(str(img_name).strip())
    label = clean_label(row["TIPO_HABIT"])

    if img_path is None:
        continue

    try:
        with rasterio.open(img_path) as src:

            r, c = rowcol(
                src.transform,
                row["UTM_E"],
                row["UTM_N"]
            )

            window = Window(
                c - PAD,
                r - PAD,
                PATCH_SIZE,
                PATCH_SIZE
            )

            patch = src.read(window=window, boundless=True, fill_value=0)

            patch = patch.transpose(1, 2, 0)

            if patch.shape[2] == 1:
                patch = patch[:, :, 0]

            img = Image.fromarray(patch.astype("uint8"))

            out_name = f"{i}_{label}.png"
            img.save(os.path.join(OUT_DIR, out_name))

    except Exception as e:
        print("error:", img_name, e)
