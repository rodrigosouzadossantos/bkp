use aws_sdk_s3::{Client, types::Object};
use tokio::sync::mpsc::Sender;
use std::sync::Arc;
use anyhow::Result;
use tokio::sync::Semaphore;
use futures::stream::{FuturesUnordered, StreamExt};

const MAX_KEYS: i32 = 1000;
const MAX_SEMAPHORE: usize = 50;

//////////////////////////////////////////////////////////////
// PREFIX GENERATION (NOW WITH BASE PREFIX SUPPORT)
//////////////////////////////////////////////////////////////

fn generate_date_prefixes(base_prefix: &str, target: usize) -> Vec<String> {
    let mut prefixes = Vec::new();

    let years = 2020..=2026;

    'outer: for year in years {
        for month in 1..=12 {
            for day in 1..=31 {
                let suffix = format!("FT_{:04}{:02}{:02}", year, month, day);

                let full_prefix = if base_prefix.is_empty() {
                    suffix
                } else {
                    format!("{}{}", base_prefix, suffix)
                };

                prefixes.push(full_prefix);

                if prefixes.len() >= target {
                    break 'outer;
                }
            }
        }
    }

    println!("Generated {} prefixes", prefixes.len());
    prefixes
}

//////////////////////////////////////////////////////////////
// MAIN ENTRY (UPDATED)
//////////////////////////////////////////////////////////////

pub async fn run_parallel_listing(
    client: Client,
    bucket: String,
    base_prefix: String,
    target: usize,
    tx: Sender<Object>,
) -> Result<()> {

    let prefixes = generate_date_prefixes(&base_prefix, target);

    let semaphore = Arc::new(Semaphore::new(MAX_SEMAPHORE));
    let mut futures = FuturesUnordered::new();

    for prefix in prefixes {
      println!("Listing prefix: {}", prefix);

        let client = client.clone();
        let bucket = bucket.clone();
        let tx = tx.clone();
        let sem = semaphore.clone();

        futures.push(tokio::spawn(async move {
            let _permit = sem.acquire().await.unwrap();

            if let Err(e) = list_all_objects(client, bucket, prefix, tx).await {
                eprintln!("error: {:?}", e);
            }
        }));
    }

    while let Some(_) = futures.next().await {}

    Ok(())
}

//////////////////////////////////////////////////////////////
// S3 LIST (WITH PAGINATION)
//////////////////////////////////////////////////////////////

pub async fn list_all_objects(
    client: Client,
    bucket: String,
    prefix: String,
    tx: Sender<Object>,
) -> Result<()> {

    let mut token = None;

    println!("Fetching objects for prefix: {}", prefix);

    loop {
        let mut req = client
            .list_objects_v2()
            .bucket(&bucket)
            .max_keys(MAX_KEYS)
            .prefix(&prefix);

        if let Some(t) = &token {
            req = req.continuation_token(t);
        }

        let resp = req.send().await?;

        for obj in resp.contents() {
            let _ = tx.send(obj.clone()).await;
        }

        if resp.is_truncated().unwrap_or(false) {
            token = resp.next_continuation_token().map(|s| s.to_string());
        } else {
            break;
        }
    }

    Ok(())
}
