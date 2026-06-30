use crate::providers::StorageProvider;

use rayon::prelude::*;
use std::fs;
use std::path::{Path, PathBuf};

//////////////////////////////////////////////////////
// LOCAL PROVIDER
//////////////////////////////////////////////////////

pub struct LocalProvider;

impl LocalProvider {
    pub fn new() -> Self {
        Self
    }

    //////////////////////////////////////////////////////
    // INTERNAL RECURSIVE LIST
    //////////////////////////////////////////////////////

    fn list_recursive(path: &Path) -> Vec<String> {

        if !path.exists() {
            return vec![];
        }

        let entries: Vec<PathBuf> = match fs::read_dir(path) {
            Ok(read_dir) => read_dir
                .filter_map(|e| e.ok())
                .map(|e| e.path())
                .collect(),
            Err(_) => return vec![],
        };

        entries
            .par_iter()
            .flat_map(|entry| {

                if entry.is_dir() {
                    // recurse into directory
                    Self::list_recursive(entry)
                } else {
                    // file
                    vec![normalize_path(entry)]
                }

            })
            .collect()
    }

    //////////////////////////////////////////////////////
    // OPTIONAL: SHALLOW LIST (NON-RECURSIVE)
    //////////////////////////////////////////////////////

    fn list_shallow(path: &Path) -> Vec<String> {

        if !path.exists() {
            return vec![];
        }

        match fs::read_dir(path) {
            Ok(read_dir) => read_dir
                .filter_map(|e| e.ok())
                .map(|e| normalize_path(&e.path()))
                .collect(),
            Err(_) => vec![],
        }
    }
}

//////////////////////////////////////////////////////
// TRAIT IMPLEMENTATION
//////////////////////////////////////////////////////

impl StorageProvider for LocalProvider {

    fn name(&self) -> &'static str {
        "local"
    }

    fn roots(&self) -> Vec<String> {

        // In production: load from config
        vec![
            "./data".to_string()
        ]
    }

    fn list(&self, path: &str) -> Vec<String> {

        let path = Path::new(path);

        // Recursive listing by default
        Self::list_recursive(path)
    }

    fn read(&self, path: &str) -> Vec<u8> {

        match fs::read(path) {
            Ok(bytes) => bytes,
            Err(_) => vec![], // in production: return Result<>
        }
    }
}

//////////////////////////////////////////////////////
// HELPERS
//////////////////////////////////////////////////////

fn normalize_path(path: &Path) -> String {

    // Convert to consistent string format
    path.to_string_lossy()
        .replace("\\", "/") // Windows compatibility
}
