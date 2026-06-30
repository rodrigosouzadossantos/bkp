use aws_config::BehaviorVersion;
use aws_sdk_s3::{config::timeout::TimeoutConfig, Client};
use indicatif::{ProgressBar, ProgressStyle};
use std::{sync::Arc, time::Duration};
use tokio::sync::{mpsc, Semaphore};
use async_recursion::async_recursion;

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {

  let timeout_config = TimeoutConfig::builder()
    .connect_timeout(Duration::from_secs(10))
    .read_timeout(Duration::from_secs(10))
    .build();

  let config = aws_config::defaults(BehaviorVersion::latest())
    .timeout_config(timeout_config)
    .load()
    .await;

  let client = Arc::new(Client::new(&config));
  let bucket = Arc::new("analise-dados".to_string());
  let semaphore = Arc::new(Semaphore::new(64));
  let (tx, mut rx) = mpsc::channel::<String>(1_000_000);

  let pb = ProgressBar::new_spinner();
  pb.set_style(
    ProgressStyle::default_spinner()
    .template("{spinner:.green} [{elapsed_precise}] Keys: {pos} ({per_sec})")?
  );

  println!("🚀 Launching Stabilized Recursive Scan...");

  let start = std::time::Instant::now();
  let c = client.clone();
  let b = bucket.clone();
  let t = tx.clone();
  let s = semaphore.clone();

  tokio::spawn(async move {
    recursive_list(
      c,
      b,
      "".to_string(),
      t,
      s
    ).await;
  } );
  drop(tx);

  let mut count = 0;
  while let Some(_key) = rx.recv().await {
    count += 1;
    if count & 0x3FFF == 0 {
      pb.set_position(count);
    }
  }
  pb.finish_with_message("Complete!");

  let duration = start.elapsed();
  println!("\n✅ Done! Total: {} | Time: {:.2?} | Rate: {:.0} keys/s",
    count, duration, count as f64 / duration.as_secs_f64());

  Ok(())
}

#[async_recursion]
async fn recursive_list(
  client: Arc<Client>,
  bucket: Arc<String>,
  prefix: String,
  tx: mpsc::Sender<String>,
  sem: Arc<Semaphore>
) {
  let mut continuation_token: Option<String> = None;

  loop {
    let _permit = sem.acquire().await.expect("Semaphore closed");

    let request = client.list_objects_v2()
      .bucket(bucket.as_str())
      .prefix(&prefix)
      .delimiter("/")
      .set_continuation_token(continuation_token.clone());

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
            let next_p = next_prefix.to_string();

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
