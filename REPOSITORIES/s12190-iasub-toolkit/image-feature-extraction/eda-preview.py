import marimo

__generated_with = "0.23.4"
app = marimo.App()


@app.cell
def _():
    from pyspark.sql import SparkSession

    spark = (
        SparkSession
            .builder
            .appName("EDA-NOAA")
            .getOrCreate()
    )
    return (spark,)


@app.cell
def _(spark):
    viola = spark.read.format("iceberg").load("lakefs.images_eda.viola")
    viola.printSchema()
    return (viola,)


@app.cell
def _(viola):
    viola.show(1, truncate=False, vertical=True)
    return


@app.cell
def _(spark):
    espadarte = spark.read.format("iceberg").load("lakefs.images_eda.espadarte")
    espadarte.printSchema()
    return (espadarte,)


@app.cell
def _(espadarte):
    espadarte.show(1, truncate=False, vertical=True)
    return


@app.cell
def _():
    # from pyspark.sql import functions as F

    # def has_nested_field(schema, path):
    #     parts = path.split(".")
    #     current = schema

    #     for part in parts:
    #         if part not in current.names:
    #             return False

    #         field = current[part]

    #         if not hasattr(field.dataType, "names"):
    #             if part != parts[-1]:
    #                 return False

    #         current = field.dataType

    #     return True


    # def safe_col(df, path, dtype="string"):
    #     if has_nested_field(df.schema, path):
    #         return F.col(path)
    #     return F.lit(None).cast(dtype)


    return


@app.cell
def _(F, espadarte, safe_col):
    df = espadarte

    (df
        .withColumn("width_px", F.col("gdal.raster_size.width"))
        .withColumn("height_px", F.col("gdal.raster_size.height"))
        .withColumn("bands", F.col("gdal.raster_size.bands"))

        .withColumn("uciqe_score", F.col("subsea_eda.uciqe_score"))
        .withColumn("sharpness", F.col("subsea_eda.sharpness_tenengrad"))

        .withColumn(
            "longitude",
            F.coalesce(
                safe_col(df, "exif.File.Comment.image.Position.Coords.long"),
                safe_col(df, "exif.ExifIFD.UserComment.image.Position.Coords.long"),
                safe_col(df, "exif.IFD0.XPComment.image.Position.Coords.long"),
            )
        )

        .withColumn(
            "latitude",
            F.coalesce(
                safe_col(df, "exif.File.Comment.image.Position.Coords.lat"),
                safe_col(df, "exif.ExifIFD.UserComment.image.Position.Coords.lat"),
                safe_col(df, "exif.IFD0.XPComment.image.Position.Coords.lat"),
            )
        )

        .withColumn("phash", F.col("clustering_identity.phash"))
    )
    return


@app.cell
def _():
    # extractors/common.py

    from pyspark.sql import functions as F
    #from pyspark.sql.types import *


    def has_nested_field(schema, path: str) -> bool:
        """
        Checks whether a nested field exists in a Spark schema.
        """

        parts = path.split(".")
        current = schema

        for i, part in enumerate(parts):

            if not hasattr(current, "names"):
                return False

            if part not in current.names:
                return False

            field = current[part]

            if i < len(parts) - 1:
                current = field.dataType

        return True


    def safe_col(df, path: str, dtype: str = "string"):
        """
        Safely returns a column if path exists,
        otherwise returns NULL casted to dtype.
        """

        if has_nested_field(df.schema, path):
            return F.col(path)

        return F.lit(None).cast(dtype)


    def first_existing(df, paths, dtype="string"):
        """
        Coalesce first existing field among multiple paths.
        """

        cols = [safe_col(df, p, dtype) for p in paths]

        return F.coalesce(*cols)


    return F, first_existing, safe_col


