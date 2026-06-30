from pyspark.sql import SparkSession, Row
from pyspark.sql.types import *
import rasterio
import hashlib
import os
import json


# =========================
# 1. SPARK INIT
# =========================

spark = (
    SparkSession.builder
    .appName("stable-geotiff-extractor-v1")
    .getOrCreate()
)

spark.conf.set("spark.sql.execution.arrow.pyspark.enabled", "false")


# =========================
# 2. SAFE TYPE HELPERS
# =========================

def safe_str(x):
    if x is None:
        return None
    if isinstance(x, (dict, list, tuple)):
        return json.dumps(x, default=str)
    return str(x)


def safe_float(x):
    try:
        return float(x)
    except:
        return None


def safe_int(x):
    try:
        return int(x)
    except:
        return None


def safe_list(x):
    if x is None:
        return []
    if isinstance(x, (list, tuple)):
        return list(x)
    return [x]


def safe_dict(x):
    if x is None:
        return {}
    if isinstance(x, dict):
        return x
    return {"value": str(x)}


# =========================
# 3. SCHEMA (STABLE v1)
# =========================

file_schema = StructType([
    StructField("path", StringType(), False),
    StructField("filename", StringType(), False),
    StructField("extension", StringType(), True),
    StructField("size_bytes", LongType(), True),
    StructField("checksum_md5", StringType(), True),
])

raster_schema = StructType([
    StructField("driver", StringType(), True),
    StructField("width", IntegerType(), True),
    StructField("height", IntegerType(), True),
    StructField("bands_count", IntegerType(), True),
    StructField("dtypes", ArrayType(StringType()), True),
    StructField("crs_wkt", StringType(), True),
    StructField("epsg", IntegerType(), True),
    StructField("transform", ArrayType(DoubleType()), True),
    StructField("nodata", DoubleType(), True),
    StructField("metadata", MapType(StringType(), StringType()), True),
])

tiff_ifd_schema = StructType([
    StructField("compression", StringType(), True),
    StructField("photometric", StringType(), True),
    StructField("planar_config", StringType(), True),
    StructField("rows_per_strip", IntegerType(), True),
    StructField("tile_width", IntegerType(), True),
    StructField("tile_length", IntegerType(), True),
    StructField("predictor", IntegerType(), True),
    StructField("bits_per_sample", ArrayType(IntegerType()), True),
    StructField("samples_per_pixel", IntegerType(), True),
    StructField("sample_format", ArrayType(StringType()), True),
    StructField("orientation", StringType(), True),
    StructField("byte_order", StringType(), True),
])

geotiff_schema = MapType(StringType(), StringType())

spatial_schema = StructType([
    StructField("bbox", ArrayType(DoubleType()), True),
    StructField("center", ArrayType(DoubleType()), True),
])

quality_band_stats = StructType([
    StructField("min", DoubleType(), True),
    StructField("max", DoubleType(), True),
    StructField("mean", DoubleType(), True),
    StructField("std", DoubleType(), True),
    StructField("valid_pixels", LongType(), True),
    StructField("nodata_pixels", LongType(), True),
    StructField("valid_percent", DoubleType(), True),
])

quality_schema = MapType(
    StringType(),
    quality_band_stats
)


schema = StructType([
    StructField("file", file_schema, True),
    StructField("raster", raster_schema, True),
    StructField("tiff_ifd", tiff_ifd_schema, True),
    StructField("geotiff", geotiff_schema, True),
    StructField("spatial", spatial_schema, True),
    StructField("quality", quality_schema, True),
])


# =========================
# 4. EXTRACTION
# =========================

def md5(path):
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            h.update(chunk)
    return h.hexdigest()


