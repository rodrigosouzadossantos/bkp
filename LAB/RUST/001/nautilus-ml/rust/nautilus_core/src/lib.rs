// vim: set ts=2 sw=2 et:
// Nautilus ML
// Deep Sea AI/ML Platform
// Rust HPC Engine


use pyo3::prelude::*;
use pyo3::wrap_pyfunction;

pub mod config;
pub mod errors;
pub mod logging;
pub mod metrics;
pub mod resources;

#[pymodule]
fn nautilus_core(_py: Python, m: &PyModule) -> PyResult<()> {
//  m.add_class::<config::Config>()?;
//  m.add_function(wrap_pyfunction!(resources::cpu_count, m)?)?;
  Ok(())
}
