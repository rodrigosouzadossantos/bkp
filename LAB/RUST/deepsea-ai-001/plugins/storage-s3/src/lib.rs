use aws_sdk_s3::{Client};
use tokio::runtime::Runtime;

pub struct S3Store {
  pub bucket: String,
  client: Client,
}

impl S3Store {
  pub fn new(bucket: &str, client: Client) -> Self {
    Self { bucket: bucket.to_string(), client }
  }
  pub fn list(&self, prefix: &str) -> Vec<String> {
    let rt = Runtime::new().unwrap();
    rt.block_on(async {
      let resp = self.client.list_objects_v2()
        .bucket(&self.bucket)
        .prefix(prefix)
        .send()
        .await.unwrap();
      resp.contents.unwrap_or_default()
        .iter()
        .filter_map(|obj| obj.key.clone())
        .collect()
    })
  }
}
