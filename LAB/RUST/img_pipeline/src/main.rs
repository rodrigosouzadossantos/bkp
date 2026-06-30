mod dataset;
mod storage;
mod codec;
mod arrow;
mod ml;

use dataset::Dataset;
use storage::s3::S3Storage;

use std::sync::Arc;
use futures::StreamExt;
use bytes::Bytes;

use aws_config::{
  load_defaults,
  BehaviorVersion,
};
use aws_sdk_s3::Client;

#[tokio::main]
async fn main() -> anyhow::Result<()> {

  let config = load_defaults(BehaviorVersion::latest()).await;
  let client = Client::new(&config);

  let storage = Arc::new(S3Storage {
    client,
    bucket: "analise-dados".to_string(),
  });

  let dataset = Dataset::new(storage);

  let ids = dataset.list(
    //"projeto-ia-submarina/ia-frente-ambiental/NOAA-AUV/VIOLA/6000713538"
    "projeto-ia-submarina/ia-frente-ambiental/NOAA-AUV/ESPADARTE/6000702270/COM20240425"
  ).await.collect::<Vec<String>>().await;

  println!("Found {} images", ids.len());

  //let images = dataset.load(ids, 128);

  //images
  //  .for_each(|img: Bytes| async move {
  //    println!("Loaded {} bytes", img.len());
  //  })
  //.await;

  Ok(())
}
