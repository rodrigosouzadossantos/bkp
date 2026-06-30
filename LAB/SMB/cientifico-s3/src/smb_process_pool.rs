use std::process::{Child, Command, Stdio};
use std::io::{Write, Read};
use std::sync::Arc;
use tokio::sync::{Semaphore, Mutex};

pub struct SmbWorkerPool {
  workers: Vec<Arc<Mutex<SmbWorker>>>,
  semaphore: Arc<Semaphore>,
}

struct SmbWorker {
  process: Child,
}

impl SmbWorkerPool {
  pub fn new(size: usize, use_kerberos: bool, username: Option<String>, password: Option<String>) -> Self {
    let mut workers = Vec::new();

    for worker_id in 0..size {
      let mut cmd = Command::new("./target/release/smb-worker");
      cmd.stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped());

      if use_kerberos {
        cmd.env("SMB_USE_KERBEROS", "1");
        if let Ok(ccname) = std::env::var("KRB5CCNAME") {
          cmd.env("KRB5CCNAME", ccname);
        }
      } else {
        cmd.env("SMB_USE_KERBEROS", "0");
        if let Some(ref user) = username {
          cmd.env("SMB_USERNAME", user);
        }
        if let Some(ref pass) = password {
          cmd.env("SMB_PASSWORD", pass);
        }
      }

      match cmd.spawn() {
        Ok(process) => {
          workers.push(Arc::new(Mutex::new(SmbWorker { process })));
        },
        Err(e) => {
          eprintln!("❌ Failed to spawn worker {}: {}", worker_id, e);
          panic!("Cannot start worker pool");
        }
      }
    }

    Self {
      workers,
      semaphore: Arc::new(Semaphore::new(size)),
    }
  }

  pub async fn read_file(&self, url: String) -> Result<Vec<u8>, String> {
    let permit = self.semaphore.acquire().await.unwrap();

    let worker_idx = {
      use std::collections::hash_map::DefaultHasher;
      use std::hash::{Hash, Hasher};
      let mut hasher = DefaultHasher::new();
      url.hash(&mut hasher);
      hasher.finish() as usize % self.workers.len()
    };

    let worker = self.workers[worker_idx].clone();

    let result = tokio::task::spawn_blocking(move || {
      let mut worker_lock = worker.blocking_lock();
      Self::communicate_with_worker(&mut worker_lock, &url)
    })
    .await
      .map_err(|e| e.to_string())??;

    drop(permit);
    Ok(result)
  }

  fn communicate_with_worker(worker: &mut SmbWorker, url: &str) -> Result<Vec<u8>, String> {
    let url_bytes = url.as_bytes();
    let url_size = url_bytes.len() as u32;

    let stdin = worker.process.stdin.as_mut()
      .ok_or("stdin not available")?;

    stdin.write_all(&url_size.to_le_bytes())
      .map_err(|e| format!("stdin write size: {}", e))?;
    stdin.write_all(url_bytes)
      .map_err(|e| format!("stdin write url: {}", e))?;
    stdin.flush()
      .map_err(|e| format!("stdin flush: {}", e))?;

    let stdout = worker.process.stdout.as_mut()
      .ok_or("stdout not available")?;

    let mut status_buf = [0u8; 1];
    stdout.read_exact(&mut status_buf)
      .map_err(|e| format!("stdout read status: {}", e))?;

    if status_buf[0] == 0 {
      return Err("Worker failed to read file".to_string());
    }

    let mut size_buf = [0u8; 8];
    stdout.read_exact(&mut size_buf)
      .map_err(|e| format!("stdout read size: {}", e))?;

    let size = u64::from_le_bytes(size_buf) as usize;

    if size == 0 {
      return Err("File is empty (0 bytes)".to_string());
    }

    if size > 100_000_000 {
      return Err(format!("File too large: {:.2} MB", size as f64 / 1024.0 / 1024.0));
    }

    let mut data = vec![0u8; size];
    stdout.read_exact(&mut data)
      .map_err(|e| format!("stdout read data: {}", e))?;

    // VALIDAÇÃO EXTRA: verificar se realmente leu dados
    if data.len() != size {
      return Err(format!("Size mismatch after read: expected {}, got {}", size, data.len()));
    }

    Ok(data)
  }
}

impl Drop for SmbWorkerPool {
  fn drop(&mut self) {
    for (idx, worker) in self.workers.iter().enumerate() {
      if let Ok(mut w) = worker.try_lock() {
        let _ = w.process.kill();
      }
    }
  }
}