@app.cell
def _(F, first_existing, safe_col):
    # extractors/spatial.py

    #from pyspark.sql import functions as F

    #from extractors.utils import safe_col, first_existing


    def extract_spatial(df):

        return (
            df

            # Geographic coordinates
            .withColumn(
                "longitude",
                first_existing(
                    df,
                    [
                        "exif.File.Comment.image.Position.Coords.long",
                        "exif.ExifIFD.UserComment.image.Position.Coords.long",
                        "exif.IFD0.XPComment.image.Position.Coords.long",
                    ],
                    dtype="double",
                ).cast("double")
            )

            .withColumn(
                "latitude",
                first_existing(
                    df,
                    [
                        "exif.File.Comment.image.Position.Coords.lat",
                        "exif.ExifIFD.UserComment.image.Position.Coords.lat",
                        "exif.IFD0.XPComment.image.Position.Coords.lat",
                    ],
                    dtype="double",
                ).cast("double")
            )

            # Vehicle navigation
            .withColumn(
                "depth_m",
                first_existing(
                    df,
                    [
                        "exif.File.Comment.image.Position.Depth.depth",
                        "exif.ExifIFD.UserComment.image.Position.Depth.depth",
                        "exif.IFD0.XPComment.image.Position.Depth.depth",
                    ],
                    dtype="double",
                ).cast("double")
            )

            .withColumn(
                "altitude_m",
                first_existing(
                    df,
                    [
                        "exif.File.Comment.image.Position.Depth.altitude",
                        "exif.ExifIFD.UserComment.image.Position.Depth.altitude",
                        "exif.IFD0.XPComment.image.Position.Depth.altitude",
                    ],
                    dtype="double",
                ).cast("double")
            )

            .withColumn(
                "yaw_deg",
                first_existing(
                    df,
                    [
                        "exif.File.Comment.image.Position.Direction.yaw",
                        "exif.ExifIFD.UserComment.image.Position.Direction.yaw",
                        "exif.IFD0.XPComment.image.Position.Direction.yaw",
                    ],
                    dtype="double",
                ).cast("double")
            )

            .withColumn(
                "pitch_deg",
                first_existing(
                    df,
                    [
                        "exif.File.Comment.image.Position.Direction.pitch",
                        "exif.ExifIFD.UserComment.image.Position.Direction.pitch",
                        "exif.IFD0.XPComment.image.Position.Direction.pitch",
                    ],
                    dtype="double",
                ).cast("double")
            )

            .withColumn(
                "roll_deg",
                first_existing(
                    df,
                    [
                        "exif.File.Comment.image.Position.Direction.roll",
                        "exif.ExifIFD.UserComment.image.Position.Direction.roll",
                        "exif.IFD0.XPComment.image.Position.Direction.roll",
                    ],
                    dtype="double",
                ).cast("double")
            )

            # GDAL / GeoTIFF
            .withColumn(
                "utm_center_x",
                F.expr("""
                    filter(gdal.corners, x -> x.name = 'center')[0].projected_x
                """)
            )

            .withColumn(
                "utm_center_y",
                F.expr("""
                    filter(gdal.corners, x -> x.name = 'center')[0].projected_y
                """)
            )
            
            .withColumn(
                "raster_width",
                safe_col(df, "gdal.raster_size.width", "long")
            )

            .withColumn(
                "raster_height",
                safe_col(df, "gdal.raster_size.height", "long")
            )

            .withColumn(
                "raster_bands",
                safe_col(df, "gdal.raster_size.bands", "long")
            )

            # Projection metadata
            .withColumn(
                "projection",
                safe_col(df, "exif.GeoTiff.Projection")
            )

            .withColumn(
                "projected_cs",
                safe_col(df, "exif.GeoTiff.PCSCitation")
            )

            # Derived metrics
            .withColumn(
                "aspect_ratio",
                F.when(
                    F.col("raster_height").isNotNull(),
                    F.col("raster_width") / F.col("raster_height")
                )
            )
        )


    return (extract_spatial,)


