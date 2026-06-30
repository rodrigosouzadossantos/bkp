use anyhow::Result;
use bytes::Bytes;
use futures::Stream;
use std::pin::Pin;

pub type ImageId = String;

#[async_trait::async_trait]
pub trait Storage: Send + Sync {
    async fn list(
        &self,
        prefix: &str,
    ) -> Result<Pin<Box<dyn Stream<Item = Result<ImageId>> + Send>>>;

    async fn read(&self, id: &ImageId) -> Result<Bytes>;

    async fn read_stream(
        &self,
        id: &ImageId,
    ) -> Result<Pin<Box<dyn Stream<Item = Result<Bytes>> + Send>>>;
}

pub mod local;
pub mod s3;
