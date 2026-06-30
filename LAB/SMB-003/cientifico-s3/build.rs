fn main() {
  println!("cargo:rustc-link-lib=smbclient");
  println!("cargo:rustc-link-search=native=/lib/x86_64-linux-gnu");

  cc::Build::new()
    .file("src/smb_wrapper.c")
    .include("/usr/include/samba-4.0")
    .compile("smb_wrapper");
}
