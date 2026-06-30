#!/usr/bin/env bash
# vim: set ts=2 sw=2 et:

set -euo pipefail

ROOT="deepsea-ai"
CPU=96

cd $ROOT

echo "Populating full plugin implementations..."

########################################
# Storage Plugins
########################################

## S3 Plugin
cat <<'EOF' > plugins/storage-s3/src/lib.rs
// vim: set ts=2 sw=2 et:

use aws_sdk_s3::{Client, Error};
use tokio::runtime::Runtime;

pub struct S3Store {
  pub bucket: String,
  client: Client,
}

impl S3Store {
  pub fn new(bucket: &str, client: Client) -> Self {
    Self {
      bucket: bucket.to_string(),
      client,
    }
  }

  pub fn list(&self, prefix: &str) -> Vec<String> {
    let rt = Runtime::new().unwrap();
    rt.block_on(async {
      let resp = self.client
        .list_objects_v2()
        .bucket(&self.bucket)
        .prefix(prefix)
        .send()
        .await
        .unwrap();
      resp.contents.unwrap_or_default()
          .iter()
          .filter_map(|obj| obj.key.clone())
          .collect()
    })
  }
}
EOF

## Azure Blob Plugin
cat <<'EOF' > plugins/storage-azure/src/lib.rs
// vim: set ts=2 sw=2 et:

use azure_storage::prelude::*;
use azure_storage_blobs::prelude::*;
use tokio::runtime::Runtime;

pub struct AzureBlobStore {
  pub container: String,
  client: BlobServiceClient,
}

impl AzureBlobStore {
  pub fn new(container: &str, client: BlobServiceClient) -> Self {
    Self {
      container: container.to_string(),
      client,
    }
  }

  pub fn list(&self, prefix: &str) -> Vec<String> {
    let rt = Runtime::new().unwrap();
    rt.block_on(async {
      let mut result = vec![];
      let mut stream = self.client
        .container_client(&self.container)
        .list_blobs()
        .prefix(prefix)
        .into_stream();
      while let Some(blob_list) = stream.next().await {
        let blobs = blob_list.unwrap().blobs.blobs;
        for b in blobs {
          result.push(b.name);
        }
      }
      result
    })
  }
}
EOF

########################################
# Experiment Plugins
########################################

## MLFlow Plugin
cat <<'EOF' > plugins/experiment-mlflow/src/lib.rs
// vim: set ts=2 sw=2 et:

use reqwest::blocking::Client;

pub struct MLFlowTracker {
  pub endpoint: String,
}

impl MLFlowTracker {
  pub fn start_run(&self, run_name: &str) {
    let client = Client::new();
    let _ = client.post(format!("{}/api/2.0/mlflow/runs/create", self.endpoint))
      .json(&serde_json::json!({ "run_name": run_name }))
      .send();
  }
}
EOF

## W&B Plugin
cat <<'EOF' > plugins/experiment-wandb/src/lib.rs
// vim: set ts=2 sw=2 et:

use reqwest::blocking::Client;

pub struct WandBTracker {
  pub project: String,
  pub entity: String,
}

impl WandBTracker {
  pub fn log_metric(&self, key: &str, value: f64) {
    let client = Client::new();
    let _ = client.post("https://api.wandb.ai/metrics")
      .json(&serde_json::json!({ "project": self.project, "entity": self.entity, "key": key, "value": value }))
      .send();
  }
}
EOF

## LakeFS Plugin
cat <<'EOF' > plugins/experiment-lakefs/src/lib.rs
// vim: set ts=2 sw=2 et:

use reqwest::blocking::Client;

pub struct LakeFSClient {
  pub endpoint: String,
  pub repo: String,
}

impl LakeFSClient {
  pub fn commit(&self, branch: &str, message: &str) {
    let client = Client::new();
    let _ = client.post(format!("{}/api/v1/commits", self.endpoint))
      .json(&serde_json::json!({ "repo": self.repo, "branch": branch, "message": message }))
      .send();
  }
}
EOF

## DVC Plugin
cat <<'EOF' > plugins/experiment-dvc/src/lib.rs
// vim: set ts=2 sw=2 et:

pub fn dvc_add_commit(path: &str) {
  std::process::Command::new("dvc")
    .arg("add")
    .arg(path)
    .output()
    .unwrap();
  std::process::Command::new("dvc")
    .arg("commit")
    .arg("-m")
    .arg("Add data")
    .arg(path)
    .output()
    .unwrap();
}
EOF

########################################
# Python bindings via PyO3
########################################

cat <<'EOF' > crates/deepsea-python/src/lib.rs
use pyo3::prelude::*;
use plugins::storage_s3::S3Store;
use plugins::experiment_mlflow::MLFlowTracker;

#[pyclass]
struct PyS3Store {
  inner: S3Store,
}

#[pymethods]
impl PyS3Store {
  #[new]
  fn new(bucket: String) -> Self {
    let client = aws_sdk_s3::Client::new(&aws_config::load_from_env().unwrap());
    Self { inner: S3Store::new(&bucket, client) }
  }

  fn list(&self, prefix: String) -> Vec<String> {
    self.inner.list(&prefix)
  }
}

#[pyclass]
struct PyMLFlow {
  inner: MLFlowTracker,
}

#[pymethods]
impl PyMLFlow {
  #[new]
  fn new(endpoint: String) -> Self {
    Self { inner: MLFlowTracker { endpoint } }
  }

  fn start_run(&self, name: String) {
    self.inner.start_run(&name)
  }
}

#[pymodule]
fn deepsea_ai(_py: Python, m: &PyModule) -> PyResult<()> {
  m.add_class::<PyS3Store>()?;
  m.add_class::<PyMLFlow>()?;
  Ok(())
}
EOF

echo "All plugin implementations created."
echo "Now you can build the Python package and run Rust/PyO3 bindings."
