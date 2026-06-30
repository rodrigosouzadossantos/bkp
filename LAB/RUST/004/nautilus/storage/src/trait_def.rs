use pyo3::PyResult;

pub trait StorageConnector: Send + Sync {
  fn list(&self, path : &str) -> PyResult<Vec<String>>;
}
