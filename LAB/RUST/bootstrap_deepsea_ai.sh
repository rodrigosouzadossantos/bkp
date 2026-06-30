#!/usr/bin/env bash
# vim: set ts=2 sw=2 et:

set -euo pipefail

ROOT="deepsea-ai"
CPU=96

echo "Bootstrapping DeepSea AI platform..."

########################################
# directory structure
########################################

mkdir -p $ROOT
cd $ROOT

mkdir -p \
crates/{deepsea-core,deepsea-storage,deepsea-video,deepsea-dataset,deepsea-runtime,deepsea-experiments,deepsea-vector,deepsea-python}/src \
plugins/{storage-s3,storage-azure,experiment-mlflow,experiment-wandb,experiment-lakefs,experiment-dvc}/src \
services/{ingestion-service,dataset-builder,training-orchestrator}/src \
python/deepsea_ai \
tests/{rust,python} \
scripts \
.github/workflows \
.github/copilot \
.vscode

########################################
# README
########################################

cat <<'EOF' > README.md
<!-- vim: set ts=2 sw=2 et: -->

# DeepSea AI Platform

Rust + Python platform for petabyte-scale computer vision.

## Integrated Systems

Storage
- AWS S3
- Azure Blob

Experiment Tracking
- MLFlow
- W&B
- DVC
- LakeFS

ML Frameworks
- PyTorch
- TensorFlow
- Keras
- Scikit-learn

## Hardware Target

96 CPU cores  
256GB RAM  
NVIDIA H100
EOF

########################################
# Cargo workspace
########################################

cat <<'EOF' > Cargo.toml
# vim: set ts=2 sw=2 et:

[workspace]
members = [
"crates/deepsea-core",
"crates/deepsea-storage",
"crates/deepsea-video",
"crates/deepsea-dataset",
"crates/deepsea-runtime",
"crates/deepsea-vector",
"crates/deepsea-experiments",
"crates/deepsea-python",

"plugins/storage-s3",
"plugins/storage-azure",

"plugins/experiment-mlflow",
"plugins/experiment-wandb",
"plugins/experiment-lakefs",
"plugins/experiment-dvc",

"services/ingestion-service",
"services/dataset-builder",
"services/training-orchestrator"
]

resolver = "2"

[profile.release]
lto = true
codegen-units = 1
EOF

########################################
# Python project
########################################

cat <<'EOF' > pyproject.toml
# vim: set ts=2 sw=2 et:

[build-system]
requires = ["maturin>=1.4"]
build-backend = "maturin"

[project]
name = "deepsea-ai"
version = "0.1.0"
requires-python = ">=3.10"

dependencies = [
"numpy",
"torch",
"tensorflow",
"keras",
"scikit-learn",
"opencv-python",
"pyarrow",

"mlflow",
"wandb",
"dvc",
"lakefs-client",

"boto3",
"azure-storage-blob",

"pytest",
"pytest-xdist",
"ruff"
]

[tool.pytest.ini_options]
addopts = "-n auto"

[tool.ruff]
line-length = 100
EOF

########################################
# Makefile
########################################

cat <<'EOF' > Makefile
# vim: set ts=2 sw=2 et:

CPU := $(shell nproc)

build:
	maturin develop --release

test:
	cargo test --all -- --test-threads=$(CPU)
	pytest -n $(CPU)

lint:
	cargo clippy --all-targets --all-features -- -D warnings
	ruff check python

format:
	cargo fmt
	ruff format python
EOF

########################################
# Rust core crate
########################################

cat <<'EOF' > crates/deepsea-core/src/lib.rs
// vim: set ts=2 sw=2 et:

use rayon::prelude::*;

pub fn parallel_map(data: Vec<u64>) -> Vec<u64> {
  data.par_iter().map(|x| x * 2).collect()
}
EOF

########################################
# storage interface
########################################

cat <<'EOF' > crates/deepsea-storage/src/lib.rs
// vim: set ts=2 sw=2 et:

pub trait ObjectStore {

