mod s3_uploader;
use s3_uploader::{S3Uploader, S3Config, UploadConfig, upload_files_with_workers};

mod smb_process_pool;
use smb_process_pool::SmbWorkerPool;

mod upload_logger;

use std::ffi::CString;
use std::os::raw::c_char;
use std::io::{self, Write};
use std::fs;
use std::sync::Arc;
use std::time::Duration;
use serde::{Deserialize, Serialize};

#[repr(C)]
#[derive(Clone, Copy)]
struct SmbEntry {
  name: [c_char; 512],
  entry_type: u32,
}

unsafe extern "C" {
  fn smb_set_credentials(username: *const c_char, password: *const c_char);
  fn smb_count_entries(url: *const c_char) -> i32;
  fn smb_list_directory(url: *const c_char, entries: *mut SmbEntry, max_entries: i32) -> i32;
//  fn smb_read_file(url: *const c_char, buffer: *mut u8, buffer_size: i64) -> i64;
//  fn smb_get_file_size(url: *const c_char) -> i64;
}

// Lock global para serializar acesso ao SMB (libsmbclient não é thread-safe)
//lazy_static::lazy_static! {
//  static ref SMB_LOCK: Mutex<()> = Mutex::new(());
//}
lazy_static::lazy_static! {
  static ref SMB_LOCK: tokio::sync::Mutex<()> = tokio::sync::Mutex::new(());
}

#[derive(Debug, Deserialize, Serialize)]
struct S3ConfigYaml {
  bucket: String,
  prefix: Option<String>,
  region: String,
}

#[derive(Debug, Deserialize, Serialize)]
struct TimeoutConfig {
  smb_read_seconds: u64,
  s3_upload_seconds: u64,
  s3_check_seconds: u64,
  worker_idle_seconds: u64,
}

#[derive(Debug, Deserialize, Serialize)]
struct RetryConfig {
  max_attempts: u32,
  backoff_seconds: u64,
  exponential_backoff: bool,
}

#[derive(Debug, Deserialize, Serialize)]
struct UploadConfigYaml {
  max_concurrent_jobs: usize,
  max_smb_workers: usize,
  chunk_size: usize,
  skip_existing: bool,
  timeouts: TimeoutConfig,
  retry: RetryConfig,
}

#[derive(Debug, Deserialize, Serialize)]
struct ServerConfig {
  host: String,
  share: String,
  #[serde(default)]
  directories: Option<Vec<String>>,
  use_kerberos: bool,
  description: Option<String>,
  s3: Option<S3ConfigYaml>,
}

#[derive(Debug, Deserialize, Serialize)]
struct GlobalConfig {
  workgroup: String,
  realm: String,
  default_user: Option<String>,
  default_password: Option<String>,
  upload: Option<UploadConfigYaml>,
}

#[derive(Debug, Deserialize, Serialize)]
struct Config {
  servers: std::collections::HashMap<String, ServerConfig>,
  global: GlobalConfig,
}

impl Config {
  fn load(path: &str) -> Result<Self, Box<dyn std::error::Error>> {
    let content = fs::read_to_string(path)?;
    let config: Config = serde_yaml::from_str(&content)?;
    Ok(config)
  }
}

fn get_password(prompt: &str) -> String {
  print!("{}", prompt);
  io::stdout().flush().unwrap();
  rpassword::read_password().unwrap_or_default()
}

fn count_directory(url: &str) -> Result<i32, String> {
  let url_c = CString::new(url).map_err(|e| e.to_string())?;

  let count = unsafe {
    smb_count_entries(url_c.as_ptr())
  };

  if count < 0 {
    return Err("Falha ao contar itens".to_string());
  }

  Ok(count)
}

