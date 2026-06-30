mod trait_def;
mod local;
mod s3;

use pyo3::prelude::*;
use std::collections::HashMap;
use trait_def::StorageConnector;

#[pyclass]
pub struct StorageManager {
  backend: Box<dyn StorageConnector>,
}

#[pymethods]
impl StorageManager {
  #[new]
  pub fn new(config: HashMap<String, String>) -> PyResult<Self> {
    let kind = config.get("kind")
      .ok_or_else(|| PyErr::new::<pyo3::exceptions::PyValueError, _>("Missing 'kind'"))?;

    let backend: Box<dyn StorageConnector> = match kind.as_str() {
      "local" => {
        let root = config.get("root").cloned().unwrap_or_else(|| ".".to_string());
        Box::new(local::LocalConnector::new(root))
      },
      "s3" => {
        let bucket = config.get("bucket")
          .ok_or_else(|| PyErr::new::<pyo3::exceptions::PyValueError, _>("S3 requires 'bucket'"))?;
        Box::new(s3::S3Connector::new(bucket.clone())?)
      },
      _ => return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(format!("Unknown storage: {}", kind))),
    };

    Ok(Self { backend })
  }

  pub fn write(&self, path: &str, data: Vec<u8>) -> PyResult<()> { self.backend.write(path, data) }
  pub fn read(&self, path: &str) -> PyResult<Vec<u8>> { self.backend.read(path) }
}

