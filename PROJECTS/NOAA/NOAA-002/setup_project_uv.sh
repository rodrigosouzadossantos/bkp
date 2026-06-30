#!/usr/bin/env bash
set -e

PROJECT_NAME="image-iceberg-pipeline"

echo "=================================================="
echo "🚀 Creating project with UV: $PROJECT_NAME"
echo "=================================================="

# --------------------------------------------------
# 0. Ensure uv is installed
# --------------------------------------------------
if ! command -v uv &> /dev/null; then
  echo "❌ uv not found. Installing..."
  curl -LsSf https://astral.sh/uv/install.sh | sh
  export PATH="$HOME/.local/bin:$PATH"
fi

# --------------------------------------------------
# 1. Create project
# --------------------------------------------------
mkdir -p PYTHON/$PROJECT_NAME
cd PYTHON/$PROJECT_NAME

mkdir -p \
  src/{ingestion,features,embeddings,utils,schemas} \
  config \
  scripts \
  tests \
  notebooks

# --------------------------------------------------
# 2. Initialize UV project
# --------------------------------------------------
uv init \
  --python 3.13 \
  --name "$PROJECT_NAME"

# --------------------------------------------------
# 3. Python version (lock for Spark compatibility)
# --------------------------------------------------
uv python pin 3.13

# --------------------------------------------------
# 4. Add dependencies (UV replaces requirements.txt)
# --------------------------------------------------
uv add \
  pyspark \
  pyiceberg \
  boto3 \
  numpy \
  opencv-python \
  pillow \
  scipy \
  scikit-image \
  pandas \
  pyarrow \
  tqdm \
  h3 \
  shapely \
  geopandas \
  faiss-cpu \
  imagehash

# --------------------------------------------------
# 5. Dev tools
# --------------------------------------------------
uv add --dev ruff pytest ipykernel

# --------------------------------------------------
# 6. Spark + Iceberg config
# --------------------------------------------------

#spark.hadoop.fs.s3a.aws.credentials.provider=com.amazonaws.auth.DefaultAWSCredentialsProviderChain

cat > config/spark.conf <<EOF
spark.eventLog.dir=file:/root/SPARK/spark-events
spark.eventLog.enabled=true
spark.hadoop.fs.s3a.endpoint=http://localhost:8000
spark.hadoop.fs.s3a.access.key='AKIAJPG2FGB3ZE4VLNGQ'
spark.hadoop.fs.s3a.secret.key='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'
spark.hadoop.fs.s3a.path.style.access=true
spark.hadoop.fs.s3a.impl=org.apache.hadoop.fs.s3a.S3AFileSystem
spark.sql.catalog.lakefs=org.apache.iceberg.spark.SparkCatalog
spark.sql.catalog.lakefs.type=hadoop
spark.sql.catalog.lakefs.warehouse=s3a://iceberg/main/warehouse
spark.sql.extensions=org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions
spark.sql.debug.maxToStringFields=1000
EOF

# --------------------------------------------------
# 7. Settings
# --------------------------------------------------
cat > config/settings.yaml <<EOF
s3:
  bucket: noaa-auv 
  profile: lakefs

lakefs:
  repo: noaa-auv
  branch: main

iceberg:
  catalog: lakefs
  namespace: noaa.auv.image
  table: metadata

embedding:
  model: clip
  dim: 512
EOF

# --------------------------------------------------
# 8. Entry point
# --------------------------------------------------
cat > src/main.py <<'EOF'
from ingestion.spark_session import create_spark
from ingestion.ingest import run_ingestion

def main():
    spark = create_spark()
    run_ingestion(spark)

if __name__ == "__main__":
    main()
EOF

# --------------------------------------------------
# 9. Spark session
# --------------------------------------------------
cat > src/ingestion/spark_session.py <<'EOF'
from pyspark.sql import SparkSession

def create_spark():
    return (
        SparkSession.builder
        .appName("image-iceberg-pipeline")
        .config("spark.sql.extensions",
                "org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions")
        .config("spark.sql.catalog.lakefs",
                "org.apache.iceberg.spark.SparkCatalog")
        .config("spark.sql.catalog.lakefs.type", "hadoop")
        .config("spark.sql.catalog.lakefs.warehouse",
                "s3a://iceberg/main/warehouse")
        .getOrCreate()
    )
EOF

# --------------------------------------------------
# 10. ingestion stub
# --------------------------------------------------
cat > src/ingestion/ingest.py <<'EOF'
def run_ingestion(spark):
    print("🚀 Ingestion pipeline started")

    # Steps:
    # 1. Read S3 images
    # 2. Detect CAMERA vs RASTER
    # 3. Extract metadata (EXIF / GeoTIFF)
    # 4. Compute CV features
    # 5. Write to Iceberg

    print("✅ Done (stub)")
EOF

# --------------------------------------------------
# 11. feature extraction
# --------------------------------------------------
cat > src/features/extract.py <<'EOF'
import numpy as np

def compute_basic_features(img):
    return {
        "luminance_mean": float(np.mean(img)),
        "luminance_std": float(np.std(img)),
    }
EOF

# --------------------------------------------------
# 12. embedding stub
# --------------------------------------------------
cat > src/embeddings/clip.py <<'EOF'
def compute_embedding(img):
    # placeholder for CLIP / ViT
    return [0.0] * 512
EOF

# --------------------------------------------------
# 13. README
# --------------------------------------------------
cat > README.md <<EOF
# Image Iceberg Pipeline (UV-based)

## Stack
- UV (package manager)
- Spark + Iceberg
- S3 storage
- CV feature extraction
- CLIP embeddings

## Models
- CAMERA (AUV/UAV)
- RASTER (GeoTIFF)

## Goal
PB-scale geospatial + vision analytics lakehouse
EOF

# --------------------------------------------------
# 14. git init
# --------------------------------------------------
git init
git add .
git commit -m "UV-based Iceberg CV pipeline bootstrap"

echo "=================================================="
echo "✅ UV project ready"
echo "=================================================="
echo ""
echo "Next steps:"
echo "  uv run python src/main.py"
