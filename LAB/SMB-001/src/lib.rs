use anyhow::{Result, anyhow};
use std::ffi::{CStr, CString};
use std::os::raw::{c_char, c_int, c_uint};
use rayon::prelude::*;

#[link(name = "smbclient")]
unsafe extern "C" {
    fn smbc_init(auth_fn: Option<extern "C" fn()>, flags: c_int) -> c_int;
    fn smbc_opendir(url: *const c_char) -> c_int;
    fn smbc_readdir(dh: c_uint) -> *mut SmbcDirent;
    fn smbc_closedir(dh: c_int) -> c_int;
    fn smbc_open(path: *const c_char, flags: c_int, mode: c_int) -> c_int;
    fn smbc_read(fd: c_int, buf: *mut u8, len: usize) -> isize;
    fn smbc_close(fd: c_int) -> c_int;
}

/// Corresponding to `struct smbc_dirent` in C
#[repr(C)]
pub struct SmbcDirent {
    pub name: *const c_char,
}

/// Simple auth callback (Kerberos will handle auth)
extern "C" fn auth_fn() {}

/// Initialize SMB client
pub fn init_smb() -> Result<()> {
    let ret = unsafe { smbc_init(Some(auth_fn), 0) };
    if ret < 0 {
        return Err(anyhow!("smbc_init returned {}", ret));
    }
    Ok(())
}

/// List directory
pub fn list_dir(path: &str) -> Result<Vec<String>> {
    let c_path = CString::new(path)?;
    let dh = unsafe { smbc_opendir(c_path.as_ptr()) };
    if dh < 0 {
        return Err(anyhow!("smbc_opendir failed"));
    }

    let mut entries = Vec::new();
    loop {
        let dirent_ptr = unsafe { smbc_readdir(dh as c_uint) };
        if dirent_ptr.is_null() {
            break;
        }
        let dirent = unsafe { &*dirent_ptr };
        let name = unsafe { CStr::from_ptr(dirent.name).to_string_lossy().to_string() };
        entries.push(name);
    }

    unsafe { smbc_closedir(dh) };
    Ok(entries)
}

/// Read a single file into a Vec<u8>
pub fn read_file(path: &str) -> Result<Vec<u8>> {
    let c_path = CString::new(path)?;
    let fd = unsafe { smbc_open(c_path.as_ptr(), 0, 0) };
    if fd < 0 {
        return Err(anyhow!("smbc_open failed"));
    }

    let mut buf = Vec::new();
    let mut tmp = [0u8; 8192];
    loop {
        let n = unsafe { smbc_read(fd, tmp.as_mut_ptr(), tmp.len()) };
        if n < 0 {
            unsafe { smbc_close(fd) };
            return Err(anyhow!("smbc_read failed"));
        }
        if n == 0 {
            break;
        }
        buf.extend_from_slice(&tmp[..n as usize]);
    }

    unsafe { smbc_close(fd) };
    Ok(buf)
}

/// Read all files in parallel
pub fn read_files_parallel(paths: Vec<String>) -> Vec<Result<Vec<u8>>> {
    paths.into_par_iter().map(|p| read_file(&p)).collect()
}
