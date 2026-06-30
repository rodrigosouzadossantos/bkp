import geopandas as gpd
import pandas as pd
from tqdm import tqdm
import os

# =========================
# CONFIG
# =========================
SHP_PATH = "/tmp/class_esp/CLASS_ESP_MODEL_IA.shp"
LIST_PATH = "espadarte.list"

OUT_MANIFEST = "training_manifest.csv"
OUT_GPKG = "ESPADARTE_CLEAN.gpkg"

# =========================
# 1. LOAD SHAPEFILE
# =========================
print("Loading shapefile...")
gdf = gpd.read_file(SHP_PATH)

gdf["NOME_FOTO"] = gdf["NOME_FOTO"].astype(str).str.strip()

# =========================
# 2. LOAD IMAGE LIST
# =========================
print("Loading image index...")

mapping = {}
all_images = set()

with open(LIST_PATH) as f:
    for line in f:
        path = line.strip()
        fname = os.path.basename(path).strip()
        mapping[fname] = path
        all_images.add(fname)

# =========================
# 3. AUDIT DATASET
# =========================
print("\n=== DATASET AUDIT ===")

shp_images = set(gdf["NOME_FOTO"].unique())

missing_in_list = shp_images - all_images
extra_in_list = all_images - shp_images
matched = shp_images & all_images

with open("matched.txt", "w", encoding="utf-8") as f:
    for item in sorted(matched):
        f.write(f"{item}\n")

print("SHP unique images      :", len(shp_images))
print("LIST unique images     :", len(all_images))
print("MATCHED                :", len(matched))
print("MISSING in list        :", len(missing_in_list))
print("UNUSED in list         :", len(extra_in_list))

print("\nCoverage:", round(len(matched) / len(shp_images), 4))

print("\nExample missing files:")
print(list(missing_in_list)[:10])

# =========================
# 4. RESOLVE PATHS
# =========================
def resolve_path(name):
    name = str(name).strip()
    return mapping.get(name)

gdf["IMG_PATH"] = gdf["NOME_FOTO"].apply(resolve_path)

# =========================
# 5. CLEAN DATASET
# =========================
clean_gdf = gdf.dropna(subset=["IMG_PATH"]).copy()

print("\n=== CLEANING REPORT ===")
print("Original rows :", len(gdf))
print("Clean rows    :", len(clean_gdf))
print("Removed       :", len(gdf) - len(clean_gdf))

# =========================
# 6. SAVE CLEAN GEODATASET
# =========================
print("\nSaving clean GeoPackage...")
clean_gdf.to_file(OUT_GPKG, driver="GPKG")

# =========================
# 7. BUILD ML MANIFEST
# =========================
manifest = clean_gdf[[
    "IMG_PATH",
    "NOME_FOTO",
    "UTM_E",
    "UTM_N",
    "TIPO_HABIT"
]].copy()

manifest.to_csv(OUT_MANIFEST, index=False)

print("\nSaved manifest:", OUT_MANIFEST)

# =========================
# 8. CLASS DISTRIBUTION
# =========================
print("\n=== CLASS DISTRIBUTION ===")
print(clean_gdf["TIPO_HABIT"].value_counts().head(20))

# =========================
# 9. IMAGE USAGE STATS
# =========================
print("\n=== IMAGE USAGE ===")
print(clean_gdf["NOME_FOTO"].value_counts().head(20))