def extract(path):

    with rasterio.open(path) as ds:

        # ---- FILE ----
        file = {
            "path": path,
            "filename": os.path.basename(path),
            "extension": os.path.splitext(path)[1],
            "size_bytes": os.path.getsize(path),
            "checksum_md5": md5(path),
        }

        # ---- RASTER ----
        raster = {
            "driver": ds.driver,
            "width": ds.width,
            "height": ds.height,
            "bands_count": ds.count,
            "dtypes": list(ds.dtypes),
            "crs_wkt": ds.crs.to_wkt() if ds.crs else None,
            "epsg": ds.crs.to_epsg() if ds.crs else None,
            "transform": list(ds.transform) if ds.transform else None,
            "nodata": ds.nodata,
            "metadata": dict(ds.tags()) if ds.tags() else {},
        }

        # ---- TIFF IFD SAFE ----
        tags = ds.tags()
        tiff_ifd = {
            "compression": safe_str(tags.get("COMPRESSION")),
            "photometric": safe_str(tags.get("PHOTOMETRIC")),
            "planar_config": safe_str(tags.get("PLANARCONFIG")),
            "rows_per_strip": safe_int(tags.get("ROWS_PER_STRIP")),
            "tile_width": safe_int(tags.get("TILE_WIDTH")),
            "tile_length": safe_int(tags.get("TILE_LENGTH")),
            "predictor": safe_int(tags.get("PREDICTOR")),
            "bits_per_sample": [],
            "samples_per_pixel": safe_int(ds.count),
            "sample_format": [],
            "orientation": safe_str(tags.get("ORIENTATION")),
            "byte_order": safe_str(tags.get("BYTE_ORDER")),
        }

        # ---- GEOTIFF ----
        geotiff = {
            "model_pixel_scale": safe_list(tags.get("ModelPixelScale")),
            "model_tiepoint": safe_list(tags.get("ModelTiepoint")),
            "geo_keys": dict(tags) if tags else {}
        }

        # ---- SPATIAL ----
        bounds = ds.bounds
        spatial = {
            "bbox": [bounds.left, bounds.bottom, bounds.right, bounds.top],
            "center": [
                (bounds.left + bounds.right) / 2,
                (bounds.bottom + bounds.top) / 2
            ]
        }

        # ---- QUALITY ----
        quality = {}
        for i in range(1, ds.count + 1):
            band = ds.read(i)
            mask = band != ds.nodata if ds.nodata is not None else band > 0

            vals = band[mask]

            quality[f"band_{i}"] = {
                "min": float(vals.min()) if len(vals) else None,
                "max": float(vals.max()) if len(vals) else None,
                "mean": float(vals.mean()) if len(vals) else None,
                "std": float(vals.std()) if len(vals) else None,
                "valid_pixels": int(vals.size),
                "nodata_pixels": int((~mask).sum()),
                "valid_percent": float(vals.size / band.size * 100),
            }

        return {
            "file": file,
            "raster": raster,
            "tiff_ifd": tiff_ifd,
            "geotiff": geotiff,
            "spatial": spatial,
            "quality": quality,
        }


# =========================
# 5. MAIN
# =========================