fn list_directory(url: &str, max_to_show: usize) -> Result<Vec<(String, u32)>, String> {
  let url_c = CString::new(url).map_err(|e| e.to_string())?;

  let max_entries = 200_000;
  let mut entries = vec![SmbEntry { name: [0; 512], entry_type: 0 }; max_entries];

  let count = unsafe {
    smb_list_directory(url_c.as_ptr(), entries.as_mut_ptr(), max_entries as i32)
  };

  if count < 0 {
    return Err("Falha ao listar diretório".to_string());
  }

  let mut result = Vec::new();
  let limit = (count as usize).min(max_to_show);

  for i in 0..limit {
    let name = unsafe {
      std::ffi::CStr::from_ptr(entries[i].name.as_ptr())
        .to_string_lossy()
        .to_string()
    };
    result.push((name, entries[i].entry_type));
  }

  Ok(result)
}

fn list_all_files(url: &str) -> Result<Vec<(String, u32)>, String> {
  let url_c = CString::new(url).map_err(|e| e.to_string())?;
  let max_entries = 200_000;
  let mut entries = vec![SmbEntry { name: [0; 512], entry_type: 0 }; max_entries];

  let count = unsafe {
    smb_list_directory(url_c.as_ptr(), entries.as_mut_ptr(), max_entries as i32)
  };

  if count < 0 {
    return Err("Falha ao listar".to_string());
  }

  let mut result = Vec::new();
  for i in 0..count as usize {
    let name = unsafe {
      std::ffi::CStr::from_ptr(entries[i].name.as_ptr())
        .to_string_lossy()
        .to_string()
    };
    result.push((name, entries[i].entry_type));
  }

  Ok(result)
}

//fn read_smb_file(url: &str) -> Result<Vec<u8>, String> {
//  let url_c = CString::new(url).map_err(|e| e.to_string())?;
//
//  let size = unsafe {
//    smb_get_file_size(url_c.as_ptr())
//  };
//
//  if size < 0 {
//    return Err(format!("Falha ao obter tamanho: {}", url));
//  }
//
//  if size == 0 {
//    return Ok(Vec::new());
//  }
//
//  let mut buffer = vec![0u8; size as usize];
//  let bytes_read = unsafe {
//    smb_read_file(url_c.as_ptr(), buffer.as_mut_ptr(), size)
//  };
//
//  if bytes_read < 0 {
//    return Err(format!("Falha ao ler: {}", url));
//  }
//
//  buffer.truncate(bytes_read as usize);
//  Ok(buffer)
//}

fn setup_authentication(
  use_kerberos: bool, 
  username: Option<String>, 
  password: Option<String>,
  realm: &str
) {
  if use_kerberos {
    println!("🎫 Usando Kerberos");
    unsafe {
      smb_set_credentials(std::ptr::null(), std::ptr::null());
    }
  } else {
    let user = username.unwrap_or_else(|| {
      print!("Username: ");
      io::stdout().flush().unwrap();
      let mut u = String::new();
      io::stdin().read_line(&mut u).unwrap();
      u.trim().to_string()
    });

    let pass = if let Some(p) = password {
      if !p.is_empty() {
        println!("🔑 Usando senha do config.yaml");
        p
      } else {
        get_password(&format!("Password for {}@{}: ", user, realm))
      }
    } else {
      get_password(&format!("Password for {}@{}: ", user, realm))
    };

    let user_c = CString::new(user.as_str()).unwrap();
    let pass_c = CString::new(pass.as_str()).unwrap();

    unsafe {
      smb_set_credentials(user_c.as_ptr(), pass_c.as_ptr());
    }

    println!("\n🔑 Autenticando como: {}", user);
  }
}

fn show_results(url: &str, total: i32) {
  let show_limit = if total > 1000 { 50 } else { total as usize };

  println!("📥 Carregando primeiros {} itens...\n", show_limit);

  match list_directory(url, show_limit) {
    Ok(entries) => {
      let mut dirs = 0;
      let mut files = 0;

      println!("{:-<80}", "");
      for (name, entry_type) in &entries {
        let (icon, label) = match entry_type {
          7 => { dirs += 1; ("📁", "DIR ") },
          8 => { files += 1; ("📄", "FILE") },
          9 => ("🔗", "LINK"),
          _ => ("❓", "????"),
        };
        println!("  {} [{}] {}", icon, label, name);
      }
      println!("{:-<80}", "");

      if total > show_limit as i32 {
        println!("\n... e mais {} itens não exibidos", total - show_limit as i32);
      }

      println!("\n📊 Estatísticas:");
      println!("   Exibidos: {}", entries.len());
      println!("   📁 Diretórios (amostra): {}", dirs);
      println!("   📄 Arquivos (amostra): {}", files);
      println!("   📦 Total no diretório: {}", total);
    },
    Err(e) => {
      eprintln!("❌ Erro ao listar: {}", e);
    }
  }
}

