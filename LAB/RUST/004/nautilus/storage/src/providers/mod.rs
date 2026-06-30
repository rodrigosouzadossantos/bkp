use std::sync::Arc;

use serde::Deserialize;

use crate::providers::local::LocalProvider;

#[cfg(feature = "s3")]
use crate::providers::s3::S3Provider;

//////////////////////////////////////////////////////
// TRAIT (PORT)
//////////////////////////////////////////////////////

pub trait StorageProvider: Send + Sync {

    /// Name of provider (for debugging / metadata)
    fn name(&self) -> &'static str;

    /// Root paths this provider exposes
    fn roots(&self) -> Vec<String>;

    /// List objects under a path
    fn list(&self, path: &str) -> Vec<String>;

    /// Read raw bytes (used by dataset layer)
    fn read(&self, path: &str) -> Vec<u8>;
}

//////////////////////////////////////////////////////
// STRUCTURED OUTPUT
//////////////////////////////////////////////////////

#[derive(Debug, Clone)]
pub struct StorageObject {
    pub provider: String,
    pub path: String,
}

//////////////////////////////////////////////////////
// CONFIG (ADAPTER INPUT)
//////////////////////////////////////////////////////

#[derive(Debug, Deserialize)]
pub struct StorageConfig {
    pub providers: Option<Vec<String>>,
}

//////////////////////////////////////////////////////
// PROVIDER FACTORY
//////////////////////////////////////////////////////

pub fn get_providers() -> Vec<Arc<dyn StorageProvider>> {

    // Priority:
    // 1. ENV
    // 2. YAML config
    // 3. Default

    if let Ok(env) = std::env::var("NAUTILUS_STORAGE") {
        return parse_provider_list(&env);
    }

    if let Ok(config) = load_config() {
        if let Some(providers) = config.providers {
            return providers
                .iter()
                .map(|p| build_provider(p))
                .collect();
        }
    }

    // Default fallback
    vec![Arc::new(LocalProvider::new())]
}

//////////////////////////////////////////////////////
// PROVIDER PARSER
//////////////////////////////////////////////////////

fn parse_provider_list(list: &str) -> Vec<Arc<dyn StorageProvider>> {

    list.split(',')
        .map(|p| build_provider(p.trim()))
        .collect()
}

//////////////////////////////////////////////////////
// PROVIDER BUILDER
//////////////////////////////////////////////////////

fn build_provider(name: &str) -> Arc<dyn StorageProvider> {

    match name {

        "local" => Arc::new(LocalProvider::new()),

        #[cfg(feature = "s3")]
        "s3" => Arc::new(S3Provider::new()),

        #[cfg(not(feature = "s3"))]
        "s3" => panic!("S3 feature not enabled"),

        _ => panic!("Unknown storage provider: {}", name),
    }
}

//////////////////////////////////////////////////////
// CONFIG LOADER
//////////////////////////////////////////////////////

fn load_config() -> Result<StorageConfig, Box<dyn std::error::Error>> {

    let path = std::env::var("NAUTILUS_CONFIG")
        .unwrap_or_else(|_| "configs/storage.yaml".to_string());

    let contents = std::fs::read_to_string(path)?;

    let config: StorageConfig = serde_yaml::from_str(&contents)?;

    Ok(config)
}

//////////////////////////////////////////////////////
// ORCHESTRATOR HELPERS
//////////////////////////////////////////////////////

/// Flatten all providers into a unified object list
pub fn list_all() -> Vec<StorageObject> {

    let providers = get_providers();

    providers
        .iter()
        .flat_map(|provider| {

            provider
                .roots()
                .into_iter()
                .flat_map(|root| {

                    provider
                        .list(&root)
                        .into_iter()
                        .map(|path| StorageObject {
                            provider: provider.name().to_string(),
                            path,
                        })
                        .collect::<Vec<_>>()

                })
                .collect::<Vec<_>>()

        })
        .collect()
}

//////////////////////////////////////////////////////
// MODULE DECLARATIONS
//////////////////////////////////////////////////////

pub mod local;

#[cfg(feature = "s3")]
pub mod s3;

// future:
// pub mod gcs;
// pub mod azure;
// pub mod cache;
