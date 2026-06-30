use libc::{c_char, c_int, c_void, size_t};
use std::ffi::{CStr, CString};
use anyhow::Result;

#[repr(C)]
pub struct SmbcDirent {
    pub name: [c_char; 256],
    pub type_: u8, // 1=file, 2=dir
}

// Mark extern block as unsafe
unsafe extern "C" {
    fn smbc_init(auth_fn: Option<extern "C" fn()>, flags: c_int) -> c_int;
    fn smbc_opendir(url: *const c_char) -> *mut c_void;
    fn smbc_readdir(dir: *mut c_void) -> *mut SmbcDirent;
    fn smbc_closedir(dir: *mut c_void) -> c_int;
    fn smbc_open(path: *const c_char, flags: c_int, mode: c_int) -> c_int;
    fn smbc_read(fd: c_int, buf: *mut u8, count: size_t) -> isize;
    fn smbc_close(fd: c_int) -> c_int;
}

pub fn init() -> Result<()> {
    let r = unsafe { smbc_init(None, 0) };
    if r < 0 {
        anyhow::bail!("Failed to initialize libsmbclient");
    }
    Ok(())
}

pub fn list_dir(path: &str) -> Result<Vec<String>> {
    let c_path = CString::new(path)?;
    unsafe {
        let dir = smbc_opendir(c_path.as_ptr());
        if dir.is_null() {
            anyhow::bail!("Failed to open {}", path);
        }

        let mut entries = Vec::new();
        loop {
            let entry = smbc_readdir(dir);
            if entry.is_null() { break; }
            let name_cstr = CStr::from_ptr((*entry).name.as_ptr());
            let name = name_cstr.to_string_lossy().into_owned();
            if name != "." && name != ".." {
                entries.push(name);
            }
        }
        smbc_closedir(dir);
        Ok(entries)
    }
}

pub fn read_file(path: &str) -> Result<Vec<u8>> {
    let c_path = CString::new(path)?;
    unsafe {
        const O_RDONLY: c_int = 0;
        let fd = smbc_open(c_path.as_ptr(), O_RDONLY, 0);
        if fd < 0 {
            anyhow::bail!("Failed to open file {}", path);
        }

        let mut buf = Vec::new();
        let mut temp = [0u8; 8192];
        loop {
            let n = smbc_read(fd, temp.as_mut_ptr(), temp.len());
            if n < 0 {
                smbc_close(fd);
                anyhow::bail!("Error reading file {}", path);
            }
            if n == 0 { break; }
            buf.extend_from_slice(&temp[..n as usize]);
        }

        smbc_close(fd);
        Ok(buf)
    }
}
