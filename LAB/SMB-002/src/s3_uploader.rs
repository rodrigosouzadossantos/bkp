use aws_sdk_s3::Client;
use aws_sdk_s3::primitives::ByteStream;
use indicatif::{ProgressBar, ProgressStyle, MultiProgress};
use std::sync::Arc;
use tokio::sync::mpsc;
use tokio::time::{timeout, Duration};
use crate::upload_logger::UploadLogger;
use chrono::{DateTime, Local};

pub struct S3Config {
  pub bucket: String,
  pub prefix: Option<String>,
  pub region: String,
}

pub struct UploadConfig {
  pub max_concurrent: usize,
  #[allow(dead_code)]
  pub chunk_size: usize,
  pub skip_existing: bool,
  pub smb_timeout: Duration,
  pub s3_upload_timeout: Duration,
  pub s3_check_timeout: Duration,
  pub max_retries: u32,
  pub retry_backoff: Duration,
  pub exponential_backoff: bool,
}

pub struct S3Uploader {
  client: Client,
  pub s3_config: S3Config,
  pub upload_config: UploadConfig,
}

impl S3Uploader {
  pub async fn new(s3_config: S3Config, upload_config: UploadConfig) -> Self {
    let config = aws_config::defaults(aws_config::BehaviorVersion::latest())
      .region(aws_sdk_s3::config::Region::new(s3_config.region.clone()))
      .load()
      .await;

    let client = Client::new(&config);

    Self {
      client,
      s3_config,
      upload_config,
    }
  }

  pub async fn file_exists(&self, key: &str) -> bool {
    // Adicionar timeout
    let check_future = self.client
      .head_object()
      .bucket(&self.s3_config.bucket)
      .key(key)
      .send();

    match timeout(self.upload_config.s3_check_timeout, check_future)
      .await {
        Ok(Ok(_)) => true,
        Ok(Err(_)) => false,
        Err(_) => {
          eprintln!("⏱️ Timeout checking S3 existence: {}", key);
          false
        }
      }
  }

  pub async fn upload_file(
    &self,
    key: String,
    data: Vec<u8>,
  ) -> Result<(), Box<dyn std::error::Error + Send + Sync>> {
    let body = ByteStream::from(data);

    // Adicionar timeout
    let upload_future = self.client
      .put_object()
      .bucket(&self.s3_config.bucket)
      .key(&key)
      .body(body)
      .send();

    match timeout(self.upload_config.s3_upload_timeout, upload_future)
      .await {
        Ok(Ok(_)) => Ok(()),
        Ok(Err(e)) => Err(Box::new(e)),
        Err(_) => Err("S3 upload timeout".into()),
      }
  }

  pub fn get_s3_key(&self, directory: &str, filename: &str) -> String {
    let mut key = String::new();

    if let Some(prefix) = &self.s3_config.prefix {
      key.push_str(prefix);
      if !prefix.ends_with('/') {
        key.push('/');
      }
    }

    key.push_str(directory);
    key.push('/');
    key.push_str(filename);

    key
  }
}

async fn retry_with_backoff<F, Fut, T, E>(
  operation: F,
  max_attempts: u32,
  base_backoff: Duration,
  exponential: bool,
  operation_name: &str,
) -> Result<T, E>
where
  F: Fn() -> Fut,
  Fut: std::future::Future<Output = Result<T, E>>,
  E: std::fmt::Display,
{
  let mut attempt = 0;
  loop {
    attempt += 1;

    match operation().await {
      Ok(result) => return Ok(result),
      Err(e) if attempt >= max_attempts => {
        eprintln!("❌ {} falhou após {} tentativas: {}", operation_name, max_attempts, e);
        return Err(e);
      },
      Err(e) => {
        let wait_time = if exponential {
          base_backoff * 2_u32.pow(attempt - 1)
        } else {
          base_backoff
        };

        eprintln!(
          "⚠️ {} falhou (tentativa {}/{}): {}. Aguardando {:?}...",
          operation_name, attempt, max_attempts, e, wait_time
        );

        tokio::time::sleep(wait_time).await;
      }
    }
  }
}

