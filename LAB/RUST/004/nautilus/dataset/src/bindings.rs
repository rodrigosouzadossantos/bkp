use pyo3::prelude::*;

#[pyclass]
pub struct Dataset {
    name: String,
}

#[pymethods]
impl Dataset {
    #[new]
    pub fn new(name: String) -> Self {
        Self { name }
    }

    pub fn ingest(&self, files: Vec<String>) -> PyResult<String> {
        // call into Rust dataset::api functions here
        Ok(format!("Ingested {} files into {}", files.len(), self.name))
    }
}
