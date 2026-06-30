import geopandas as gpd
import pandas as pd

# =========================
# CONFIG
# =========================
SHP_PATH = "/tmp/class_esp/CLASS_ESP_MODEL_IA.shp"

# spatial bin size in meters
GRID_SIZE = 50

# =========================
# LOAD DATA
# =========================
gdf = gpd.read_file(SHP_PATH)

# Optional cleanup
gdf["NOME_FOTO"] = gdf["NOME_FOTO"].astype(str).str.strip()

# =========================
# ONE ROW PER IMAGE
# =========================
# multiple annotations may exist per image,
# so keep one representative coordinate per image
images = (
    gdf.groupby("NOME_FOTO")
    .first()
    .reset_index()
)

# =========================
# SPATIAL GRID BINNING
# =========================
# Convert UTM coordinates into grid cells
images["grid_x"] = (images["UTM_E"] // GRID_SIZE).astype(int)
images["grid_y"] = (images["UTM_N"] // GRID_SIZE).astype(int)

# Unique spatial tile ID
images["tile"] = (
    images["grid_x"].astype(str)
    + "_"
    + images["grid_y"].astype(str)
)

# =========================
# TILE REPORT
# =========================
tile_report = (
    images.groupby("tile")
    .agg(
        num_images=("NOME_FOTO", "nunique"),
        mean_x=("UTM_E", "mean"),
        mean_y=("UTM_N", "mean")
    )
    .sort_values("num_images", ascending=False)
)

# =========================
# PRINT FULL REPORT
# =========================
pd.set_option("display.max_rows", None)
pd.set_option("display.max_columns", None)
pd.set_option("display.width", None)

print(tile_report)

# =========================
# SAVE RESULTS
# =========================
images.to_csv("images_with_tiles.csv", index=False)
tile_report.to_csv("tile_report.csv")

print("\nSaved:")
print("  images_with_tiles.csv")
print("  tile_report.csv")