@app.cell
def _(F):
    # extractors/quality.py

    #from pyspark.sql import functions as F


    def extract_quality(df):

        return (
            df

            .withColumn(
                "uciqe_score",
                F.col("subsea_eda.uciqe_score")
            )

            .withColumn(
                "red_loss_ratio",
                F.col("subsea_eda.red_loss_ratio")
            )

            .withColumn(
                "avg_saturation",
                F.col("subsea_eda.avg_saturation")
            )

            .withColumn(
                "sharpness_tenengrad",
                F.col("subsea_eda.sharpness_tenengrad")
            )

            .withColumn(
                "data_coverage_pct",
                F.col("subsea_eda.data_coverage_pct")
            )

            # -----------------------------
            # Derived quality flags
            # -----------------------------
            .withColumn(
                "is_blurry",
                F.col("sharpness_tenengrad") < 30
            )

            .withColumn(
                "is_low_visibility",
                F.col("red_loss_ratio") > 0.7
            )

            .withColumn(
                "is_low_coverage",
                F.col("data_coverage_pct") < 0.9
            )

            # -----------------------------
            # Composite quality score
            # -----------------------------
            .withColumn(
                "quality_score",
                (
                    (F.col("uciqe_score") * 0.35)
                    + (F.col("sharpness_tenengrad") * 0.25)
                    + (F.col("avg_saturation") * 0.20)
                    + (F.col("data_coverage_pct") * 100 * 0.20)
                )
            )
        )


    return (extract_quality,)


@app.cell
def _(F, first_existing, safe_col):
    # extractors/camera.py

    #from pyspark.sql import functions as F

    #from extractors.utils import first_existing, safe_col


    def extract_camera(df):

        return (
            df

            .withColumn(
                "file_type",
                safe_col(df, "exif.File.FileType")
            )

            .withColumn(
                "mime_type",
                safe_col(df, "exif.File.MIMEType")
            )

            .withColumn(
                "width_px",
                F.col("gdal.raster_size.width")
            )

            .withColumn(
                "height_px",
                F.col("gdal.raster_size.height")
            )

            .withColumn(
                "bands",
                F.col("gdal.raster_size.bands")
            )

            .withColumn(
                "megapixels",
                safe_col(df, "exif.Composite.Megapixels").cast("double")
            )
            
            .withColumn(
                "camera_name",
                first_existing(
                    df,
                    [
                        "exif.File.Comment.image.acquisition.name",
                        "exif.ExifIFD.UserComment.image.acquisition.name",
                        "exif.IFD0.XPComment.image.acquisition.name",
                    ]
                )
            )

            .withColumn(
                "camera_model",
                first_existing(
                    df,
                    [
                        "exif.File.Comment.image.clarity-processing.Config.Camera.Model",
                        "exif.ExifIFD.UserComment.image.clarity-processing.Config.Camera.Model",
                        "exif.IFD0.XPComment.image.clarity-processing.Config.Camera.Model",
                    ]
                )
            )

            .withColumn(
                "firmware",
                first_existing(
                    df,
                    [
                        "exif.File.Comment.image.clarity-processing.Config.Camera.Firmware",
                        "exif.ExifIFD.UserComment.image.clarity-processing.Config.Camera.Firmware",
                        "exif.IFD0.XPComment.image.clarity-processing.Config.Camera.Firmware",
                    ]
                )
            )

            .withColumn(
                "exposure",
                first_existing(
                    df,
                    [
                        "exif.File.Comment.image.acquisition.exposure",
                        "exif.ExifIFD.UserComment.image.acquisition.exposure",
                        "exif.IFD0.XPComment.image.acquisition.exposure",
                    ],
                    dtype="double"
                ).cast("double")
            )

            .withColumn(
                "aperture",
                first_existing(
                    df,
                    [
                        "exif.File.Comment.image.acquisition.aperture",
                        "exif.ExifIFD.UserComment.image.acquisition.aperture",
                        "exif.IFD0.XPComment.image.acquisition.aperture",
                    ],
                    dtype="double"
                ).cast("double")
            )

            .withColumn(
                "digital_gain",
                first_existing(
                    df,
                    [
                        "exif.File.Comment.image.acquisition.digital.gain",
                        "exif.ExifIFD.UserComment.image.acquisition.digital.gain",
                        "exif.IFD0.XPComment.image.acquisition.digital.gain",
                    ],
                    dtype="double"
                ).cast("double")
            )

            .withColumn(
                "analog_gain",
                first_existing(
                    df,
                    [
                        "exif.File.Comment.image.acquisition.analog.gain",
                        "exif.ExifIFD.UserComment.image.acquisition.analog.gain",
                        "exif.IFD0.XPComment.image.acquisition.analog.gain",
                    ],
                    dtype="double"
                ).cast("double")
            )

            .withColumn(
                "sensor_gain",
                first_existing(
                    df,
                    [
                        "exif.File.Comment.image.acquisition.sensor.gain",
                        "exif.ExifIFD.UserComment.image.acquisition.sensor.gain",
                        "exif.IFD0.XPComment.image.acquisition.sensor.gain",
                    ],
                    dtype="double"
                ).cast("double")
            )

            .withColumn(
                "software_version",
                first_existing(
                    df,
                    [
                        "exif.File.Comment.image.versions.software",
                        "exif.ExifIFD.UserComment.image.versions.software",
                        "exif.IFD0.XPComment.image.versions.software",
                    ]
                )
            )
        )

    return (extract_camera,)


