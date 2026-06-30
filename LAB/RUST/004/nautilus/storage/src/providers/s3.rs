use crate::providers::StorageProvider;

use aws_config::meta::region::RegionProviderChain;
use aws_sdk_s3::{config::timeout::TimeoutConfig, Client, types::Object};

use std::{sync::Arc, time::Duration};

use tokio::runtime::Runtime;
use tokio::sync::{mpsc, Semaphore};

use async_recursion::async_recursion;

use indicatif::{ProgressBar, ProgressStyle};


//////////////////////////////////////////////////////
// S3 PROVIDER
//////////////////////////////////////////////////////

pub struct S3Provider {
    client: Arc<Client>,
    rt: Arc<Runtime>,
}

impl S3Provider {

  pub fn new() -> Self {

    // Tokio runtime (shared)
    let rt = Runtime::new().expect("Failed to create Tokio runtime");

    // Load AWS config (env, profile, IAM, etc.)
    let config = rt.block_on(async {
      let timeout_config = TimeoutConfig::builder()
        .connect_timeout(Duration::from_secs(10))
        .read_timeout(Duration::from_secs(10))
        .build();

      let region_provider = RegionProviderChain::default_provider()
        .or_else("us-east-1");

      aws_config::defaults(
        aws_config::BehaviorVersion::latest()
      )
        .region(region_provider)
        .timeout_config(timeout_config)
        .load()
        .await
    });

    let client = Client::new(&config);

    Self {
      client: Arc::new(client),
      rt: Arc::new(rt),
    }
  }
}

//////////////////////////////////////////////////////
// TRAIT IMPLEMENTATION
//////////////////////////////////////////////////////

impl StorageProvider for S3Provider {

  fn name(&self) -> &'static str {
    "s3"
  }

  fn roots(&self) -> Vec<String> {

    // In real system → load from config
    vec![
      "s3://analise-dados".to_string()
    ]
  }

  fn list(&self, path: &str) -> Vec<String> {

    println!("Listing S3 path: {}", path);

    let (bucket, prefix) = parse_s3_path(path);
    let bucket = Arc::new(bucket);
    let prefix = Arc::new(prefix);

    let mut results = Vec::new();

    #[tokio::main]
    async fn list_help(
      client: Arc<Client>,
      bucket: Arc<String>,
      prefix: Arc<Option<String>>,
      results: &mut Vec<String> ) -> Result<(), Box<dyn std::error::Error>> {

      let semaphore = Arc::new(Semaphore::new(64));
      let (tx, mut rx) = mpsc::channel::<String>(500_000);

      let pb = ProgressBar::new_spinner();
      pb.set_style(
        ProgressStyle::default_spinner()
        .template("{spinner:.green} [{elapsed_precise}] Keys: {pos} ({per_sec})")?
      );

      println!("Launching Stabilized Recursive Scan...");

      let start = std::time::Instant::now();

      let c = client.clone();
      let b = bucket.clone();
      let p = prefix.clone();

      let t = tx.clone();
      let s = semaphore.clone();

      tokio::spawn(async move {
        recursive_list(
          c,
          b,
          p,
          t,
          s
        ).await;
      } );
      drop(tx);

      let mut count = 0;
      while let Some(_key) = rx.recv().await {
        count += 1;
        results.push( _key );
        if count & 0x3FFF == 0 {
          pb.set_position(count);
        }
      }
      pb.finish_with_message("Complete!");

      let duration = start.elapsed();
      println!("\nDone! Total: {} | Time: {:.2?} | Rate: {:.0} keys/s",
        count, duration, count as f64 / duration.as_secs_f64());

      Ok(())
    }

    #[async_recursion]
    async fn recursive_list(
      client: Arc<Client>,
      bucket: Arc<String>,
      prefix: Arc<Option<String>>,
      tx: mpsc::Sender<String>,
      sem: Arc<Semaphore>
    ) {
      let mut continuation_token: Option<String> = None;

      loop {
        let _permit = sem.acquire()
                          .await
                          .expect("Semaphore closed");

        let mut request = client.list_objects_v2()
          .bucket(bucket.as_str())
          .delimiter("/")
          .set_continuation_token(
            continuation_token.clone()
          );

        if let Some(p) = prefix.as_deref() {
          request = request.prefix(p);
        }

        match request.send().await {
          Ok(output) => {

            drop(_permit);

            for obj in output.contents() {
              if let Some(key) = obj.key() {
                let _ = tx.send(
                  key.to_string()
                ).await;
              }
            }

            for cp in output.common_prefixes() {
              if let Some(next_prefix) = cp.prefix() {
                let c_c = client.clone();
                let b_c = bucket.clone();
                let t_c = tx.clone();
                let s_c = sem.clone();

                let next_p = Arc::new(Some(next_prefix.to_string()));

                tokio::spawn(async move {
                  recursive_list(c_c, b_c, next_p, t_c, s_c).await;
                });
              }
            }

            if let Some(token) = output.next_continuation_token() {
              continuation_token = Some(token.to_string());
            } else {
              break;
            }
          }

          Err(_e) => {
            break;
          }
        }
      }
    }

    let _ = list_help(
      self.client.clone(),
      bucket,
      prefix,
      &mut results,
    );

    results
  }

  fn read(&self, path: &str) -> Vec<u8> {

    let (bucket, key) = parse_s3_path(path);

    let client = self.client.clone();
    let rt = self.rt.clone();

    rt.block_on(async {

      let resp = client
        .get_object()
        .bucket(bucket)
        .key(key.expect("S3 key ausente"))
        .send()
        .await
        .expect("S3 get_object failed");

      let data = resp.body
        .collect()
        .await
        .expect("read body");

      data.into_bytes().to_vec()
    })
  }
}

//////////////////////////////////////////////////////
// HELPERS
//////////////////////////////////////////////////////

fn parse_s3_path(path: &str) -> (String, Option<String>) {

    // "s3://bucket/prefix"
    let stripped = path.strip_prefix("s3://")
        .expect("Invalid S3 path");

    let mut parts = stripped.splitn(2, '/');

    let bucket = parts.next().unwrap().to_string();
    let prefix = parts.next();

    let prefix = match prefix {
        Some("") | None => None,
        Some(s) => Some(s.to_string()),
    };

    (bucket, prefix)
}

fn object_to_path(bucket: &str) -> impl Fn(&Object) -> String + '_ {

    move |obj: &Object| {

        let key = obj.key().unwrap_or_default();

        format!("s3://{}/{}", bucket, key)
    }
}

async fn list_prefix(
    client: Client,
    bucket: String,
    prefix: String,
) -> (String, Vec<String>) {
    let mut keys = Vec::new();

    if let Ok(output) = client
        .list_objects_v2()
        .bucket(bucket)
        .prefix(&prefix)
        .send()
        .await
    {
        for obj in output.contents() {
            if let Some(key) = obj.key() {
                keys.push(key.to_string());
            }
        }
    }

    (prefix, keys)
}
