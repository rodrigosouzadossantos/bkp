use anyhow::{Result, anyhow};
use std::ffi::{CStr, CString};
use std::os::raw::{c_char, c_int};

// FFI structs
#[repr(C)]
pub struct SMBCCTX {
    _private: [u8; 0],
}

#[repr(C)]
pub struct SmbcDirent {
    pub name: *const c_char,
}

// FFI functions
#[link(name = "smbclient")]
unsafe extern "C" {
    fn smbc_init(
        auth_fn: Option<extern "C" fn(
            *const c_char,
            *const c_char,
            *mut c_char,
            c_int,
            *mut c_char,
            c_int,
            *mut c_char,
            c_int,
        )>,
        flags: c_int
    ) -> c_int;

    fn smbc_new_context() -> *mut SMBCCTX;
    fn smbc_setOptionUseKerberos(ctx: *mut SMBCCTX, use_kerberos: c_int) -> c_int;
    fn smbc_init_context(ctx: *mut SMBCCTX) -> c_int;
    fn smbc_set_context(ctx: *mut SMBCCTX) -> *mut SMBCCTX;

    fn smbc_opendir(url: *const c_char) -> c_int;
    fn smbc_readdir(dh: c_int) -> *mut SmbcDirent;
    fn smbc_closedir(dh: c_int) -> c_int;
}

// Kerberos auth callback: empty username/password
extern "C" fn auth_fn(
    _server: *const c_char,
    _share: *const c_char,
    _workgroup: *mut c_char,
    _wglen: c_int,
    _username: *mut c_char,
    _unlen: c_int,
    _password: *mut c_char,
    _pwlen: c_int,
) {
    unsafe {
        if !_username.is_null() && _unlen > 0 { *_username = 0; }
        if !_password.is_null() && _pwlen > 0 { *_password = 0; }
    }
}

// Initialize SMB client with Kerberos context
pub fn init_smb() -> Result<()> {
    unsafe {
        // Initialize lib with auth callback
        if smbc_init(Some(auth_fn), 0) < 0 {
            return Err(anyhow!("smbc_init failed"));
        }

        // Create context
        let ctx = smbc_new_context();
        if ctx.is_null() {
            return Err(anyhow!("Failed to create SMBC context"));
        }

        // Enable Kerberos
        smbc_setOptionUseKerberos(ctx, 1);

        // Initialize context
        if smbc_init_context(ctx) == 0 {
            return Err(anyhow!("Failed to init SMB context"));
        }

        // Set global context
        smbc_set_context(ctx);
    }
    Ok(())
}

// List SMB directory
pub fn list_dir(path: &str) -> Result<Vec<String>> {
    let c_path = CString::new(path)?;
    unsafe {
        let dh = smbc_opendir(c_path.as_ptr());
        if dh < 0 {
            return Err(anyhow!("smbc_opendir failed"));
        }

        let mut entries = Vec::new();
        loop {
            let dirent_ptr = smbc_readdir(dh);
            if dirent_ptr.is_null() {
                break;
            }
            let dirent = &*dirent_ptr;
            let name = CStr::from_ptr(dirent.name).to_string_lossy().to_string();
            entries.push(name);
        }

        smbc_closedir(dh);
        Ok(entries)
    }
}

// Example usage
fn main() -> Result<()> {
    // Initialize SMB client
    init_smb()?;

    // List directory (replace with your SMB path)
    let path = "smb://SMB.SRJCIPDVFS10101.PETROBRAS.BIZ/servico_002$";
    let entries = list_dir(path)?;

    println!("Entries in {}:", path);
    for e in entries {
        println!("{}", e);
    }

    Ok(())
}