fn process_single_directory(url: &str, use_kerberos: bool) {
  println!("📂 URL: {}\n", url);

  println!("📊 Contando itens no diretório...");
  match count_directory(url) {
    Ok(total) => {
      println!("✅ Total de itens: {}\n", total);
      show_results(url, total);
    },
    Err(e) => {
      eprintln!("❌ Erro ao contar: {}", e);
      if !use_kerberos {
        eprintln!("💡 Verifique usuário e senha");
      } else {
        eprintln!("💡 Verifique seu ticket Kerberos: klist");
      }
    }
  }
}

fn process_all_directories_list_mode(
  server_config: &ServerConfig,
  directories: &[String],
) {
  println!("\n📁 Processando {} diretórios...\n", directories.len());

  let mut total_items = 0;
  let mut total_dirs = 0;
  let mut total_files = 0;

  for (idx, dir) in directories.iter().enumerate() {
    let mut url = format!("smb://{}/{}", server_config.host, server_config.share);
    if !url.ends_with('/') {
      url.push('/');
    }
    url.push_str(dir);
    if !url.ends_with('/') {
      url.push('/');
    }

    println!("{:-<80}", "");
    println!("📂 [{}/{}] {}", idx + 1, directories.len(), dir);
    println!("{:-<80}", "");

    match count_directory(&url) {
      Ok(count) => {
        println!("✅ Total de itens: {}", count);
        total_items += count;

        if let Ok(entries) = list_directory(&url, 10) {
          let mut dirs = 0;
          let mut files = 0;

          for (name, entry_type) in &entries {
            let (icon, label) = match entry_type {
              7 => { dirs += 1; ("📁", "DIR ") },
              8 => { files += 1; ("📄", "FILE") },
              9 => ("🔗", "LINK"),
              _ => ("❓", "????"),
            };
            println!("  {} [{}] {}", icon, label, name);
          }

          if count > 10 {
            println!("  ... e mais {} itens", count - 10);
          }

          total_dirs += dirs;
          total_files += files;
        }
      },
      Err(e) => {
        eprintln!("❌ Erro: {}", e);
      }
    }
    println!();
  }

  println!("{:=<80}", "");
  println!("📊 RESUMO GERAL");
  println!("{:=<80}", "");
  println!("   Diretórios processados: {}", directories.len());
  println!("   Total de itens: {}", total_items);
  println!("   📁 Diretórios (amostra): {}", total_dirs);
  println!("   📄 Arquivos (amostra): {}", total_files);
  println!("{:=<80}", "");
}

//async fn read_smb_file_via_command(url: &str) -> Result<Vec<u8>, String> {
//  // Usar smbget que suporta múltiplas instâncias
//  let output = tokio::process::Command::new("smbget")
//    .arg("-q")  // quiet
//    .arg("-n")  // non-interactive
//    .arg("-k")  // use kerberos
//    .arg("-O")  // output to stdout
//    .arg(url)
//    .output()
//    .await
//    .map_err(|e| e.to_string())?;
//
//  if output.status.success() {
//    Ok(output.stdout)
//  } else {
//    Err(format!("smbget failed: {}", String::from_utf8_lossy(&output.stderr)))
//  }
//}

