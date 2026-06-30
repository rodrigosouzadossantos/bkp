#!/usr/bin/env bash
set -euo pipefail

PROJECT="cvx"

# Rollback on error
rollback() {
    echo -e "\033[31mError occurred. Rolling back...\033[0m"
    cd ..
    rm -rf "${PROJECT}"
    exit 1
}
trap rollback ERR

#----------------------------------------
# Helper: create directory + __init__.py
#----------------------------------------
create_domain() {
    local domain_path=$1
    mkdir -p "$domain_path"
    cat <<EOF > "$domain_path/__init__.py"
raise ImportError(
    "Direct import of this domain is forbidden. Use the CVX public API."
)
EOF
}

#----------------------------------------
# Helper: create Python file with header
#----------------------------------------
create_py() {
    local file_path=$1
    mkdir -p "$(dirname "$file_path")"
    cat <<EOF > "$file_path"
# -*- coding: utf-8 -*-
\"\"\"
Module: $(basename "$file_path")
Part of ${PROJECT} HPC Vision AI Platform
\"\"\"

from __future__ import annotations
__all__ = []
EOF
}

#----------------------------------------
# Root public API
#----------------------------------------
create_root_init() {
    local root_path=$1
    mkdir -p "$root_path"
    cat <<EOF > "$root_path/__init__.py"
from cvx.pipelines.image.image_manager import ImageManager
from cvx.pipelines.video.video_manager import VideoManager
from cvx.lifecycle.experiment.experiment_runner import ExperimentRunner

images = ImageManager()
videos = VideoManager()
experiment = ExperimentRunner()
EOF
}

#----------------------------------------
# Create top-level directories
#----------------------------------------
create_infrastructure() {
    mkdir -p "${PROJECT}"
    cd "${PROJECT}"

    echo -e "\033[34mCreating repository root...\033[0m"
    touch README.md LICENSE Makefile

    mkdir -p docker k8s benchmarks tests/{unit,integration,distributed,memory,performance}

    touch docker/Dockerfile.gpu \
          docker/Dockerfile.edge \
          docker/Dockerfile.server \
          docker/docker-compose.yml

    touch k8s/ray-cluster.yaml \
          k8s/gpu-serving.yaml \
          k8s/kafka.yaml \
          k8s/spark.yaml

    touch benchmarks/h100_throughput.py \
          benchmarks/memory_profile.py \
          benchmarks/nvlink_test.py \
          benchmarks/streaming_latency.py
}

#----------------------------------------
# Create domain-wrapped Python structure
#----------------------------------------
create_domains() {
    echo -e "\033[34mCreating domain-wrapped package structure...\033[0m"

    # Domains
    DOMAINS=(platform data pipelines inference lifecycle services)

    for d in "${DOMAINS[@]}"; do
        create_domain "${PROJECT}/$d"
    done

    # Submodules per domain
    declare -A SUBMODULES
    SUBMODULES[platform]="core models training distributed"
    SUBMODULES[data]="storage cache memory"
    SUBMODULES[pipelines]="image video multimodal"
    SUBMODULES[inference]="serving edge"
    SUBMODULES[lifecycle]="experiments features"
    SUBMODULES[services]="api agent search streaming anomaly reporting"

    for domain in "${!SUBMODULES[@]}"; do
        for sub in ${SUBMODULES[$domain]}; do
            create_domain "${PROJECT}/${domain}/${sub}"
        done
    done
}

#----------------------------------------
# Create placeholder Python files
#----------------------------------------
create_placeholder_files() {
    echo -e "\033[34mCreating placeholder Python files...\033[0m"

    FILES=(
        platform/core/config.py
        platform/core/base_model.py
        platform/models/torch_model.py
        pipelines/image/image_manager.py
        pipelines/video/video_manager.py
        lifecycle/experiment/experiment_runner.py
    )

    for f in "${FILES[@]}"; do
        create_py "${PROJECT}/$f"
    done
}

#----------------------------------------
# Create pyproject.toml
#----------------------------------------
create_pyproject() {
    echo -e "\033[34mCreating pyproject.toml...\033[0m"
    cat <<EOF > pyproject.toml
[project]
name = "${PROJECT}"
version = "0.1.0"
description = "Distributed HPC Vision AI Platform"
requires-python = ">=3.10"

[build-system]
requires = ["setuptools>=61"]
build-backend = "setuptools.build_meta"
EOF
}

#----------------------------------------
# Main bootstrap
#----------------------------------------
main() {
    create_infrastructure
    create_domains
    create_placeholder_files
    create_root_init "${PROJECT}"
    create_pyproject
    echo -e "\033[32mRepository ${PROJECT} created successfully.\033[0m"
}

main
