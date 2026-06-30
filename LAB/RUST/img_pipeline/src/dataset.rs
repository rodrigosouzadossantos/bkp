use crate::storage::Storage;
use futures::{Stream, StreamExt};
use std::sync::Arc;
use bytes::Bytes;

pub struct Dataset {
    storage: Arc<dyn Storage>,
}

impl Dataset {
    pub fn new(storage: Arc<dyn Storage>) -> Self {
        Self { storage }
    }

    pub async fn list(&self, prefix: &str) -> impl Stream<Item = String> {
        self.storage
            .list(prefix)
            .await
            .unwrap()
            .filter_map(|r| async move { r.ok() })
    }

    pub fn load(
        &self,
        input: impl Stream<Item = String> + Send,
        concurrency: usize,
    ) -> impl Stream<Item = Bytes> {
        let storage = self.storage.clone();

        input
            .map(move |id| {
                let storage = storage.clone();
                async move { storage.read(&id).await }
            })
            .buffer_unordered(concurrency)
            .filter_map(|r| async move { r.ok() })
    }
}
