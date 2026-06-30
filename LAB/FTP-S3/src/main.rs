use aws_config::meta::region::RegionProviderChain;
use aws_sdk_s3::{Client, primitives::ByteStream};
use futures::stream::{FuturesUnordered, StreamExt};
use indicatif::{ProgressBar, ProgressStyle};
use std::{path::PathBuf, sync::Arc, time::Instant};
use tokio::fs::File;
use tokio::io::AsyncReadExt;
use tokio::sync::Semaphore;

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    // -----------------------------
    // Configuration
    // -----------------------------
    let bucket = "analise-dados";
    let prefix = "projeto-ia-submarina/ia-frente-ambiental/NOAA-AUV/ESPADARTE/6000702270/";

    // File containing full paths of all images
    let file_list_path = "files.txt";
    let file_list = std::fs::read_to_string(file_list_path)?;
    let paths: Vec<PathBuf> = file_list
        .lines()
        .map(|line| PathBuf::from(line.trim()))
        .collect();

    println!("Found {} files to upload", paths.len());

    // -----------------------------
    // Progress bar setup
    // -----------------------------
    let pb = ProgressBar::new(paths.len() as u64);
    pb.set_style(
        ProgressStyle::default_bar()
            .template("{spinner:.green} [{elapsed_precise}] [{bar:40.cyan/blue}] {pos}/{len} ({eta}) {msg}")
            .unwrap()
            .progress_chars("#>-"),
    );

    // -----------------------------
    // S3 client
    // -----------------------------
    let region_provider = RegionProviderChain::default_provider().or_else("sa-east-1");
    let config = aws_config::from_env().region(region_provider).load().await;
    let client = Client::new(&config);

    // -----------------------------
    // Concurrency control
    // -----------------------------
    let max_concurrency = 500; // adjust based on file size / OS limits
    let semaphore = Arc::new(Semaphore::new(max_concurrency));
    let start = Instant::now();

    let mut handles = FuturesUnordered::new();

    for path in paths.iter() {
        let permit = semaphore.clone().acquire_owned().await.unwrap();
        let client = client.clone();
        let bucket = bucket.to_string();
        let key = format!("{}{}", prefix, path.file_name().unwrap().to_string_lossy());
        let pb = pb.clone();
        let path = path.clone();

        handles.push(tokio::spawn(async move {
            if let Err(e) = upload_file(&client, &bucket, &key, &path).await {
                eprintln!("Failed to upload {}: {}", path.display(), e);
            }
            pb.inc(1);
            drop(permit); // release semaphore
        }));
    }

    // Wait for all tasks to complete
    while let Some(_) = handles.next().await {}

    let elapsed = start.elapsed();
    pb.finish_with_message(
      format!(
        "Finished {} files in {:.2?} ({:.2} files/sec)",
        paths.len(),
        elapsed,
        paths.len() as f64 / elapsed.as_secs_f64()
    ));

    Ok(())
}

async fn upload_file(client: &Client, bucket: &str, key: &str, path: &PathBuf) -> anyhow::Result<()> {
    let mut file = File::open(path).await?;
    let mut buf = Vec::new();
    file.read_to_end(&mut buf).await?;

    let byte_stream = ByteStream::from(buf);
    client.put_object()
        .bucket(bucket)
        .key(key)
        .body(byte_stream)
        .send()
        .await?;

    Ok(())
}
