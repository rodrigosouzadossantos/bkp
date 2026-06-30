import geopandas as gpd
import pandas as pd
from tqdm import tqdm
import os

# =========================
# CONFIGURAÇÃO
# =========================
SHP_PATH = "/tmp/class_esp/CLASS_ESP_MODEL_IA.shp"
LIST_PATH = "espadarte.list"

OUT_MANIFEST = "training_manifest.csv"
OUT_GPKG = "ESPADARTE_CLEAN.gpkg"

# =========================
# 1. CARREGAR SHAPEFILE
# =========================
print("Carregando shapefile...")
gdf = gpd.read_file(SHP_PATH)

gdf["NOME_FOTO"] = gdf["NOME_FOTO"].astype(str).str.strip()

# =========================
# 2. CARREGAR LISTA DE IMAGENS
# =========================
print("Carregando índice de imagens...")

mapping = {}
all_images = set()

with open(LIST_PATH) as f:
    for line in f:
        path = line.strip()
        fname = os.path.basename(path).strip()
        mapping[fname] = path
        all_images.add(fname)

# =========================
# 3. AUDITORIA DO DATASET
# =========================
print("\n=== AUDITORIA DO DATASET ===")

shp_images = set(gdf["NOME_FOTO"].unique())

missing_in_list = shp_images - all_images
extra_in_list = all_images - shp_images
matched = shp_images & all_images

print("Imagens únicas no SHP   :", len(shp_images))
print("Imagens únicas na LISTA :", len(all_images))
print("CORRESPONDENTES         :", len(matched))
print("FALTANDO na lista       :", len(missing_in_list))
print("NÃO UTILIZADAS na lista :", len(extra_in_list))

print("\nCobertura:", round(len(matched) / len(shp_images), 4))

print("\nExemplo de arquivos ausentes:")
print(list(missing_in_list)[:10])

# =========================
# 4. RESOLVER CAMINHOS
# =========================
def resolve_path(name):
    name = str(name).strip()
    return mapping.get(name)

gdf["IMG_PATH"] = gdf["NOME_FOTO"].apply(resolve_path)

# =========================
# 5. LIMPAR DATASET
# =========================
clean_gdf = gdf.dropna(subset=["IMG_PATH"]).copy()

print("\n=== RELATÓRIO DE LIMPEZA ===")
print("Linhas originais :", len(gdf))
print("Linhas limpas    :", len(clean_gdf))
print("Removidas        :", len(gdf) - len(clean_gdf))

# =========================
# 6. SALVAR GEODATASET LIMPO
# =========================
print("\nSalvando GeoPackage limpo...")
clean_gdf.to_file(OUT_GPKG, driver="GPKG")

# =========================
# 7. CRIAR MANIFESTO PARA ML
# =========================
manifest = clean_gdf[[
    "IMG_PATH",
    "NOME_FOTO",
    "UTM_E",
    "UTM_N",
    "TIPO_HABIT"
]].copy()

manifest.to_csv(OUT_MANIFEST, index=False)

print("\nManifesto salvo:", OUT_MANIFEST)

# =========================
# 8. DISTRIBUIÇÃO DAS CLASSES
# =========================
print("\n=== DISTRIBUIÇÃO DAS CLASSES ===")
print(clean_gdf["TIPO_HABIT"].value_counts().head(20))

# =========================
# 9. ESTATÍSTICAS DE USO DAS IMAGENS
# =========================
print("\n=== USO DAS IMAGENS ===")
print(clean_gdf["NOME_FOTO"].value_counts().head(20))