async fn perform_upload(
    server_config: &ServerConfig,
    directories: &[String],
    s3_config: S3Config,
    upload_config: UploadConfig,
    global_config: &GlobalConfig,
    num_smb_workers: usize,
    smb_timeout_secs: u64,
) {
    let uploader = Arc::new(S3Uploader::new(s3_config, upload_config).await);
    
    println!("📋 Coletando lista de arquivos de {} diretórios...\n", directories.len());
    let mut all_files = Vec::new();
    
    for (idx, dir) in directories.iter().enumerate() {
        let mut url = format!("smb://{}/{}", server_config.host, server_config.share);
        if !url.ends_with('/') {
            url.push('/');
        }
        url.push_str(dir);
        if !url.ends_with('/') {
            url.push('/');
        }
        
        print!("  [{}/{}] Listando {}... ", idx + 1, directories.len(), dir);
        io::stdout().flush().unwrap();
        
        match list_all_files(&url) {
            Ok(entries) => {
                let file_count = entries.iter().filter(|(_, t)| *t == 8).count();
                println!("✅ {} arquivos", file_count);
                
                for (filename, file_type) in entries {
                    if file_type == 8 {
                        let smb_url = format!("smb://{}/{}/{}/{}", 
                            server_config.host, 
                            server_config.share, 
                            dir, 
                            filename
                        );
                        let s3_key = uploader.get_s3_key(dir, &filename);
                        all_files.push((smb_url, s3_key));
                    }
                }
            },
            Err(e) => {
                println!("❌ Erro: {}", e);
            }
        }
    }
    
    println!("\n✅ Total de arquivos encontrados: {}\n", all_files.len());
    
    if all_files.is_empty() {
        println!("⚠️  Nenhum arquivo para fazer upload");
        return;
    }
    
    let num_workers = uploader.upload_config.max_concurrent;
    
    println!("🚀 Iniciando pipeline de upload");
    println!("⚡ {} processos SMB independentes", num_smb_workers);
    println!("⚡ {} workers S3 em paralelo", num_workers);
    println!("⚙️  Pipeline: Check S3 (paralelo) → Read SMB ({} processos) → Upload S3 (paralelo)\n", num_smb_workers);
    
    // Criar pool de workers SMB (processos independentes)
    let username = if server_config.use_kerberos {
        None
    } else {
        global_config.default_user.clone()
    };
    
    let password = if server_config.use_kerberos {
        None
    } else {
        global_config.default_password.clone()
    };
    
    let worker_pool = Arc::new(SmbWorkerPool::new(
        num_smb_workers,
        server_config.use_kerberos,
        username,
        password,
    ));
    
    // Função de leitura usando o pool
    let read_fn = move |url: String| {
      let pool = worker_pool.clone();
      let timeout = smb_timeout_secs;
      async move {
        pool.read_file(url, timeout).await
      }
    };
    
    let stats = upload_files_with_workers(
        uploader,
        all_files,
        read_fn,
    ).await;
    
    println!("\n{:=<80}", "");
    println!("📊 RESUMO DO UPLOAD");
    println!("{:=<80}", "");
    println!("   ⏱️  Início: {}", stats.start_time.format("%Y-%m-%d %H:%M:%S"));
    println!("   ⏱️  Término: {}", stats.end_time.format("%Y-%m-%d %H:%M:%S"));
    let duration = stats.end_time.signed_duration_since(stats.start_time);
    println!("   ⏱️  Duração: {}h {}m {}s", 
      duration.num_hours(),
      duration.num_minutes() % 60,
      duration.num_seconds() % 60);
    println!("   Total de arquivos: {}", stats.total_files);
    println!("   ✅ Enviados: {}", stats.uploaded);
    println!("   ⏭️  Ignorados (já existentes): {}", stats.skipped);
    println!("   ❌ Falhas: {}", stats.failed);
    println!("   📦 Total enviado: {:.2} MB", stats.total_bytes as f64 / 1024.0 / 1024.0);
    println!("{:=<80}", "");

}

