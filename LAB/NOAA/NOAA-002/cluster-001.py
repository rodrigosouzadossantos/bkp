import geopandas as gpd
from sklearn.cluster import DBSCAN
import pandas as pd

pd.set_option("display.max_rows", None)
pd.set_option("display.max_columns", None)
pd.set_option("display.width", None)
pd.set_option("display.max_colwidth", None)


# Load shapefile
gdf = gpd.read_file("/tmp/class_esp/CLASS_ESP_MODEL_IA.shp")

# One row per image
images = gdf.groupby("NOME_FOTO").first().reset_index()

# Coordinates
coords = images[["UTM_E", "UTM_N"]].values

# Spatial clustering
clustering = DBSCAN(
    eps=2,       # meters
    min_samples=1
).fit(coords)

# Assign cluster labels
images["cluster"] = clustering.labels_

# Save image-level clusters
#images.to_csv("clustered_images.csv", index=False)

# -------------------------------------------------
# MERGE CLUSTERS BACK INTO FULL GEO DATAFRAME
# -------------------------------------------------
gdf = gdf.merge(
    images[["NOME_FOTO", "cluster"]],
    on="NOME_FOTO",
    how="left"
)

# -------------------------------------------------
# REPORT
# -------------------------------------------------
report = (
    gdf.groupby("cluster")
    .agg(
        num_annotations=("NOME_FOTO", "size"),
        num_images=("NOME_FOTO", "nunique"),
        num_classes=("TIPO_HABIT", "nunique")
    )
    .sort_values("num_images", ascending=False)
)

print(report)

# Optional save
#report.to_csv("cluster_report.csv")

cluster_centers = (
    gdf.groupby("cluster")[["UTM_E", "UTM_N"]]
    .mean()
)

print(cluster_centers)
