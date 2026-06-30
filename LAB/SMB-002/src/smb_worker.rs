use std::io::{self, Read, Write};
use std::ffi::CString;
use std::os::raw::c_char;

unsafe extern "C" {
  fn smb_set_credentials(username: *const c_char, password: *const c_char);
  fn smb_read_file(url: *const c_char, buffer: *mut u8, buffer_size: i64) -> i64;
  fn smb_get_file_size(url: *const c_char) -> i64;
}

fn read_smb_file(url: &str) -> Result<Vec<u8>, String> {
  let url_c = CString::new(url).map_err(|e| e.to_string())?;

  let expected_size = unsafe {
    smb_get_file_size(url_c.as_ptr())
  };

  if expected_size < 0 {
    return Err(format!("Falha ao obter tamanho"));
  }

  if expected_size == 0 {
    return Err(format!("Arquivo com tamanho 0 bytes"));
  }

  let mut buffer = vec![0u8; expected_size as usize];

  let bytes_read = unsafe {
    smb_read_file(url_c.as_ptr(), buffer.as_mut_ptr(), expected_size)
  };

  if bytes_read < 0 {
    return Err(format!("Falha ao ler arquivo"));
  }

  if bytes_read != expected_size {
    return Err(format!(
        "Tamanho incompatível! Esperado: {} bytes, Lido: {} bytes",
        expected_size, bytes_read
    ));
  }

  buffer.truncate(bytes_read as usize);

  let all_zeros = buffer.iter().all(|&b| b == 0);
  if all_zeros {
    return Err(format!(
        "Arquivo contém apenas zeros! Tamanho: {} bytes",
        bytes_read
    ));
  }

  Ok(buffer)
}


fn main() {
  eprintln!(
    "[Worker] Starting PID: {}",
    std::process::id()
  );

  let use_kerberos = std::env::var("SMB_USE_KERBEROS").unwrap_or_else(|_| "1".to_string()) == "1";

  if !use_kerberos {
    let username = std::env::var("SMB_USERNAME").unwrap_or_default();
    let password = std::env::var("SMB_PASSWORD").unwrap_or_default();

    eprintln!(
      "[Worker] Using NTLM auth: user={}",
      username
    );

    if !username.is_empty() {
      let user_c = CString::new(username).unwrap();
      let pass_c = CString::new(password).unwrap();
      unsafe {
        smb_set_credentials(user_c.as_ptr(), pass_c.as_ptr());
      }
    }
  } else {
    eprintln!("[Worker] Using Kerberos auth");
    unsafe {
      smb_set_credentials(std::ptr::null(), std::ptr::null());
    }
  }

  let stdin = io::stdin();
  let mut stdout = io::stdout();

  eprintln!("[Worker] Ready to process requests");

  let mut request_count = 0;
  loop {
    let mut size_buf = [0u8; 4];
    if stdin.lock().read_exact(&mut size_buf).is_err() {
      eprintln!("[Worker] EOF on stdin, exiting");
      break;
    }

    let url_size = u32::from_le_bytes(size_buf) as usize;
    if url_size == 0 || url_size > 10000 {
      eprintln!(
        "[Worker] Invalid URL size: {}",
        url_size
      );
      break;
    }

    let mut url_buf = vec![0u8; url_size];
    if stdin.lock().read_exact(&mut url_buf).is_err() {
      eprintln!("[Worker] Failed to read URL, exiting");
      break;
    }

    let url = match String::from_utf8(url_buf) {
      Ok(u) => u,
      Err(_) => {
        eprintln!("[Worker] Invalid UTF-8 in URL, exiting");
        break;
      }
    };

    request_count += 1;
    eprintln!(
      "[Worker] Request #{}: {}",
      request_count, url
    );

    match read_smb_file(&url) {
      Ok(data) => {
        let status = 1u8;
        let size = data.len() as u64;

        eprintln!(
          "[Worker] Successfully read {} bytes from {}",
          size, url
        );

        stdout.write_all(&[status]).unwrap();
        stdout.write_all(&size.to_le_bytes()).unwrap();
        stdout.write_all(&data).unwrap();
        stdout.flush().unwrap();
      },
      Err(e) => {
        eprintln!("[Worker] Erro ao ler {}: {}", url, e);
        let status = 0u8;
        stdout.write_all(&[status]).unwrap();
        stdout.flush().unwrap();
      }
    }
  }
}
