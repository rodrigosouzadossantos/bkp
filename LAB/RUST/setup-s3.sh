#!/usr/bin/env bash
set -e

PROJECT_NAME="ps3-rust"

echo "Creating project..."
cargo new $PROJECT_NAME
cd $PROJECT_NAME

cargo add \
  tokio --features "tokio/full" \
  clap --features "clap/derive" \
  aws-config \
  aws-sdk-s3 \
  futures \
  anyhow

mkdir -p src

echo "Writing main.rs..."
cat > src/main.rs << 'EOF'
use aws_sdk_s3::{Client, types::Object};
use clap::Parser;
use tokio::sync::{mpsc, Semaphore};
use std::sync::Arc;
use anyhow::Result;

mod s3_utils;
use s3_utils::*;

const MAX_SEMAPHORE: usize = 50;

#[derive(Parser, Debug)]
#[command(author, version, about)]
struct Args {
    #[arg(long)]
    bucket: String,

    #[arg(long, default_value_t = 500)]
    prefix_count: usize,
}

#[tokio::main]
async fn main() -> Result<()> {
    let args = Args::parse();

    let config = aws_config::load_from_env().await;
    let client = Client::new(&config);

    list_objects_v2(client, args.bucket, args.prefix_count).await?;

    Ok(())
}

async fn list_objects_v2(
    client: Client,
    bucket: String,
    prefix_target: usize,
) -> Result<()> {

    let (tx, mut rx) = mpsc::channel::<Object>(1000);
    let prefixes = Arc::new(tokio::sync::Mutex::new(Vec::new()));

    // prefix discovery
    let discover = {
        let client = client.clone();
        let bucket = bucket.clone();
        let tx = tx.clone();
        let prefixes = prefixes.clone();

        tokio::spawn(async move {
            find_prefixes(client, bucket, "".to_string(), prefix_target, tx, prefixes).await;
        })
    };

    discover.await?;

    let prefixes = prefixes.lock().await.clone();

    let semaphore = Arc::new(Semaphore::new(MAX_SEMAPHORE));
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

    drop(tx);

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
EOF

echo "Writing s3_utils.rs..."
cat > src/s3_utils.rs << 'EOF'
use aws_sdk_s3::{Client, types::Object};
use tokio::sync::mpsc::Sender;
use std::sync::Arc;
use anyhow::{Result, anyhow};
use tokio::time::{sleep, Duration};

const MAX_KEYS: i32 = 1000;

// FULL base36 charset (matches typical Go implementation)
const CHARSET: &[char] = &[
    '0','1','2','3','4','5','6','7','8','9',
    'a','b','c','d','e','f','g','h','i','j',
    'k','l','m','n','o','p','q','r','s','t',
    'u','v','w','x','y','z'
];

pub async fn find_prefixes(
    client: Client,
    bucket: String,
    prefix: String,
    target: usize,
    tx: Sender<Object>,
    prefixes: Arc<tokio::sync::Mutex<Vec<String>>>,
) {
    let mut processed = 0;

    async fn recurse(
        client: Client,
        bucket: String,
        current: String,
        target: usize,
        processed: &mut usize,
        tx: &Sender<Object>,
        prefixes: &Arc<tokio::sync::Mutex<Vec<String>>>,
    ) {
        if *processed >= target {
            prefixes.lock().await.push(current);
            return;
        }

        for c in CHARSET {
            let next = format!("{}{}", current, c);

            let resp = match list_objects_with_backoff(&client, &bucket, &next).await {
                Ok(r) => r,
                Err(_) => continue,
            };

            let count = resp.contents().len();

            if count > 999 {
                *processed += 1;

                recurse(
                    client.clone(),
                    bucket.clone(),
                    next,
                    target,
                    processed,
                    tx,
                    prefixes,
                ).await;

            } else if count > 0 {
                *processed += 1;

                for obj in resp.contents() {
                    let _ = tx.send(obj.clone()).await;
                }
            }
        }
    }

    recurse(
        client,
        bucket,
        prefix,
        target,
        &mut processed,
        &tx,
        &prefixes,
    ).await;
}

pub async fn list_objects_with_backoff(
    client: &Client,
    bucket: &str,
    prefix: &str,
) -> Result<aws_sdk_s3::operation::list_objects_v2::ListObjectsV2Output> {

    let max_retries = 10;

    for i in 0..max_retries {
        let res = client
            .list_objects_v2()
            .bucket(bucket)
            .prefix(prefix)
            .max_keys(MAX_KEYS)
            .send()
            .await;

        match res {
            Ok(output) => return Ok(output),
            Err(e) => {
                let wait = 2u64.pow(i as u32);
                sleep(Duration::from_secs(wait)).await;

                if i == max_retries - 1 {
                    return Err(anyhow!("too many retries: {:?}", e));
                }
            }
        }
    }

    unreachable!()
}

pub async fn list_all_objects(
    client: Client,
    bucket: String,
    prefix: String,
    tx: Sender<Object>,
) -> Result<()> {

    let mut token = None;

    loop {
        let mut req = client
            .list_objects_v2()
            .bucket(&bucket)
            .max_keys(MAX_KEYS);

        if let Some(t) = &token {
            req = req.continuation_token(t);
        }

        if !prefix.is_empty() {
            req = req.prefix(&prefix);
        }

        let resp = req.send().await?;

        for obj in resp.contents() {
            tx.send(obj.clone()).await.ok();
        }

        if resp.is_truncated() {
            token = resp.next_continuation_token().map(|s| s.to_string());
        } else {
            break;
        }
    }

    Ok(())
}
EOF

echo "Done!"
echo ""
echo "Run it like:"
echo "cargo run -- --bucket YOUR_BUCKET_NAME"
