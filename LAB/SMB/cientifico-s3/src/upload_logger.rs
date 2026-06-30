use chrono::Local;
use serde::{Deserialize, Serialize};
use std::fs::OpenOptions;
use std::io::Write;
use std::sync::Arc;
use tokio::sync::Mutex;

#[derive(Debug, Serialize, Deserialize)]
pub struct UploadLogEntry {
  pub timestamp: String,
  pub status: String,
  pub smb_path: String,
  pub s3_path: String,
  pub size_bytes: u64,
  pub size_human: String,
  pub error_message: Option<String>,
}

pub struct UploadLogger {
  file: Arc<Mutex<std::fs::File>>,
}

impl UploadLogger {
  pub fn new(log_path: &str) -> std::io::Result<Self> {
    let file = OpenOptions::new()
      .create(true)
      .append(true)
      .open(log_path)?;

    Ok(Self {
      file: Arc::new(Mutex::new(file)),
    })
  }

  pub async fn log_upload(&self, entry: UploadLogEntry) {
    let mut file = self.file.lock().await;
    let json = serde_json::to_string(&entry).unwrap_or_else(|_| "{}".to_string());
    let _ = writeln!(file, "{}", json);
  }

  pub async fn log_success(&self, smb_path: String, s3_path: String, size: u64) {
    let entry = UploadLogEntry {
      timestamp: Local::now().format("%Y-%m-%d %H:%M:%S").to_string(),
      status: "SUCCESS".to_string(),
      smb_path,
      s3_path,
      size_bytes: size,
      size_human: format_size(size),
      error_message: None,
    };
    self.log_upload(entry).await;
  }

  pub async fn log_skip(&self, smb_path: String, s3_path: String) {
    let entry = UploadLogEntry {
      timestamp: Local::now().format("%Y-%m-%d %H:%M:%S").to_string(),
      status: "SKIPPED".to_string(),
      smb_path,
      s3_path,
      size_bytes: 0,
      size_human: "N/A".to_string(),
      error_message: Some("File already exists in S3".to_string()),
    };
    self.log_upload(entry).await;
  }

  pub async fn log_error(&self, smb_path: String, s3_path: String, error: String) {
    let entry = UploadLogEntry {
      timestamp: Local::now().format("%Y-%m-%d %H:%M:%S").to_string(),
      status: "FAILED".to_string(),
      smb_path,
      s3_path,
      size_bytes: 0,
      size_human: "N/A".to_string(),
      error_message: Some(error),
    };
    self.log_upload(entry).await;
  }
}

fn format_size(bytes: u64) -> String {
  const KB: u64 = 1024;
  const MB: u64 = KB * 1024;
  const GB: u64 = MB * 1024;
  const TB: u64 = GB * 1024;

  if bytes >= TB {
    format!("{:.2} TB", bytes as f64 / TB as f64)
  } else if bytes >= GB {
    format!("{:.2} GB", bytes as f64 / GB as f64)
  } else if bytes >= MB {
    format!("{:.2} MB", bytes as f64 / MB as f64)
  } else if bytes >= KB {
    format!("{:.2} KB", bytes as f64 / KB as f64)
  } else {
    format!("{} bytes", bytes)
  }
}
