#!/usr/bin/env bash

set -e  # stop on error

ENV_NAME="eda-noaa"
PYTHON_VERSION="3.14"

echo "Creating environment with uv..."

# Create virtual environment
uv venv --python ${PYTHON_VERSION} ${ENV_NAME}

# Activate environment
source ${ENV_NAME}/bin/activate

echo "Installing dependencies..."

# Core
uv pip install \
    numpy \
    pandas \
    pyarrow \
    pyyaml

# Image processing
uv pip install \
    opencv-python \
    scikit-image

# ML / EDA
uv pip install \
    scikit-learn \
    matplotlib \
    seaborn

# EXIF + XML parsing
uv pip install \
    exifread \
    lxml

# Parallel / HPC
uv pip install \
    dask[complete] \
    distributed

# Optional (useful for large-scale + debugging)
uv pip install \
    tqdm \
    joblib

echo "Environment ready!"

echo ""
echo "To activate later:"
echo "source ${ENV_NAME}/bin/activate"
