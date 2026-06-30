use pyo3::prelude::*;

use crate::trait_def::StorageConnector;

pub struct S3Connector;

impl StorageConnector for S3Connector {
  fn list(&self, path: &str) -> PyResult<Vec<String>> {
    Ok(vec!["s3://bucket/photo.jpg".to_string(), "s3://bucket/data.csv".to_string()])
  }
}

