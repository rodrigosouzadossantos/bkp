use pyo3::PyResult;

pub trait StorageConnector: Send + Sync {
  fn write(&self, path: &str, data: Vec<u8>) -> PyResult<()>;
  fn read(&self, path: &str) -> PyResult<Vec<u8>>;
}