def main():
    import sys

    path = sys.argv[1]
    row = extract(path)

    df = spark.createDataFrame([row], schema=schema)

    #df.printSchema()
    #df.show(truncate=False,vertical=True)

    import geopandas as gpd
    import matplotlib.pyplot as plt
    from shapely.geometry import box
    #pdf = df.select(
    #    "file.filename",
    #    "spatial.bbox"
    #).toPandas()

    #gdf = gpd.GeoDataFrame(
    #    pdf,
    #    geometry=[
    #        box(b[0], b[1], b[2], b[3]) for b in pdf["bbox"]
    #    ],
    #    crs="EPSG:31984"
    #)

    #ax = gdf.boundary.plot(figsize=(10, 10), edgecolor="blue")
    #gdf.plot(ax=ax, alpha=0.2)
    #plt.title("Raster Footprints (GDAL bbox)")
    #plt.show()
    

    #import folium

    ##center = df.select("spatial.center").first()[0]
    ##m = folium.Map(location=[center[1], center[0]], zoom_start=12)

    #from pyproj import Transformer

    #transformer = Transformer.from_crs("EPSG:31984", "EPSG:4326", always_xy=True)

    #pdf = df.select("file.filename", "spatial.bbox").toPandas()

    #m = folium.Map(location=[-22.7, -40.3], zoom_start=10)

    #for _, row in pdf.iterrows():
    #    xmin, ymin, xmax, ymax = row["bbox"]

    #    lon1, lat1 = transformer.transform(xmin, ymin)
    #    lon2, lat2 = transformer.transform(xmax, ymax)

    #    folium.Rectangle(
    #        bounds=[[lat1, lon1], [lat2, lon2]],
    #        color="blue",
    #        fill=True,
    #        fill_opacity=0.2
    #    ).add_to(m)

    #m.save("raster_footprints.html")


    ###
    ###
    ###
    ###
    pdf = df.select(
        "file.filename",
        "file.size_bytes",
        "raster.epsg",
        "raster.width",
        "raster.height",
        "spatial.bbox",
        "raster.crs_wkt"
    ).toPandas()

    def validate_row(row):
        warnings = []

        if row["epsg"] is None:
            warnings.append("Missing EPSG")

        if row["bbox"][2] <= row["bbox"][0]:
            warnings.append("Invalid X bounds")

        if row["bbox"][3] <= row["bbox"][1]:
            warnings.append("Invalid Y bounds")

        return " | ".join(warnings) if warnings else "OK"

    pdf["status"] = pdf.apply(validate_row, axis=1)

    #from pyproj import Transformer
    #from shapely.geometry import box

    #transformer = Transformer.from_crs("EPSG:31984", "EPSG:4326", always_xy=True)

    #import folium

    #m = folium.Map(location=[-22.7, -40.3], zoom_start=10)

    #for _, row in pdf.iterrows():
    #    xmin, ymin, xmax, ymax = row["bbox"]

    #    lon1, lat1 = transformer.transform(xmin, ymin)
    #    lon2, lat2 = transformer.transform(xmax, ymax)

    #    popup_html = f"""
    #    <b>{row['filename']}</b><br>
    #    EPSG: {row['epsg']}<br>
    #    Size: {row['width']} x {row['height']}<br>
    #    Status: {row['status']}
    #    """

    #    folium.Rectangle(
    #        bounds=[[lat1, lon1], [lat2, lon2]],
    #        color="red" if row["status"] != "OK" else "blue",
    #        fill=True,
    #        fill_opacity=0.3,
    #        popup=folium.Popup(popup_html, max_width=300)
    #    ).add_to(m)

    #m.save("raster_footprints_validated.html")


    ###
    ###
    ###
    ###

    #from shapely.geometry import box
    #import geopandas as gpd
    #import pandas as pd

    #def build_footprint_row(row):
    #    bbox = row["spatial"]["bbox"]

    #    minx, miny, maxx, maxy = bbox

    #    geom = box(minx, miny, maxx, maxy)

    #    return {
    #        "filename": row["file"]["filename"],
    #        "path": row["file"]["path"],
    #        "epsg": row["raster"]["epsg"],
    #        "geometry": geom,
    #        "minx": minx,
    #        "miny": miny,
    #        "maxx": maxx,
    #        "maxy": maxy,
    #        "center_lon": (minx + maxx) / 2,
    #        "center_lat": (miny + maxy) / 2
    #    }

    #pdf = df.select("file", "raster", "spatial").toPandas()

    #rows = [build_footprint_row(r) for r in pdf.to_dict("records")]

    #gdf = gpd.GeoDataFrame(rows, geometry="geometry", crs=f"EPSG:{rows[0]['epsg']}")

    #from keplergl import KeplerGl

    #map_1 = KeplerGl(height=600)

    #map_1.add_data(data=gdf, name="raster_footprints")  # ✅ correct

    #map_1.save_to_html(file_name="raster_footprints_kepler.html")



    from shapely.geometry import box
    import geopandas as gpd

    def build_gdf(spark_df):
        pdf = spark_df.select("file", "raster", "spatial").toPandas()

        rows = []
        for r in pdf.to_dict("records"):
            minx, miny, maxx, maxy = r["spatial"]["bbox"]

            rows.append({
                "filename": r["file"]["filename"],
                "path": r["file"]["path"],
                "epsg": r["raster"]["epsg"],
                "minx": minx,
                "miny": miny,
                "maxx": maxx,
                "maxy": maxy,
                "geometry": box(minx, miny, maxx, maxy),
                "center_lat": (miny + maxy) / 2,
                "center_lon": (minx + maxx) / 2,
            })

        gdf = gpd.GeoDataFrame(rows, geometry="geometry", crs=f"EPSG:{rows[0]['epsg']}")
        return gdf

    import json

    def to_geojson(gdf):
        features = []

        for _, r in gdf.iterrows():
            features.append({
                "type": "Feature",
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[
                        [r["minx"], r["miny"]],
                        [r["minx"], r["maxy"]],
                        [r["maxx"], r["maxy"]],
                        [r["maxx"], r["miny"]],
                        [r["minx"], r["miny"]],
                    ]]
                },
                "properties": {
                    "filename": r["filename"],
                    "epsg": int(r["epsg"])
                }
            })

        return {
            "type": "FeatureCollection",
            "features": features
        }

    import folium

    def build_folium_dashboard(gdf, output="dashboard.html"):
        center_lat = gdf["center_lat"].mean()
        center_lon = gdf["center_lon"].mean()

        m = folium.Map(location=[center_lat, center_lon], zoom_start=10)

        # 🔥 auto-fit to layer (your requirement)
        bounds = [
            [gdf["miny"].min(), gdf["minx"].min()],
            [gdf["maxy"].max(), gdf["maxx"].max()]
        ]
        m.fit_bounds(bounds)

        for _, r in gdf.iterrows():
            folium.Polygon(
                locations=[
                    [r["miny"], r["minx"]],
                    [r["miny"], r["maxx"]],
                    [r["maxy"], r["maxx"]],
                    [r["maxy"], r["minx"]],
                    [r["miny"], r["minx"]],
                ],
                popup=f"{r['filename']} (EPSG:{r['epsg']})",
                color="blue",
                fill=True,
                fill_opacity=0.2
            ).add_to(m)

        m.save(output)

    build_folium_dashboard(build_gdf(df))



if __name__ == "__main__":
    main()
