-- ============================================================
-- NAMESPACE (DATABASE)
-- ============================================================

CREATE NAMESPACE IF NOT EXISTS lakefs.noaa.auv.image;

USE lakefs.noaa.auv.image;

-- ============================================================
-- ICEBERG TABLE: metadata
-- ============================================================
-- Purpose:
--   Unified storage for large-scale image dataset (PB scale)
--   Supports both:
--     1. CAMERA images (AUV/UAV raw imagery with pose + altitude)
--     2. RASTER images (GeoTIFF / orthorectified GIS data)
--
-- Design goals:
--   - Efficient OLAP queries (Trino / Spark)
--   - Partition pruning at PB scale
--   - Supports CV + geospatial analytics
--   - Compatible with lakeFS versioning
-- ============================================================

CREATE TABLE metadata (

-- ============================================================
-- 1. IDENTITY & STORAGE LAYER
-- ============================================================

image_id STRING COMMENT 'Unique image identifier (UUID or deterministic hash)',

s3_uri STRING COMMENT 'S3 location of image file',

lakefs_snapshot_id STRING COMMENT 'lakeFS version / commit reference for reproducibility',

ingestion_time TIMESTAMP COMMENT 'Time image was ingested into data lake',

acq_time TIMESTAMP COMMENT 'Original acquisition time from sensor metadata',

source_system STRING COMMENT 'Origin system: AUV, UAV, survey vessel, etc.',


-- ============================================================
-- 2. GEOMETRY MODEL SWITCH (CRITICAL FIELD)
-- ============================================================

geometry_model STRING COMMENT 'Defines coordinate model: CAMERA (pose-based) or RASTER (GeoTIFF/GIS)',


-- ============================================================
-- 3. SPATIOTEMPORAL CORE (COMMON TO ALL IMAGES)
-- ============================================================

lat DOUBLE COMMENT 'Latitude of image center (WGS84 or derived)',

lon DOUBLE COMMENT 'Longitude of image center',

h3_index BIGINT COMMENT 'H3 spatial index for fast geospatial partitioning',

depth_m DOUBLE COMMENT 'Vehicle depth below surface (if available)',

altitude_m DOUBLE COMMENT 'Altitude above seabed (CAMERA only; NULL for RASTER)',

pitch DOUBLE COMMENT 'Camera pitch angle (degrees)',

roll DOUBLE COMMENT 'Camera roll angle (degrees)',

yaw DOUBLE COMMENT 'Camera yaw angle (degrees)',


-- ============================================================
-- 4. CAMERA MODEL (USED ONLY WHEN geometry_model = CAMERA)
-- ============================================================

camera_id STRING COMMENT 'Camera unique identifier',

camera_model STRING COMMENT 'Camera model name',

firmware STRING COMMENT 'Camera firmware version',

focal_length_mm DOUBLE COMMENT 'Lens focal length in millimeters',

sensor_width_mm DOUBLE COMMENT 'Sensor physical width',

sensor_height_mm DOUBLE COMMENT 'Sensor physical height',

image_width INT COMMENT 'Image width in pixels',

image_height INT COMMENT 'Image height in pixels',

exposure_ms DOUBLE COMMENT 'Exposure time in milliseconds',

aperture DOUBLE COMMENT 'Lens aperture (f-stop)',

analog_gain DOUBLE COMMENT 'Analog gain applied by sensor',

digital_gain DOUBLE COMMENT 'Digital gain applied',

sensor_gain DOUBLE COMMENT 'Total sensor gain',

fov_x_deg DOUBLE COMMENT 'Horizontal field of view (computed)',

fov_y_deg DOUBLE COMMENT 'Vertical field of view (computed)',


-- ============================================================
-- 5. GEOSPATIAL FOOTPRINT
-- ============================================================

footprint_polygon STRING COMMENT 'GeoJSON polygon of projected footprint (optional)',

footprint_width_m DOUBLE COMMENT 'Ground footprint width',

footprint_height_m DOUBLE COMMENT 'Ground footprint height',

footprint_area_m2 DOUBLE COMMENT 'Ground footprint area (CAMERA model only)',

ground_resolution_m DOUBLE COMMENT 'Mean ground sampling distance (meters per pixel)',

footprint_valid BOOLEAN COMMENT 'Indicates if footprint computation succeeded',


-- ============================================================
-- 6. RASTER
-- ============================================================

crs STRING COMMENT 'Coordinate Reference System (e.g., EPSG:31984)',

pixel_size_x DOUBLE COMMENT 'Ground resolution per pixel (X axis, meters)',

pixel_size_y DOUBLE COMMENT 'Ground resolution per pixel (Y axis, meters)',

tiepoint_x DOUBLE COMMENT 'GeoTIFF tiepoint X coordinate',

tiepoint_y DOUBLE COMMENT 'GeoTIFF tiepoint Y coordinate',

raster_type STRING COMMENT 'PixelIsArea or PixelIsPoint (GeoTIFF standard)',


-- ============================================================
-- 7. IMAGE QUALITY FEATURES (CV CORE METRICS)
-- ============================================================

luminance_mean DOUBLE COMMENT 'Mean luminance intensity',

luminance_std DOUBLE COMMENT 'Luminance standard deviation',

brightness_mean DOUBLE COMMENT 'Average brightness',

brightness_clipped_ratio DOUBLE COMMENT 'Fraction of under/overexposed pixels',

contrast_rms DOUBLE COMMENT 'Root mean square contrast',

sharpness_laplacian DOUBLE COMMENT 'Laplacian-based sharpness metric (blur indicator)',

blur_score DOUBLE COMMENT 'Normalized blur estimate',

noise_estimate DOUBLE COMMENT 'Estimated sensor noise level',

entropy DOUBLE COMMENT 'Image entropy (information content)',

edge_density DOUBLE COMMENT 'Density of edges (Sobel/Canny-based)',

texture_complexity DOUBLE COMMENT 'Texture variance / complexity score',


-- ============================================================
-- 8. COLOR FEATURES
-- ============================================================

r_mean DOUBLE COMMENT 'Mean red channel intensity',

g_mean DOUBLE COMMENT 'Mean green channel intensity',

b_mean DOUBLE COMMENT 'Mean blue channel intensity',

h_mean DOUBLE COMMENT 'Hue mean (HSV space)',

s_mean DOUBLE COMMENT 'Saturation mean',

v_mean DOUBLE COMMENT 'Value (brightness) mean',

color_variance DOUBLE COMMENT 'Overall color variance metric',


-- ============================================================
-- 9. COMPRESSED HISTOGRAM FEATURES (LOW STORAGE OVERHEAD)
-- ============================================================

hist_r ARRAY<INT> COMMENT 'Red channel histogram (compressed bins)',

hist_g ARRAY<INT> COMMENT 'Green channel histogram',

hist_b ARRAY<INT> COMMENT 'Blue channel histogram',


-- ============================================================
-- 10. QUALITY SCORING (FOR DATA FILTERING / ML TRAINING)
-- ============================================================

quality_score DOUBLE COMMENT 'Overall image usability score (0–1)',

usability_flag BOOLEAN COMMENT 'Whether image is usable for ML training',

redundancy_score DOUBLE COMMENT 'Similarity score vs nearby images (optional dedup metric)',


-- ============================================================
-- 11. ML EMBEDDINGS (OPTIONAL ADVANCED FEATURE)
-- ============================================================

embedding ARRAY<FLOAT> COMMENT 'CLIP / vision embedding (fixed 512-dim enforced in pipeline)',

embedding_norm DOUBLE COMMENT 'L2 norm of embedding (for ANN search optimization)',

embedding_model STRING COMMENT 'Model version used for embedding generation',


-- ============================================================
-- 12. VISUAL SIMILARITY (hash-based)
-- ============================================================

phash STRING COMMENT 'Perceptual hash (global structure similarity)',

whash STRING COMMENT 'Wavelet hash (robust to noise / blur)',

pdq_hash BINARY COMMENT 'PDQ perceptual hash (high-quality near-duplicate detection)',

pdq_quality_score DOUBLE COMMENT 'Quality/confidence score of PDQ hash'

)
USING iceberg

-- ============================================================
-- 13. ICEBERG PARTITIONING STRATEGY
-- ============================================================
-- Designed for:
--   - fast time slicing
--   - spatial pruning (H3)
--   - separation of CAMERA vs RASTER workloads
-- ============================================================

PARTITIONED BY (
  days(acq_time),               -- time-based pruning (critical for ML training sets)
  geometry_model,               -- separates CAMERA vs RASTER query paths
  bucket(32, camera_id),        -- balances ingestion + avoids hot partitions
  h3_index                      -- geospatial pruning at scale
)

COMMENT 'Unified PB-scale image dataset supporting CAMERA + RASTER geospatial models';


