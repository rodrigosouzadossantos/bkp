use pyo3::prelude::*;

#[pyclass]
pub struct Storage;

#[pymethods]
impl Storage {

  #[staticmethod]
  #[pyo3(signature = (path=None))]
    pub fn list( path: Option<&str> ) -> Vec<(String, String)> {
      crate::list( path.unwrap_or("") )
        .into_iter()
        .map(|o| (o.provider, o.path))
        .collect()
    }
}
