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

    #[arg(long)]
    prefix: String,

    #[arg(long, default_value_t = 5)]
    prefix_count: usize,
}

#[tokio::main]
async fn main() -> Result<()> {
    let args = Args::parse();

    let config = aws_config::load_defaults(aws_config::BehaviorVersion::latest()).await;
    let client = Client::new(&config);

    list_objects_v2(client, args.bucket, args.prefix, args.prefix_count).await?;

    Ok(())
}

async fn list_objects_v2(
    client: Client,
    bucket: String,
    prefix: String,
    prefix_target: usize,
) -> Result<()> {

    let (tx, mut rx) = mpsc::channel::<Object>(1000);
    let prefixes = Arc::new(tokio::sync::Mutex::new(Vec::new()));

    // prefix discovery
    let discover = {
        let client = client.clone();
        let bucket = bucket.clone();
        let prefix = prefix.clone();
        let tx = tx.clone();

        tokio::spawn(async move {
            run_parallel_listing(client, bucket, prefix, prefix_target, tx).await;
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
                obj.size().unwrap_or(0),
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