  fn list(&self, prefix: &str) -> Vec<String>;

}
EOF

########################################
# S3 plugin
########################################

cat <<'EOF' > plugins/storage-s3/src/lib.rs
// vim: set ts=2 sw=2 et:

pub struct S3Store {

  pub bucket: String

}
EOF

########################################
# Azure plugin
########################################

cat <<'EOF' > plugins/storage-azure/src/lib.rs
// vim: set ts=2 sw=2 et:

pub struct AzureBlobStore {

  pub container: String

}
EOF

########################################
# experiment interface
########################################

cat <<'EOF' > crates/deepsea-experiments/src/lib.rs
// vim: set ts=2 sw=2 et:

pub trait ExperimentTracker {

  fn start_run(&self, name: &str);

  fn log_metric(&self, key: &str, value: f64);

}
EOF

########################################
# MLFlow plugin
########################################

cat <<'EOF' > plugins/experiment-mlflow/src/lib.rs
// vim: set ts=2 sw=2 et:

pub struct MLFlowTracker {

  pub endpoint: String

}
EOF

########################################
# W&B plugin
########################################

cat <<'EOF' > plugins/experiment-wandb/src/lib.rs
// vim: set ts=2 sw=2 et:

pub struct WandBTracker {

  pub project: String

}
EOF

########################################
# LakeFS plugin
########################################

cat <<'EOF' > plugins/experiment-lakefs/src/lib.rs
// vim: set ts=2 sw=2 et:

pub struct LakeFSClient {

  pub endpoint: String

}
EOF

########################################
# DVC plugin
########################################

cat <<'EOF' > plugins/experiment-dvc/src/lib.rs
// vim: set ts=2 sw=2 et:

pub fn dvc_commit(path: &str) {

  std::process::Command::new("dvc")
    .arg("add")
    .arg(path)
    .output()
    .unwrap();

}
EOF

########################################
# Python SDK
########################################

cat <<'EOF' > python/deepsea_ai/__init__.py
# vim: set ts=2 sw=2 et:

from .dataset import Dataset
EOF

cat <<'EOF' > python/deepsea_ai/dataset.py
# vim: set ts=2 sw=2 et:

class Dataset:

  def __init__(self, name):
    self.name = name
EOF

########################################
# tests
########################################

cat <<'EOF' > tests/python/test_dataset.py
# vim: set ts=2 sw=2 et:

from deepsea_ai import Dataset

def test_dataset():
  ds = Dataset("test")
  assert ds.name == "test"
EOF

########################################
# environment script
########################################

cat <<EOF > scripts/env.sh
#!/usr/bin/env bash
# vim: set ts=2 sw=2 et:

export RAYON_NUM_THREADS=$CPU
export OMP_NUM_THREADS=$CPU
export MKL_NUM_THREADS=$CPU
EOF

chmod +x scripts/env.sh

########################################
# GitHub Actions CI
########################################

cat <<'EOF' > .github/workflows/ci.yml
name: CI

on: [push]

jobs:
 build:

  runs-on: ubuntu-latest

  steps:
  - uses: actions/checkout@v3

  - name: Install Rust
    uses: actions-rs/toolchain@v1
    with:
      toolchain: stable

  - name: Install Python
    uses: actions/setup-python@v4
    with:
      python-version: 3.10

  - run: pip install -e .
  - run: cargo test --all
  - run: pytest
EOF

########################################
# Copilot instructions
########################################

cat <<'EOF' > .github/copilot/instructions.md
# vim: set ts=2 sw=2 et:

Project coding rules:

- Rust for infrastructure
- Python for ML workflows
- Use multiprocessing
- Use async IO
- Prefer streaming pipelines
EOF

########################################
# VSCode settings
########################################

cat <<'EOF' > .vscode/settings.json
{
  "editor.tabSize": 2,
  "editor.insertSpaces": true
}
EOF

echo ""
echo "DeepSea AI platform created."
echo ""
echo "Next:"
echo "cd deepsea-ai"
echo "source scripts/env.sh"
echo "make build"
echo "make test"
