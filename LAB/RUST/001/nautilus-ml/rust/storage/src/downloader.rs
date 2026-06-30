// vim: set ts=2 sw=2 et:
// Nautilus ML
// Deep Sea AI/ML Platform
// Rust HPC Engine

pub fn init() {}
use rayon::prelude::*;

pub fn parallel_download(objects: Vec<String>) {

  objects.par_iter().for_each(|o| {

    println!("downloading {}", o);

  });

}
