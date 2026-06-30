use pyo3::prelude::*;

use crate::trait_def::StorageConnector;

pub struct LocalConnector;

impl StorageConnector for LocalConnector {
    fn list(&self, path: &str) -> PyResult<Vec<String>> {
      Ok(vec!["local_file_1.txt".to_string(), "local_file_2.png".to_string()])
    }
}

