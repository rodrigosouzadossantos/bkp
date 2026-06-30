use std::io::{Write, Read, BufReader};
use std::os::unix::io::{AsRawFd, FromRawFd};
use std::process::{Child, Command, Stdio};
use std::sync::{Arc,mpsc};
use std::thread;
use std::time::{Duration,SystemTime, UNIX_EPOCH};
use tokio::sync::{Semaphore, Mutex};

pub struct SmbWorkerPool {
  workers: Vec<Arc<Mutex<SmbWorker>>>,
  semaphore: Arc<Semaphore>,
  use_kerberos: bool,
  username: Option<String>,
  password: Option<String>,
}

struct SmbWorker {
  process: Child,
  worker_id: usize,
  created_at: u64,
  requests_processed: u64,
  last_request_at: u64,
}

impl SmbWorkerPool {
  pub fn new(
    size: usize,
    use_kerberos: bool,
    username: Option<String>,
    password: Option<String>
  ) -> Self {
    let mut workers = Vec::new();
    let now = SystemTime::now()
      .duration_since(UNIX_EPOCH)
      .unwrap()
      .as_secs();

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
          eprintln!(
            "[Pool] Worker {} spawned with PID {:?}",
            worker_id, process.id()
          );
          workers.push(Arc::new(
            Mutex::new(SmbWorker {
              process,
              worker_id,
              created_at: now,
              requests_processed: 0,
              last_request_at: 0,
            })
          ));
        },
        Err(e) => {
          eprintln!(
            "❌ Failed to spawn worker {}: {}",
            worker_id, e
          );
          panic!("Cannot start worker pool");
        }
      }
    }

    Self {
      workers,
      semaphore: Arc::new(Semaphore::new(size)),
      use_kerberos,
      username,
      password,
    }
  }

  fn respawn_worker(
    worker_arc: Arc<Mutex<SmbWorker>>,
    worker_idx: usize,
    use_kerberos: bool,
    username: &Option<String>,
    password: &Option<String>,
  ) -> Result<(), String> {
    eprintln!("[Pool] Recriando worker {}...", worker_idx);

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
      if let Some(user) = username {
        cmd.env("SMB_USERNAME", user);
      }
      if let Some(pass) = password {
        cmd.env("SMB_PASSWORD", pass);
      }
    }

    let process = cmd.spawn()
      .map_err(|e| format!("Failed to respawn: {}", e))?;

    let pid = process.id();
    eprintln!("[Pool] Worker {} recriado com PID {:?}", worker_idx, pid);

    let now = SystemTime::now()
      .duration_since(UNIX_EPOCH)
      .unwrap()
      .as_secs();

    // Substituir o worker morto
    let new_worker = SmbWorker {
      process,
      worker_id: worker_idx,
      created_at: now,
      requests_processed: 0,
      last_request_at: 0,
    };

    // Tentar bloquear e substituir
    if let Ok(mut worker_lock) = worker_arc.try_lock() {
      // Matar o processo antigo se ainda existir
      let _ = worker_lock.process.kill();
      let _ = worker_lock.process.wait();

      *worker_lock = new_worker;
      Ok(())
    } else {
      Err("Failed to lock worker for replacement".to_string())
    }
  }

  pub async fn read_file(
    &self,
    url: String,
    timeout_secs: u64,
  ) -> Result<Vec<u8>, String> {
    let permit = self.semaphore.acquire().await.unwrap();

    let worker_idx = {
      use std::collections::hash_map::DefaultHasher;
      use std::hash::{Hash, Hasher};
      let mut hasher = DefaultHasher::new();
      url.hash(&mut hasher);
      hasher.finish() as usize % self.workers.len()
    };

    let worker = self.workers[worker_idx].clone();

    let use_kerberos = self.use_kerberos;
    let username = self.username.clone();
    let password = self.password.clone();

    let result = tokio::task::spawn_blocking(move || {
      let mut worker_lock = worker.blocking_lock();

      // Diagnóstico antes da comunicação
      let pid = worker_lock.process.id();
      let worker_id = worker_lock.worker_id;
      let now = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap()
        .as_secs();

      eprintln!(
        "[Worker {}] PID: {:?}, Requests: {}, Last: {}s ago, Uptime: {}s",
        worker_id,
        pid,
        worker_lock.requests_processed,
        now.saturating_sub(worker_lock.last_request_at),
        now - worker_lock.created_at
      );

      // Verificar se processo está vivo
      match worker_lock.process.try_wait() {
        Ok(Some(status)) => {
          eprintln!(
            "Worker {} (PID {:?}) Detectado morto (status: {}), recriando...",
            worker_id, pid, status
          );
          if let Some(stderr) = worker_lock.process.stderr.as_mut() {
            let mut err_buf = String::new();
            let _ = stderr.read_to_string(&mut err_buf);
            eprintln!(
              "[Worker {}] STDERR:\n{}",
              worker_id, err_buf
            );
          }

          drop(worker_lock); // Liberar lock antes de recriar
                             //
          eprintln!("[Worker {}] Recriando worker agora...", worker_id);

          // Recriar Worker
          if let Err(e) = Self::respawn_worker(
            worker.clone(),
            worker_idx,
            use_kerberos,
            &username,
            &password,
          ) {
            return Err(format!(
              "Failed to respawn worker {}: {}",
              worker_id, e
            ));
          }

          worker_lock = worker.blocking_lock();

          eprintln!(
            "[Worker {}] Recriado com PID {:?}",
            worker_id, worker_lock.process.id()
          );
        },
        Ok(None) => {
          // Processo ainda rodando
        },
        Err(e) => {
          return Err(format!(
            "Worker {} (PID {:?}) erro ao verificar status: {}",
            worker_id, pid, e
          ));
        }
      }

      // Verificar disponibilidade de streams antes de usar
      if worker_lock.process.stdin.is_none() {
        return Err(format!(
          "Worker {} (PID {:?}) stdin not available",
          worker_id, pid
        ));
      }
      if worker_lock.process.stdout.is_none() {
        return Err(format!(
          "Worker {} (PID {:?}) stdout not available",
          worker_id, pid
        ));
      }

      let result = Self::communicate_with_worker(&mut worker_lock, &url, timeout_secs);

      // Atualizar estatísticas
      worker_lock.requests_processed += 1;
      worker_lock.last_request_at = SystemTime::now().duration_since(UNIX_EPOCH).unwrap().as_secs();

      result
    })
    .await
      .map_err(|e| format!(
        "Task join error: {}", e
      ))??;

    drop(permit);
    Ok(result)
  }

  fn communicate_with_worker(
    worker: &mut SmbWorker,
    url: &str,
    timeout_secs: u64
  ) -> Result<Vec<u8>, String> {
    let url_bytes = url.as_bytes();
    let url_size = url_bytes.len() as u32;
    let worker_id = worker.worker_id;
    let pid = worker.process.id();

    eprintln!(
      "[Worker {}] Enviando requisição para: {}",
      worker_id, url
    );

    // Verificar se worker ainda está vivo ANTES de usar
    match worker.process.try_wait() {
      Ok(Some(status)) => {
        // Worker morreu - capturar stderr
        if let Some(stderr) = worker.process.stderr.as_mut() {
          let mut err_buf = String::new();
          let _ = stderr.read_to_string(&mut err_buf);
          eprintln!(
            "[Worker {}] STDERR:\n{}",
            worker_id, err_buf
          );
        }
        return Err(format!(
            "[Worker {}] (PID {:?}) já morreu com status: {}",
            worker_id, pid, status
        ));
      },
      Ok(None) => {
        // Processo ainda rodando - OK
      },
      Err(e) => {
        return Err(format!(
          "[Worker {}] Erro ao verificar status: {}",
          worker_id, e
        ));
      }
    }

    let stdin = worker.process.stdin.as_mut()
      .ok_or_else(|| format!("[Worker {}] stdin not available", worker_id))?;

    // Enviar requisição
    stdin.write_all(&url_size.to_le_bytes())
      .map_err(|e| {
        eprintln!(
          "[Worker {}] Erro ao escrever tamanho no stdin: {}",
          worker_id, e
        );
        format!("Worker {} stdin write size: {}", worker_id, e)
      })?;
    stdin.write_all(url_bytes)
      .map_err(|e| {
        eprintln!(
          "[Worker {}] Erro ao escrever URL no stdin: {}",
          worker_id, e
        );
        format!("Worker {} stdin write url: {}", worker_id, e)
      })?;
    stdin.flush()
      .map_err(|e| {
        eprintln!(
          "[Worker {}] Erro ao flush stdin: {}",
          worker_id, e
        );
        format!("Worker {} stdin flush: {}", worker_id, e)
      })?;

    eprintln!(
      "[Worker {}] Requisição enviada, aguardando resposta...",
      worker_id
    );

    let stdout = worker.process.stdout.as_mut()
      .ok_or_else(|| format!(
        "Worker {} stdout not available",
        worker_id
      ))?;

    // Criar canal para timeout
    let (tx, rx) = mpsc::channel();

    // Clonar o file descriptor para thread
    let stdout_fd = stdout.as_raw_fd();
    let stdout_clone = unsafe { std::fs::File::from_raw_fd(stdout_fd) };

    // Thread para ler stdout com timeout
    thread::spawn(move || {
      let mut reader = BufReader::new(stdout_clone);

      let mut status_buf = [0u8; 1];
      if reader.read_exact(&mut status_buf).is_err() {
        let _ = tx.send(Err("Failed to read status".to_string()));
        return;
      }

      if status_buf[0] == 0 {
        let _ = tx.send(Err("Worker reported failure".to_string()));
        return;
      }

      let mut size_buf = [0u8; 8];
      if reader.read_exact(&mut size_buf).is_err() {
        let _ = tx.send(Err("Failed to read size".to_string()));
        return;
      }

      let size = u64::from_le_bytes(size_buf) as usize;

      if size == 0 {
        let _ = tx.send(Err("File is empty".to_string()));
        return;
      }

      if size > 100_000_000 {
        let _ = tx.send(Err(format!("File too large: {} bytes", size)));
        return;
      }

      let mut data = vec![0u8; size];
      if reader.read_exact(&mut data).is_err() {
        let _ = tx.send(Err("Failed to read data".to_string()));
        return;
      }

      // VALIDAÇÃO EXTRA: verificar se realmente leu dados
      if data.len() != size {
        let _ = tx.send(Err(format!("Size mismatch after read: expected {}, got {}", size, data.len())));
      }

      let _ = tx.send(Ok(data));
    });

    // Esperar resposta com timeout
    match rx.recv_timeout(Duration::from_secs(timeout_secs)) {
      Ok(Ok(data)) => {
        // Recolocar stdout (hack porque Rust ownership)
        // worker.process.stdout será None, mas ok para next call
        eprintln!(
          "[Worker {}] Resposta recebida: {} bytes",
          worker_id, data.len()
        );
        Ok(data)
      },
      Ok(Err(e)) => {
        eprintln!(
          "[Worker {}] Erro: {}",
          worker_id, e
        );
        Err(e)
      },
      Err(_) => {
        eprintln!(
          "[Worker {}] TIMEOUT após {}s",
          worker_id, timeout_secs
        );

        // Tentar matar o processo travado
        eprintln!(
          "[Worker {}] Tentando matar processo travado PID {:?}",
          worker_id, pid
        );
        let _ = worker.process.kill();

        Err(format!(
          "Worker {} timeout after {}s (killed)",
          worker_id, timeout_secs
        ))
      }
    }
  }
}

impl Drop for SmbWorkerPool {
  fn drop(&mut self) {
    eprintln!(
      "[Pool] Shutting down {} workers...",
      self.workers.len()
    );
    for worker in self.workers.iter() {
      if let Ok(mut w) = worker.try_lock() {
        let pid = w.process.id();
        eprintln!(
          "[Pool] Killing worker {} (PID {:?})",
          w.worker_id, pid
        );
        let _ = w.process.kill();
        let _ = w.process.wait();
      }
    }
  }
}
