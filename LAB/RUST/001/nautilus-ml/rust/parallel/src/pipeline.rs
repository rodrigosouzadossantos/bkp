// vim: set ts=2 sw=2 et:
// Nautilus ML
// Deep Sea AI/ML Platform
// Rust HPC Engine

pub fn init() {}
use rayon::prelude::*;

pub fn parallel_map<T,U,F>(data: Vec<T>, f: F) -> Vec<U>
where
  T: Send,
  U: Send,
  F: Fn(T) -> U + Send + Sync
{
  data.into_par_iter().map(f).collect()
}
