mod trait_def;
mod local;
mod s3;

use pyo3::prelude::*;
use trait_def::StorageConnector;
use std::collections::HashMap;

#[pyclass]
pub struct Storage {
  // Box holds the generic implementation
  backend: Box<dyn StorageConnector>,
}

#[pymethods]
impl Storage {
  #[new]
  pub fn new(config: HashMap<String, String>) -> PyResult<Self> {
    let kind = config.get("kind")
      .ok_or_else(|| PyErr::new::<pyo3::exceptions::PyValueError, _>("Missing 'kind' in config"))?;

    let backend: Box<dyn StorageConnector> = match kind.as_str() {
      "local" => Box::new(local::LocalConnector),
      "s3" => Box::new(s3::S3Connector),
      _ => return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>("Unknown storage kind")),
    };

    Ok(Storage { backend })
  }

  pub fn list(&self) -> PyResult<Vec<String>> {
    self.backend.list("path")
  }
}
