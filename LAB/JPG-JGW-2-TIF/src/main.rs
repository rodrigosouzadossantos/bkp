use anyhow::Result;
use aws_sdk_s3::{Client, types::{CompletedMultipartUpload, CompletedPart}};
use rayon::prelude::*;
use std::process::{Command, Stdio};
use std::io::{Read};
use std::sync::Arc;
use tokio::runtime::Runtime;

const BUCKET: &str = "analise-dados";
const PREFIX: &str = "projeto-ia-submarina/ia-frente-ambiental/NOAA-AUV/VIOLA/6000713538/";
const PART_SIZE: usize = 8 * 1024 * 1024; // 8MB for S3 multipart

#[tokio::main]
async fn main() -> Result<()> {
    // Load AWS config
    let config = aws_config::load_from_env().await;
    let s3_client = Arc::new(Client::new(&config));

    // List all JPG files from S3
    let files = list_jpg_files(&s3_client, BUCKET, PREFIX).await?;
    println!("Found {} JPG files", files.len());

    // Chunk files to avoid too many simultaneous GDAL pipelines
    let chunk_size = 50; // tune based on memory/network
    let chunks: Vec<Vec<String>> = files.chunks(chunk_size).map(|c| c.to_vec()).collect();

    // Initialize Rayon
    rayon::ThreadPoolBuilder::new()
        .num_threads(num_cpus::get())
        .build_global()
        .unwrap();

    // Process chunks in parallel
    chunks.par_iter().for_each(|chunk| {
        let s3 = Arc::clone(&s3_client);
        let chunk = chunk.clone();
        let rt = Runtime::new().unwrap();

        rt.block_on(async move {
            // Generate unique output key
            let output_key = format!("processed/{}.tif", uuid::Uuid::new_v4());
            match process_and_upload(&s3, &chunk, BUCKET, &output_key).await {
                Ok(_) => println!("✅ Uploaded {}", output_key),
                Err(e) => eprintln!("❌ Failed {}: {:?}", output_key, e),
            }
        });
    });

    Ok(())
}

// -------------------------
// List JPG files in S3
// -------------------------
async fn list_jpg_files(s3: &Client, bucket: &str, prefix: &str) -> Result<Vec<String>> {
    let mut files = Vec::new();
    let mut paginator = s3.list_objects_v2()
        .bucket(bucket)
        .prefix(prefix)
        .into_paginator()
        .send();

    use futures::StreamExt;
    while let Some(page) = paginator.next().await {
        let page = page?;
        for obj in page.contents().unwrap_or_default() {
            let key = obj.key().unwrap();
            if key.ends_with(".jpg") {
                files.push(key.to_string());
            }
        }
    }

    Ok(files)
}

// -------------------------
// Process chunk: build VRT + warp + stream upload
// -------------------------
async fn process_and_upload(
    s3: &Client,
    files: &[String],
    bucket: &str,
    output_key: &str,
) -> Result<()> {
    // Run gdalbuildvrt → gdalwarp pipeline
    let mut stdout = process_chunk(files)?;

    // Upload the resulting GeoTIFF to S3
    upload_stream(s3, bucket, output_key, &mut stdout).await
}

// -------------------------
// Build GDAL pipeline streaming from /vsis3/ without disk
// -------------------------
fn process_chunk(files: &[String]) -> Result<std::process::ChildStdout> {
    let bucket = BUCKET;

    // Prepare gdalbuildvrt command
    let mut vrt_args = vec!["/vsistdout/".to_string()]; // output to stdout
    for key in files {
        vrt_args.push(format!("/vsis3/{}/{}", bucket, key));
    }

    let mut vrt_child = Command::new("gdalbuildvrt")
        .args(&vrt_args)
        .stdout(Stdio::piped())
        .spawn()?;

    // Prepare gdalwarp reading from stdin (VRT) and writing to stdout
    let mut warp_child = Command::new("gdalwarp")
        .args([
            "-of", "GTiff",
            "-t_srs", "EPSG:4326",
            "-r", "bilinear",
            "-co", "COMPRESS=LZW",
            "-co", "TILED=YES",
            "/vsistdin/",
            "/vsistdout/",
        ])
        .stdin(vrt_child.stdout.take().unwrap())
        .stdout(Stdio::piped())
        .spawn()?;

    Ok(warp_child.stdout.take().unwrap())
}

// -------------------------
// Multipart upload streaming
// -------------------------
async fn upload_stream(
    s3: &Client,
    bucket: &str,
    key: &str,
    reader: &mut impl Read,
) -> Result<()> {
    use std::io::BufReader;
    let buffer = BufReader::new(reader);

    // 1️⃣ Create multipart upload
    let create_resp = s3.create_multipart_upload()
        .bucket(bucket)
        .key(key)
        .send()
        .await?;
    let upload_id = create_resp.upload_id().unwrap();

    let mut completed_parts = Vec::new();
    let mut part_number = 1;
    let mut buf = vec![0u8; PART_SIZE];
    let mut buf_reader = buffer;

    loop {
        let n = buf_reader.read(&mut buf)?;
        if n == 0 { break; }

        let mut chunk = buf[..n].to_vec();

        // 2️⃣ Upload part
        let resp = s3.upload_part()
            .bucket(bucket)
            .key(key)
            .upload_id(upload_id)
            .part_number(part_number)
            .body(chunk.into())
            .send()
            .await?;
        let etag = resp.e_tag().unwrap().to_string();

        completed_parts.push(
            CompletedPart::builder()
                .set_e_tag(Some(etag))
                .part_number(part_number)
                .build()
        );

        part_number += 1;
    }

    // 3️⃣ Complete multipart upload
    let completed = CompletedMultipartUpload::builder()
        .set_parts(Some(completed_parts))
        .build();

    s3.complete_multipart_upload()
        .bucket(bucket)
        .key(key)
        .upload_id(upload_id)
        .multipart_upload(completed)
        .send()
        .await?;

    Ok(())
}
