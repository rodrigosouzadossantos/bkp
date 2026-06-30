use aws_sdk_s3::{Client, types::Object};
use tokio::sync::{mpsc, Semaphore};
use std::sync::Arc;
use anyhow::Result;

mod s3_utils;
use s3_utils::*;

const MAX_SEMAPHORE: usize = 50;
const MAX_KEYS: i32 = 1000;

#[tokio::main]
async fn main() -> Result<()> {
  let bucket = std::env::args().nth(1).expect("bucket required");

  let config = aws_config::load_from_env().await;
  let client = Client::new(&config);

  list_objects_v2(client, bucket, 500).await?;

  Ok(())
}

async fn list_objects_v2(
  client: Client,
  bucket: String,
  prefix_target: usize,
) -> Result<()> {

  let (tx, mut rx) = mpsc::channel::<Object>(1000);

  let prefixes = Arc::new(tokio::sync::Mutex::new(Vec::new()));

  // Spawn prefix discovery
  let client_clone = client.clone();
  let bucket_clone = bucket.clone();
  let tx_clone = tx.clone();
  let prefixes_clone = prefixes.clone();

  let discover = tokio::spawn(async move {
    find_prefixes(
      client_clone,
      bucket_clone,
      "".to_string(),
      prefix_target,
      tx_clone,
      prefixes_clone,
    ).await;
  });

  discover.await?;

  // Parallel listing
  let semaphore = Arc::new(Semaphore::new(MAX_SEMAPHORE));
  let prefixes = prefixes.lock().await.clone();

  let mut handles = vec![];

  for prefix in prefixes {
    let client = client.clone();
    let bucket = bucket.clone();
    let tx = tx.clone();
    let permit = semaphore.clone().acquire_owned().await.unwrap();

    let handle = tokio::spawn(async move {
      let _permit = permit;

      if let Err(e) = list_all_objects(client, bucket, prefix, tx).await {
        eprintln!("error: {:?}", e);
      }
    });

    handles.push(handle);
  }

  drop(tx); // close channel

  // Reader workers
  let reader = tokio::spawn(async move {
    while let Some(obj) = rx.recv().await {
      println!(
        "Object: {:?} {} {:?}",
        obj.last_modified(),
        obj.size(),
        obj.key()
      );
    }
  });

  for h in handles {
    h.await?;
  }

  reader.await?;

  Ok(())
}