@app.cell
def _(F, safe_col):
    # extractors/clustering.py

    #from pyspark.sql import functions as F

    #from extractors.utils import safe_col


    def extract_clustering(df):

        return (
            df

            .withColumn(
                "phash",
                safe_col(df, "clustering_identity.phash")
            )

            .withColumn(
                "feature_vector",
                safe_col(df, "clustering_identity.feature_vector")
            )

            .withColumn(
                "feature_vector_length",
                F.when(
                    F.col("feature_vector").isNotNull(),
                    F.size("feature_vector")
                )
            )

            # Basic vector statistics
            .withColumn(
                "feature_vector_norm",
                F.expr("""
                    aggregate(
                        clustering_identity.feature_vector,
                        CAST(0 AS DOUBLE),
                        (acc, x) -> acc + (x * x)
                    )
                """)
            )

            .withColumn(
                "feature_vector_norm",
                F.sqrt("feature_vector_norm")
            )

            .withColumn(
                "feature_vector_sum",
                F.expr("aggregate(feature_vector, 0L, (acc, x) -> acc + x)")
            )

            .withColumn(
                "feature_vector_mean",
                F.when(
                    F.col("feature_vector_length") > 0,
                    F.col("feature_vector_norm") / F.col("feature_vector_length")
                )
            )

            # Duplicate candidate
            .withColumn(
                "is_valid_phash",
                F.length("phash") > 0
            )

            .withColumn(
                "phash_prefix",
                F.substring("clustering_identity.phash", 1, 8)
            )
        )

    return (extract_clustering,)


@app.cell
def _(
    extract_camera,
    extract_clustering,
    extract_quality,
    extract_spatial,
    viola,
):
    viola_gold = (
        viola
        .transform(extract_spatial)
        .transform(extract_quality)
        .transform(extract_camera)
        .transform(extract_clustering)
    )

    viola_gold.printSchema()
    return (viola_gold,)


@app.cell
def _(viola_gold):
    viola_gold
    return


@app.cell
def _(
    espadarte,
    extract_camera,
    extract_clustering,
    extract_quality,
    extract_spatial,
):
    espadarte_gold = (
        espadarte
        .transform(extract_spatial)
        .transform(extract_quality)
        .transform(extract_camera)
        .transform(extract_clustering)
    )

    espadarte_gold.printSchema()
    return (espadarte_gold,)


@app.cell
def _(espadarte_gold):
    espadarte_gold.select(['phash','phash_prefix'])
    return


if __name__ == "__main__":
    app.run()
