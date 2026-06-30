use rayon::prelude::*;
use std::collections::HashMap;

use crate::providers::{get_providers, StorageObject, StorageProvider};

//////////////////////////////////////////////////////
// PUBLIC API
//////////////////////////////////////////////////////

/// List all objects across all providers (flattened)
pub fn list( path: &str ) -> Vec<StorageObject> {
  let providers = get_providers();

  providers
    .par_iter()
    .flat_map(|provider| list_provider(provider.as_ref(), path))
    .collect()
}

/// List all objects for a specific provider
pub fn list_by_provider(name: &str, path: &str) -> Vec<StorageObject> {
  let providers = get_providers();

  providers
    .into_iter()
    .filter(|p| p.name() == name)
    .flat_map(|p| list_provider(p.as_ref(), path))
    .collect()
}

/// Resolve dataset name → actual storage paths
///
/// This is CRITICAL: Python never sees real paths.
pub fn resolve_dataset(name: &str) -> Vec<StorageObject> {
  let mapping = dataset_mapping();

  let paths = mapping.get(name)
    .unwrap_or_else(|| panic!("Dataset '{}' not found", name));

  let providers = get_providers();

  providers
    .par_iter()
    .flat_map(|provider| {

      paths.par_iter()
        .flat_map(|path| {

          // Only use provider if it matches prefix
          if matches_provider(provider.name(), path) {

            provider
              .list(path)
              .into_par_iter()
              .map(|p| StorageObject {
                provider: provider.name().to_string(),
                path: p,
              })
            .collect::<Vec<_>>()

          } else {
            vec![]
          }

        })
      .collect::<Vec<_>>()

    })
  .collect()
}

/// Read a single object (delegates to correct provider)
pub fn read(path: &str) -> Vec<u8> {
  let providers = get_providers();

  let provider = providers
    .into_iter()
    .find(|p| matches_provider(p.name(), path))
    .unwrap_or_else(|| panic!("No provider found for path: {}", path));

  provider.read(path)
}

//////////////////////////////////////////////////////
// INTERNAL HELPERS
//////////////////////////////////////////////////////

fn list_provider(provider: &dyn StorageProvider, path: &str) -> Vec<StorageObject> {

  provider
    .roots()
    .par_iter()
    .flat_map(|root| {
      let full_path = format!("{}/{}", root, path);

      provider
        .list(&full_path)
        .into_par_iter()
        .map(|path| StorageObject {
          provider: provider.name().to_string(),
          path,
        })
      .collect::<Vec<_>>()

    })
  .collect()
}

/// Determine if a provider should handle a path
fn matches_provider(provider: &str, path: &str) -> bool {

  match provider {
    "local" => path.starts_with("./") || path.starts_with("/"),
    "s3" => path.starts_with("s3://"),
    "gcs" => path.starts_with("gcs://"),
    "azure" => path.starts_with("azure://"),
    _ => false,
  }
}

//////////////////////////////////////////////////////
// DATASET MAPPING (CONFIG-DRIVEN IN FUTURE)
//////////////////////////////////////////////////////

/// Temporary in-memory mapping
/// Replace with YAML / DVC / LakeFS later
fn dataset_mapping() -> HashMap<String, Vec<String>> {

  let mut map = HashMap::new();

  map.insert(
    "images".to_string(),
    vec![
    "./data/images".to_string(),
    "s3://ml-bucket/images".to_string(),
    ],
  );

  map.insert(
    "videos".to_string(),
    vec![
    "./data/videos".to_string(),
    "s3://ml-bucket/videos".to_string(),
    ],
  );

  map
}

//////////////////////////////////////////////////////
// FUTURE: ARROW INGESTION HOOK
//////////////////////////////////////////////////////

/// Placeholder for zero-copy ingestion
/// Will return Arrow RecordBatch later
pub fn load_dataset_arrow(_name: &str) {
    // TODO:
    // 1. resolve_dataset(name)
    // 2. read files in parallel
    // 3. convert to Arrow
    // 4. expose via FFI
}

//////////////////////////////////////////////////////
// FUTURE: CACHING LAYER
//////////////////////////////////////////////////////

/// Placeholder for caching layer
pub fn read_with_cache(path: &str) -> Vec<u8> {
    // TODO:
    // check local cache
    // fallback to provider
    // store in cache
    read(path)
}