pub struct UploadStats {
  pub total_files: usize,
  pub uploaded: usize,
  pub skipped: usize,
  pub failed: usize,
  pub total_bytes: u64,
  pub start_time: DateTime<Local>,
  pub end_time: DateTime<Local>,
}

enum WorkerResult {
  Uploaded(u64, String, String),
  Skipped(String, String),
  Failed(String, String, String),
}

pub async fn upload_files_with_workers<F, Fut>(
  uploader: Arc<S3Uploader>,
  files: Vec<(String, String)>,
  read_file_fn: F,
) -> UploadStats
where
  F: Fn(String) -> Fut + Send + Sync + Clone + 'static,
  Fut: std::future::Future<Output = Result<Vec<u8>, String>> + Send + 'static,
{
  let total_files = files.len();
  let num_workers = uploader.upload_config.max_concurrent;

  let log_file = format!("upload_{}.jsonl", 
    chrono::Local::now().format("%Y%m%d_%H%M%S"));
  let logger = Arc::new(UploadLogger::new(&log_file).expect("Failed to create log file"));

  println!("📝 Log: {}\n", log_file);

  let start_time = chrono::Local::now();
  let start_str = start_time.format("%Y-%m-%d %H:%M:%S").to_string();

  let multi_progress = MultiProgress::new();

  let header_pb = multi_progress.add(ProgressBar::new(0));
  header_pb.set_style(
    ProgressStyle::default_bar()
    .template(&format!("🕐 Início: {} | Atual: {{msg}}", start_str))
    .unwrap()
  );

  let main_pb = multi_progress.add(ProgressBar::new(total_files as u64));
  main_pb.set_style(
    ProgressStyle::default_bar()
    .template("{spinner:.green} [{elapsed_precise}] [{bar:40.cyan/blue}] {pos}/{len} ({per_sec}) ETA: {eta}")
    .unwrap()
    .progress_chars("#>-")
  );

  let stats_pb = multi_progress.add(ProgressBar::new(0));
  stats_pb.set_style(
    ProgressStyle::default_bar()
    .template("✅ {pos} uploaded | ⏭️  {len} skipped | ❌ {msg} failed | 📦 {prefix}")
    .unwrap()
  );

  let header_pb_clone = header_pb.clone();
  let update_time_handle = tokio::spawn(async move {
    loop {
      let current = chrono::Local::now();
      let current_str = current.format("%Y-%m-%d %H:%M:%S").to_string();
      header_pb_clone.set_message(current_str);
      tokio::time::sleep(tokio::time::Duration::from_secs(1)).await;
    }
  });

  let files_queue = Arc::new(tokio::sync::Mutex::new(files.into_iter()));
  let (result_tx, mut result_rx) = mpsc::channel::<WorkerResult>(num_workers * 2);

  let mut worker_handles = vec![];
  for worker_id in 0..num_workers {
    let uploader = uploader.clone();
    let read_fn = read_file_fn.clone();
    let queue = files_queue.clone();
    let tx = result_tx.clone();
    let worker_pb = multi_progress.add(ProgressBar::new_spinner());
    worker_pb.set_style(
      ProgressStyle::default_spinner()
      .template(&format!("{{spinner}} Worker {:02}: {{msg}}", worker_id))
      .unwrap()
    );

    let bucket = uploader.s3_config.bucket.clone();

    let handle = tokio::spawn(async move {
      worker_pb.set_message("Starting");

      loop {
        let next_file = {
          let mut queue_lock = queue.lock().await;
          queue_lock.next()
        };

        let Some((smb_url, s3_key)) = next_file else {
          break;
        };

        let full_s3_path = format!("s3://{}/{}", bucket, s3_key);
        worker_pb.set_message(format!("{}", full_s3_path));

        // Processar com retry
        let max_retries = uploader.upload_config.max_retries;
        let retry_backoff = uploader.upload_config.retry_backoff;
        let exponential = uploader.upload_config.exponential_backoff;
        let smb_timeout = uploader.upload_config.smb_timeout;

        let final_result = retry_with_backoff(
          || async {
            // 1. Check S3 existence (com timeout)
            if uploader.upload_config.skip_existing {
              if uploader.file_exists(&s3_key).await {
                return Ok(WorkerResult::Skipped(smb_url.clone(), full_s3_path.clone()));
              }
            }

            // 2. Read SMB (com timeout)
            let smb_url_clone = smb_url.clone();
            let read_fn_clone = read_fn.clone();

            let read_future = read_fn_clone(smb_url_clone.clone());
            let data = match timeout(smb_timeout, read_future).await {
              Ok(Ok(d)) => d,
              Ok(Err(e)) => {
                return Err(format!("SMB read error: {}", e));
              },
              Err(_) => {
                return Err(format!("SMB read timeout after {:?}", smb_timeout));
              }
            };

            let size = data.len() as u64;

            // Validações
            if size == 0 {
              return Err("Arquivo vazio (0 bytes)".to_string());
            }

            let all_zeros = data.iter().all(|&b| b == 0);
            if all_zeros {
              return Err(format!("Arquivo contém apenas zeros ({} bytes)", size));
            }

            // 3. Upload S3 (já tem timeout interno)
            match uploader.upload_file(s3_key.clone(), data).await {
              Ok(_) => Ok(WorkerResult::Uploaded(size, smb_url_clone, full_s3_path.clone())),
              Err(e) => Err(format!("S3 upload error: {}", e)),
            }
          },
          max_retries,
          retry_backoff,
          exponential,
          &format!("Worker {} - {}", worker_id, full_s3_path),
          ).await;

        let result = match final_result {
          Ok(r) => r,
          Err(e) => WorkerResult::Failed(smb_url, full_s3_path, e),
        };

        let _ = tx.send(result).await;
      }

      worker_pb.finish_with_message("Done");
    });

    worker_handles.push(handle);
  }

  drop(result_tx);

  let logger_clone = logger.clone();
  let stats_handle = tokio::spawn(async move {
    let mut stats = UploadStats {
      total_files,
      uploaded: 0,
      skipped: 0,
      failed: 0,
      total_bytes: 0,
      start_time,
      end_time: chrono::Local::now(), // será atualizado
    };

    while let Some(result) = result_rx.recv().await {
      match result {
        WorkerResult::Uploaded(bytes, smb_path, s3_path) => {
          stats.uploaded += 1;
          stats.total_bytes += bytes;
          stats_pb.inc(1);
          stats_pb.set_prefix(format!("{:.2} MB", stats.total_bytes as f64 / 1024.0 / 1024.0));
          logger_clone.log_success(smb_path, s3_path, bytes).await;
        },
        WorkerResult::Skipped(smb_path, s3_path) => {
          stats.skipped += 1;
          stats_pb.set_length(stats.skipped as u64);
          logger_clone.log_skip(smb_path, s3_path).await;
        },
        WorkerResult::Failed(smb_path, s3_path, error) => {
          stats.failed += 1;
          stats_pb.set_message(format!("{}", stats.failed));
          logger_clone.log_error(smb_path.clone(), s3_path.clone(), error.clone()).await;
          eprintln!("❌ {}: {} -> {}", error, smb_path, s3_path);
        },
      }
      main_pb.inc(1);
    }

    stats.end_time = chrono::Local::now();

    main_pb.finish_with_message("✅ Concluído");
    stats_pb.finish();

    stats
  });

  for handle in worker_handles {
    let _ = handle.await;
  }

  let stats = stats_handle.await.unwrap();

  update_time_handle.abort();

  let duration = stats.end_time.signed_duration_since(stats.start_time);
  header_pb.finish_with_message(format!(
      "Final: {} | Duração: {}h {}m {}s",
      stats.end_time.format("%Y-%m-%d %H:%M:%S"),
      duration.num_hours(),
      duration.num_minutes() % 60,
      duration.num_seconds() % 60
  ));

  stats
}
