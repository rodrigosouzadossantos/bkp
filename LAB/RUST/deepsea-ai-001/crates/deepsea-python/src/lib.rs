use pyo3::prelude::*;
use plugins::storage_s3::S3Store;
use plugins::storage_azure::AzureBlobStore;
use plugins::experiment_mlflow::MLFlowTracker;
use plugins::experiment_wandb::WandBTracker;
use plugins::experiment_lakefs::LakeFSClient;

#[pyclass]
struct PyS3Store { inner: S3Store }
#[pymethods]
impl PyS3Store {
  #[new] fn new(bucket: String) -> Self {
    let client = aws_sdk_s3::Client::new(&aws_config::load_from_env().unwrap());
    Self { inner: S3Store::new(&bucket, client) }
  }
  fn list(&self, prefix: String) -> Vec<String> { self.inner.list(&prefix) }
}

#[pyclass]
struct PyAzureBlob { inner: AzureBlobStore }
#[pymethods]
impl PyAzureBlob {
  #[new] fn new(container: String) -> Self {
    let client = azure_storage_blobs::prelude::ClientBuilder::default().build().unwrap();
    Self { inner: AzureBlobStore::new(&container, client) }
  }
  fn list(&self, prefix: String) -> Vec<String> { self.inner.list(&prefix) }
}

#[pyclass]
struct PyMLFlow { inner: MLFlowTracker }
#[pymethods]
impl PyMLFlow {
  #[new] fn new(endpoint: String) -> Self { Self { inner: MLFlowTracker { endpoint } } }
  fn start_run(&self, name: String) { self.inner.start_run(&name) }
}

#[pyclass]
struct PyWandB { inner: WandBTracker }
#[pymethods]
impl PyWandB {
  #[new] fn new(project: String, entity: String) -> Self { Self { inner: WandBTracker { project, entity } } }
  fn log_metric(&self, key: String, value: f64) { self.inner.log_metric(&key, value) }
}

#[pyclass]
struct PyLakeFS { inner: LakeFSClient }
#[pymethods]
impl PyLakeFS {
  #[new] fn new(endpoint: String, repo: String) -> Self { Self { inner: LakeFSClient { endpoint, repo } } }
  fn commit(&self, branch: String, message: String) { self.inner.commit(&branch, &message) }
}

#[pymodule]
fn deepsea_ai(_py: Python, m: &PyModule) -> PyResult<()> {
  m.add_class::<PyS3Store>()?;
  m.add_class::<PyAzureBlob>()?;
  m.add_class::<PyMLFlow>()?;
  m.add_class::<PyWandB>()?;
  m.add_class::<PyLakeFS>()?;
  Ok(())
}
