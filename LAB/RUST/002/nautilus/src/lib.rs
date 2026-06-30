use pyo3::prelude::*;
use pyo3::types::PyModule;

#[pyfunction]
fn add(a: i32, b: i32) -> PyResult<i32> {
  Ok(a + b)
}

#[pymodule]
fn nautilus(m: &Bound<'_, PyModule>) -> PyResult<()> {
  m.add_function(pyo3::wrap_pyfunction!(add, m)?)?;
  Ok(())
}
