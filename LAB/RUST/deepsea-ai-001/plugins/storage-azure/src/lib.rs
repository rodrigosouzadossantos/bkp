use azure_storage::prelude::*;
use azure_storage_blobs::prelude::*;
use tokio::runtime::Runtime;

pub struct AzureBlobStore {
  pub container: String,
  client: BlobServiceClient,
}

impl AzureBlobStore {
  pub fn new(container: &str, client: BlobServiceClient) -> Self {
    Self { container: container.to_string(), client }
  }
  pub fn list(&self, prefix: &str) -> Vec<String> {
    let rt = Runtime::new().unwrap();
    rt.block_on(async {
      let mut result = vec![];
      let mut stream = self.client.container_client(&self.container).list_blobs().prefix(prefix).into_stream();
      while let Some(blob_list) = stream.next().await {
        let blobs = blob_list.unwrap().blobs.blobs;
        for b in blobs { result.push(b.name); }
      }
      result
    })
  }
}
