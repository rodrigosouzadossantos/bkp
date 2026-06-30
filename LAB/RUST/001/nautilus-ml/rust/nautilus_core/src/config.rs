// vim: set ts=2 sw=2 et:
// Nautilus ML
// Deep Sea AI/ML Platform
// Rust HPC Engine

pub fn init() {}

use pyo3::prelude::*;

#[pyclass]
pub struct Config {
  #[pyo3(get, set)]
  pub workers: usize,
}

#[pymethods]
impl Config {
  #[new]
  fn new(workers: Option<usize>) -> Self {
    Self {
      workers: workers.unwrap_or(num_cpus::get()),
    }
  }

  fn show(&self) -> String {
    format!("Config: {} workers", self.workers)
  }
}
