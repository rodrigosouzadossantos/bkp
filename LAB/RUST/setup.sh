#!/usr/bin/env bash

set -e

PROJECT_NAME="img_pipeline"

echo "Creating project: $PROJECT_NAME"

cargo new $PROJECT_NAME
cd $PROJECT_NAME

cargo add \
  tokio --features "tokio/full" \
  tokio-stream --features fs \
  anyhow \
  bytes \
  futures \
  arrow \
  memmap2 \
  async-trait \
  async-stream \
  aws-config \
  aws-sdk-s3

# Create directories
mkdir -p src/storage

# Create files
touch src/dataset.rs
touch src/pipeline.rs
touch src/codec.rs
touch src/arrow.rs
touch src/ml.rs
touch src/storage/mod.rs
touch src/storage/local.rs
touch src/storage/s3.rs

# -------------------------
# main.rs
# -------------------------
cat > src/main.rs <<'EOF'
mod dataset;
mod storage;
mod codec;
mod arrow;
mod ml;

use dataset::Dataset;
use storage::local::LocalFs;
use std::{sync::Arc, path::PathBuf};
use futures::StreamExt;

#[tokio::main]
async fn main() {
    let storage = Arc::new(LocalFs::new(PathBuf::from("./data")));
    let dataset = Dataset::new(storage);

    let ids = dataset.list("").await;

    let images = dataset.load(ids, 128);

    images
        .for_each(|img| async move {
            println!("Loaded {} bytes", img.len());
        })
        .await;
}
EOF

# -------------------------
# dataset.rs
# -------------------------
cat > src/dataset.rs <<'EOF'
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
        input: impl Stream<Item = String> + Send + 'static,
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
EOF

# -------------------------
# storage/mod.rs
# -------------------------
cat > src/storage/mod.rs <<'EOF'
use anyhow::Result;
use bytes::Bytes;
use futures::Stream;

pub type ImageId = String;

#[async_trait::async_trait]
pub trait Storage: Send + Sync {
    async fn list(
        &self,
        prefix: &str,
    ) -> Result<Box<dyn Stream<Item = Result<ImageId>> + Unpin + Send>>;

    async fn read(&self, id: &ImageId) -> Result<Bytes>;

    async fn read_stream(
        &self,
        id: &ImageId,
    ) -> Result<Box<dyn Stream<Item = Result<Bytes>> + Unpin + Send>>;
}

pub mod local;
pub mod s3;
EOF

# -------------------------
# storage/local.rs
# -------------------------
cat > src/storage/local.rs <<'EOF'
use super::*;
use futures::{stream, StreamExt};
use memmap2::Mmap;
use std::{fs::File, path::PathBuf};

pub struct LocalFs {
    root: PathBuf,
}

impl LocalFs {
    pub fn new(root: PathBuf) -> Self {
        Self { root }
    }
}

#[async_trait::async_trait]
impl Storage for LocalFs {
    async fn list(
        &self,
        prefix: &str,
    ) -> Result<Box<dyn futures::Stream<Item = Result<ImageId>> + Unpin + Send>> {
        let root = self.root.join(prefix);
        let entries = tokio::fs::read_dir(root).await?;

        let stream = tokio_stream::wrappers::ReadDirStream::new(entries)
            .filter_map(|e| async move {
                match e {
                    Ok(entry) => {
                        let path = entry.path();
                        if path.is_file() {
                            Some(Ok(path.to_string_lossy().to_string()))
                        } else {
                            None
                        }
                    }
                    Err(e) => Some(Err(e.into())),
                }
            });

        Ok(Box::new(stream))
    }

    async fn read(&self, id: &ImageId) -> Result<Bytes> {
        let data = tokio::fs::read(id).await?;
        Ok(Bytes::from(data))
    }

    async fn read_stream(
        &self,
        id: &ImageId,
    ) -> Result<Box<dyn futures::Stream<Item = Result<Bytes>> + Unpin + Send>> {
        let file = File::open(id)?;
        let mmap = unsafe { Mmap::map(&file)? };
        let bytes = Bytes::from(mmap);

        Ok(Box::new(stream::once(async move { Ok(bytes) })))
    }
}
EOF

# -------------------------
# storage/s3.rs
# -------------------------
cat > src/storage/s3.rs <<'EOF'
use super::*;
use aws_sdk_s3::Client;
use futures::StreamExt;

pub struct S3Storage {
    pub client: Client,
    pub bucket: String,
}

#[async_trait::async_trait]
impl Storage for S3Storage {
    async fn list(
        &self,
        prefix: &str,
    ) -> Result<Box<dyn futures::Stream<Item = Result<ImageId>> + Unpin + Send>> {

        let client = self.client.clone();
        let bucket = self.bucket.clone();
        let prefix = prefix.to_string();

        let stream = async_stream::try_stream! {
            let mut continuation = None;

            loop {
                let mut req = client
                    .list_objects_v2()
                    .bucket(&bucket)
                    .prefix(&prefix);

                if let Some(token) = continuation {
                    req = req.continuation_token(token);
                }

                let resp = req.send().await?;

                if let Some(contents) = resp.contents {
                    for obj in contents {
                        if let Some(key) = obj.key {
                            yield key;
                        }
                    }
                }

                if resp.is_truncated.unwrap_or(false) {
                    continuation = resp.next_continuation_token;
                } else {
                    break;
                }
            }
        };

        Ok(Box::new(stream))
    }

    async fn read(&self, id: &ImageId) -> Result<Bytes> {
        let obj = self.client
            .get_object()
            .bucket(&self.bucket)
            .key(id)
            .send()
            .await?;

        let data = obj.body.collect().await?;
        Ok(data.into_bytes())
    }

    async fn read_stream(
        &self,
        id: &ImageId,
    ) -> Result<Box<dyn futures::Stream<Item = Result<Bytes>> + Unpin + Send>> {

        let obj = self.client
            .get_object()
            .bucket(&self.bucket)
            .key(id)
            .send()
            .await?;

        let stream = obj.body.map(|chunk| {
            chunk.map(|b| b.into_bytes()).map_err(|e| e.into())
        });

        Ok(Box::new(stream))
    }
}
EOF

# -------------------------
# codec.rs
# -------------------------
cat > src/codec.rs <<'EOF'
use bytes::Bytes;

pub struct ImageView {
    pub data: Vec<u8>,
}

pub async fn decode(bytes: Bytes) -> ImageView {
    tokio::task::spawn_blocking(move || {
        ImageView { data: bytes.to_vec() }
    })
    .await
    .unwrap()
}
EOF

# -------------------------
# arrow.rs
# -------------------------
cat > src/arrow.rs <<'EOF'
use arrow::array::BinaryArray;
use arrow::record_batch::RecordBatch;
use std::sync::Arc;

pub fn to_arrow(data: Vec<Vec<u8>>) -> RecordBatch {
    let arr = BinaryArray::from_iter(data.iter().map(|b| Some(b.as_slice())));

    RecordBatch::try_from_iter(vec![
        ("data", Arc::new(arr) as _)
    ]).unwrap()
}
EOF

# -------------------------
# ml.rs
# -------------------------
cat > src/ml.rs <<'EOF'
use crate::codec::ImageView;

pub fn infer(_batch: Vec<ImageView>) {
    // placeholder
}
EOF

echo "Project created successfully!"
echo "Run:"
echo "cd $PROJECT_NAME && cargo run"
