use tokio::runtime::Runtime;

use aws_sdk_s3::Client;
use aws_sdk_s3::primitives::ByteStream;

use pyo3::prelude::*;

use crate::trait_def::StorageConnector;

pub struct S3Connector {
  client: Client,
  bucket: String,
  rt: Runtime,
}

impl S3Connector {
  pub fn new(bucket: String) -> PyResult<Self> {
    let rt = Runtime::new().unwrap();

    let client = rt.block_on(async {
      let config = aws_config::load_defaults(
        aws_config::BehaviorVersion::latest(),
      ).await;
      Client::new(&config)
    });
    Ok(Self { client, bucket, rt })
  }
}

impl StorageConnector for S3Connector {
  fn write(&self, path: &str, data: Vec<u8>) -> PyResult<()> {
    self.rt.block_on(async {
      self.client.put_object()
        .bucket(&self.bucket)
        .key(path)
        .body(ByteStream::from(data))
        .send()
        .await
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))
    })?;
    Ok(())
  }

  fn read(&self, path: &str) -> PyResult<Vec<u8>> {
    self.rt.block_on(async {
      let resp = self.client.get_object()
        .bucket(&self.bucket)
        .key(path)
        .send()
        .await
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyIOError, _>(e.to_string()))?;

      let data = resp.body.collect().await
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyIOError, _>(e.to_string()))?;
      Ok(data.into_bytes().to_vec())
    })
  }
}

