import geopandas as gpd
from sklearn.cluster import DBSCAN
import pandas as pd

# =========================
# CONFIG
# =========================
SHP_PATH = "/tmp/class_esp/CLASS_ESP_MODEL_IA.shp"

# specialist-defined habitat distance
EPS_METERS = 2

# =========================
# LOAD SHAPEFILE
# =========================
gdf = gpd.read_file(SHP_PATH)

# cleanup
gdf["NOME_FOTO"] = gdf["NOME_FOTO"].astype(str).str.strip()

# =========================
# COORDINATES
# =========================
coords = gdf[["UTM_E", "UTM_N"]].values

# =========================
# DBSCAN CLUSTERING
# =========================
clustering = DBSCAN(
    eps=EPS_METERS,
    min_samples=1
).fit(coords)

# assign cluster ids
gdf["cluster"] = clustering.labels_

# =========================
# REPORT
# =========================
report = (
    gdf.groupby("cluster")
    .agg(
        num_annotations=("NOME_FOTO", "size"),
        num_images=("NOME_FOTO", "nunique"),
        num_classes=("TIPO_HABIT", "nunique")
    )
    .sort_values("num_annotations", ascending=False)
)

# =========================
# FULL PRINT
# =========================
pd.set_option("display.max_rows", None)
pd.set_option("display.max_columns", None)
pd.set_option("display.width", None)

print(report)

# =========================
# SAVE
# =========================
#gdf.to_file("clustered_annotations.gpkg", driver="GPKG")

#report.to_csv("cluster_report.csv")

#print("\nSaved:")
#print("  clustered_annotations.gpkg")
#print("  cluster_report.csv")