#[tokio::main]
async fn main() {
  let args: Vec<String> = std::env::args().collect();

  let config_path = "config.yaml";
  let config = match Config::load(config_path) {
    Ok(c) => c,
    Err(e) => {
      eprintln!("❌ Erro ao carregar {}: {}", config_path, e);
      return;
    }
  };

  if args.len() < 2 {
    eprintln!("Uso: {} <servidor|url> [diretório|caminho] [-u username] [-p password] [--upload]", args[0]);
    eprintln!("\nServidores disponíveis:");
    for (name, server) in &config.servers {
      let desc = server.description.as_deref().unwrap_or("");
      let auth = if server.use_kerberos { "Kerberos" } else { "NTLM" };
      println!("  • {} - {} ({})", name, desc, auth);
      if let Some(dirs) = &server.directories {
        println!("      📁 {} diretórios configurados", dirs.len());
      }
      if server.s3.is_some() {
        println!("      ☁️  Upload S3 configurado");
      }
    }
    eprintln!("\nExemplos:");
    eprintln!("  {} servico", args[0]);
    eprintln!("  {} noaa                    # Lista todos os diretórios", args[0]);
    eprintln!("  {} noaa DIR                # Lista diretório específico", args[0]);
    eprintln!("  {} noaa --upload           # Upload todos para S3", args[0]);
    eprintln!("  {} noaa DIR --upload       # Upload DIR para S3", args[0]);
    return;
  }

  let server_or_url = &args[1];
  let mut path = String::new();
  let mut username = config.global.default_user.clone();
  let mut password = config.global.default_password.clone();
  let mut do_upload = false;

  let mut i = 2;
  while i < args.len() {
    match args[i].as_str() {
      "-u" | "--user" => {
        if i + 1 < args.len() {
          username = Some(args[i + 1].clone());
          i += 2;
        } else {
          eprintln!("Erro: -u requer um argumento");
          return;
        }
      },
      "-p" | "--password" => {
        if i + 1 < args.len() {
          password = Some(args[i + 1].clone());
          i += 2;
        } else {
          eprintln!("Erro: -p requer um argumento");
          return;
        }
      },
      "--upload" => {
        do_upload = true;
        i += 1;
      },
      _ => {
        if !args[i].starts_with('-') && path.is_empty() {
          path = args[i].clone();
        }
        i += 1;
      }
    }
  }

  // Processar servidor
  if server_or_url.starts_with("smb://") {
    let needs_auth = server_or_url.contains("dfs.petrobras.biz");
    let url = server_or_url.to_string();
    let use_kerberos = !needs_auth;

    setup_authentication(use_kerberos, username, password, &config.global.realm);
    process_single_directory(&url, use_kerberos);
  } else if let Some(server_config) = config.servers.get(server_or_url) {
    if let Some(desc) = &server_config.description {
      println!("📋 Servidor: {}", desc);
    }

    setup_authentication(server_config.use_kerberos, username, password, &config.global.realm);

    // Se tem lista de diretórios
    if let Some(directories) = &server_config.directories {
      if path.is_empty() {
        // Modo UPLOAD ou LISTAGEM de todos
        if do_upload {
          if let (Some(s3_yaml), Some(upload_yaml)) = (&server_config.s3, &config.global.upload) {
            let s3_config = S3Config {
              bucket: s3_yaml.bucket.clone(),
              prefix: s3_yaml.prefix.clone(),
              region: s3_yaml.region.clone(),
            };

            let upload_config = UploadConfig {
              max_concurrent: upload_yaml.max_concurrent_jobs,
              chunk_size: upload_yaml.chunk_size,
              skip_existing: upload_yaml.skip_existing,
              smb_timeout: Duration::from_secs(upload_yaml.timeouts.smb_read_seconds),
              s3_upload_timeout: Duration::from_secs(upload_yaml.timeouts.s3_upload_seconds),
              s3_check_timeout: Duration::from_secs(upload_yaml.timeouts.s3_check_seconds),
              max_retries: upload_yaml.retry.max_attempts,
              retry_backoff: Duration::from_secs(upload_yaml.retry.backoff_seconds),
              exponential_backoff: upload_yaml.retry.exponential_backoff,
            };

            let num_smb_workers = upload_yaml.max_smb_workers;
            let smb_timeout_secs = upload_yaml.timeouts.smb_read_seconds;

            println!("\n🚀 Modo UPLOAD ativado");
            println!("📦 Bucket: s3://{}/{}", s3_config.bucket, s3_config.prefix.as_deref().unwrap_or(""));
            println!("⚡ Conexões S3: {}", upload_config.max_concurrent);
            println!("⚡ Workers SMB: {}\n", num_smb_workers);

            perform_upload(
              server_config, 
              directories, 
              s3_config, 
              upload_config,
              &config.global,
              num_smb_workers,
              smb_timeout_secs
            ).await;
          } else {
            eprintln!("❌ Configuração S3 ou upload não encontrada no config.yaml");
          }
        } else {
          process_all_directories_list_mode(server_config, directories);
        }
      } else {
        // PROCESSAR DIRETÓRIO ESPECÍFICO
        if directories.contains(&path) {
          if do_upload {
            if let (Some(s3_yaml), Some(upload_yaml)) = (&server_config.s3, &config.global.upload) {
              let s3_config = S3Config {
                bucket: s3_yaml.bucket.clone(),
                prefix: s3_yaml.prefix.clone(),
                region: s3_yaml.region.clone(),
              };

              let upload_config = UploadConfig {
                max_concurrent: upload_yaml.max_concurrent_jobs,
                chunk_size: upload_yaml.chunk_size,
                skip_existing: upload_yaml.skip_existing,
                smb_timeout: Duration::from_secs(upload_yaml.timeouts.smb_read_seconds),
                s3_upload_timeout: Duration::from_secs(upload_yaml.timeouts.s3_upload_seconds),
                s3_check_timeout: Duration::from_secs(upload_yaml.timeouts.s3_check_seconds),
                max_retries: upload_yaml.retry.max_attempts,
                retry_backoff: Duration::from_secs(upload_yaml.retry.backoff_seconds),
                exponential_backoff: upload_yaml.retry.exponential_backoff,
              };

              let num_smb_workers = upload_yaml.max_smb_workers;
              let smb_timeout_secs = upload_yaml.timeouts.smb_read_seconds;

              println!("\n🚀 Modo UPLOAD ativado");
              println!("📂 Diretório: {}", path);
              println!("📦 Bucket: s3://{}/{}", s3_config.bucket, s3_config.prefix.as_deref().unwrap_or(""));
              println!("⚡ Conexões S3: {}", upload_config.max_concurrent);
              println!("⚡ Workers SMB: {}\n", num_smb_workers);

              perform_upload(
                server_config, 
                &vec![path.clone()], 
                s3_config, 
                upload_config,
                &config.global,
                num_smb_workers,
                smb_timeout_secs
              ).await;
            } else {
              eprintln!("❌ Configuração S3 ou upload não encontrada");
            }
          } else {
            let mut url = format!("smb://{}/{}", server_config.host, server_config.share);
            if !url.ends_with('/') {
              url.push('/');
            }
            url.push_str(&path);
            if !url.ends_with('/') {
              url.push('/');
            }

            println!("📂 Diretório: {}\n", path);
            process_single_directory(&url, server_config.use_kerberos);
          }
        } else {
          eprintln!("❌ Diretório '{}' não encontrado na configuração", path);
          eprintln!("\nDiretórios disponíveis:");
          for dir in directories {
            println!("  • {}", dir);
          }
        }
      }
    } else if !path.is_empty() {
      let mut url = format!("smb://{}/{}", server_config.host, server_config.share);
      if !url.ends_with('/') && !path.starts_with('/') {
        url.push('/');
      }
      url.push_str(&path);
      if !url.ends_with('/') {
        url.push('/');
      }

      process_single_directory(&url, server_config.use_kerberos);
    } else {
      let url = format!("smb://{}/{}", server_config.host, server_config.share);
      process_single_directory(&url, server_config.use_kerberos);
    }
  } else {
    eprintln!("❌ Servidor '{}' não encontrado", server_or_url);
  }
}
