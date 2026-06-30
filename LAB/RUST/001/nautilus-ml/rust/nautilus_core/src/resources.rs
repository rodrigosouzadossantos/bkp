// vim: set ts=2 sw=2 et:
// Nautilus ML
// Deep Sea AI/ML Platform
// Rust HPC Engine

pub fn init() {}
use pyo3::prelude::*;

#[pyfunction]
pub fn cpu_count() -> usize {
  num_cpus::get()
}
