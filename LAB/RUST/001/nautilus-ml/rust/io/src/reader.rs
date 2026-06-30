// vim: set ts=2 sw=2 et:
// Nautilus ML
// Deep Sea AI/ML Platform
// Rust HPC Engine

pub fn init() {}
use std::fs::File;
use std::io::{BufReader, Read};

pub fn read_file(path: &str) -> Vec<u8> {

  let file = File::open(path).unwrap();
  let mut reader = BufReader::new(file);

  let mut buf = Vec::new();
  reader.read_to_end(&mut buf).unwrap();

  buf

}
