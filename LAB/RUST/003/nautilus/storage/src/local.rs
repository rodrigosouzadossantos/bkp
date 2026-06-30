use std::fs;
use std::path::PathBuf;
use pyo3::prelude::*;
use crate::trait_def::StorageConnector;

pub struct LocalConnector {
    root: PathBuf,
}

impl LocalConnector {
    pub fn new(root: String) -> Self {
        Self { root: PathBuf::from(root) }
    }
}

impl StorageConnector for LocalConnector {
    fn write(&self, path: &str, data: Vec<u8>) -> PyResult<()> {
        let full_path = self.root.join(path);
        if let Some(parent) = full_path.parent() {
            fs::create_dir_all(parent)
              .map_err(
                |e| PyErr::new::<pyo3::exceptions::PyIOError, _>(e.to_string())
              )?;
        }
        fs::write(full_path, data)
          .map_err(
            |e| PyErr::new::<pyo3::exceptions::PyIOError, _>(e.to_string())
          )
    }

    fn read(&self, path: &str) -> PyResult<Vec<u8>> {
        fs::read(self.root.join(path))
          .map_err(
            |e| PyErr::new::<pyo3::exceptions::PyIOError, _>(e.to_string())
          )
    }
}

