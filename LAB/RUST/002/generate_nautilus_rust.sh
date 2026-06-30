#!/usr/bin/env bash
set -euo pipefail

PROJECT="nautilus-ml"
RUST_DIR="$PROJECT/rust"

echo "=== Creating Nautilus ML Rust workspace ==="

HEADER="// vim: set ts=2 sw=2 et:
// Nautilus ML
// Deep Sea AI/ML Platform
// Rust HPC Engine
"

create_file() {
  FILE=$1
  mkdir -p "$(dirname "$FILE")"
  echo "$HEADER" > "$FILE"
}

create_module() {
  DIR=$1
  MOD=$2

  echo "pub mod $MOD;" >> "$DIR/lib.rs"

  FILE="$DIR/$MOD.rs"
  create_file "$FILE"

  echo "pub fn init() {}" >> "$FILE"
}

echo "Creating Nautilus ML workspace..."

rm -rf "$PROJECT"
mkdir -p "$RUST_DIR"

cd "$RUST_DIR"

########################################
# CREATE CRATES
########################################

CRATES=(
  nautilus_core
  parallel
  io
  storage
  dataset
  arrow_bridge
  cv
  experiment
  visualization
)

for C in "${CRATES[@]}"; do
  cargo new "$C" --lib
done

########################################
# WORKSPACE
########################################

cat <<EOF > Cargo.toml
[workspace]
resolver = "3"

members = [
  "nautilus_core",
  "parallel",
  "io",
  "storage",
  "dataset",
  "arrow_bridge",
  "cv",
  "experiment",
  "visualization"
]
EOF

########################################
# CORE
########################################

DIR="nautilus_core/src"

create_file "$DIR/lib.rs"
cat >> "$DIR/lib.rs" <<'EOF'

use pyo3::prelude::*;
use pyo3::wrap_pyfunction;

EOF

create_module "$DIR" config
create_module "$DIR" errors
create_module "$DIR" logging
create_module "$DIR" metrics
create_module "$DIR" resources

cat >> "$DIR/lib.rs" <<'EOF'

#[pymodule]
fn nautilus_core(_py: Python, m: &PyModule) -> PyResult<()> {
  m.add_class::<config::Config>()?;
  m.add_function(wrap_pyfunction!(resources::cpu_count, m)?)?;
  Ok(())
}
EOF

cat >> "$DIR/config.rs" <<'EOF'

use pyo3::prelude::*;

#[pyclass]
pub struct Config {
  #[pyo3(get, set)]
  pub workers: usize,
}

#[pymethods]
impl Config {
  #[new]
  fn new(workers: Option<usize>) -> Self {
    Self {
      workers: workers.unwrap_or(num_cpus::get()),
    }
  }

  fn show(&self) -> String {
    format!("Config: {} workers", self.workers)
  }
}
EOF

cat >> "$DIR/resources.rs" <<'EOF'
use pyo3::prelude::*;

#[pyfunction]
pub fn cpu_count() -> usize {
  num_cpus::get()
}
EOF

cat >> "$DIR/errors.rs" <<'EOF'
pub type Result<T> = std::result::Result<T, anyhow::Error>;
EOF

cat >> "$DIR/metrics.rs" <<'EOF'

pub fn report_metric(name: &str, value: f64) {
  println!("Metric {} = {}", name, value);
}
EOF

########################################
# PARALLEL
########################################

DIR="parallel/src"

create_file "$DIR/lib.rs"

create_module "$DIR" threadpool
create_module "$DIR" pipeline
create_module "$DIR" scheduler
create_module "$DIR" batching

cat >> "$DIR/pipeline.rs" <<'EOF'
use rayon::prelude::*;

pub fn parallel_map<T,U,F>(data: Vec<T>, f: F) -> Vec<U>
where
  T: Send,
  U: Send,
  F: Fn(T) -> U + Send + Sync
{
  data.into_par_iter().map(f).collect()
}
EOF

########################################
# IO
########################################

DIR="io/src"

create_file "$DIR/lib.rs"

create_module "$DIR" reader
create_module "$DIR" writer
create_module "$DIR" mmap
create_module "$DIR" buffers

cat >> "$DIR/reader.rs" <<'EOF'
use std::fs::File;
use std::io::{BufReader, Read};

pub fn read_file(path: &str) -> Vec<u8> {

  let file = File::open(path).unwrap();
  let mut reader = BufReader::new(file);

  let mut buf = Vec::new();
  reader.read_to_end(&mut buf).unwrap();

  buf

}
EOF

########################################
# STORAGE
########################################

DIR="storage/src"

create_file "$DIR/lib.rs"

create_module "$DIR" s3
create_module "$DIR" azure
create_module "$DIR" listing
create_module "$DIR" downloader
create_module "$DIR" streaming

cat >> "$DIR/listing.rs" <<'EOF'
pub fn list_objects() -> Vec<String> {

  vec![
    "image1.jpg".into(),
    "image2.jpg".into()
  ]

}
EOF

cat >> "$DIR/downloader.rs" <<'EOF'
use rayon::prelude::*;

pub fn parallel_download(objects: Vec<String>) {

  objects.par_iter().for_each(|o| {

    println!("downloading {}", o);

  });

}
EOF

########################################
# DATASET
########################################

DIR="dataset/src"

create_file "$DIR/lib.rs"

create_module "$DIR" ingest
create_module "$DIR" arrow
create_module "$DIR" parquet
create_module "$DIR" metadata
create_module "$DIR" dataset

cat >> "$DIR/ingest.rs" <<'EOF'
pub fn ingest_files(files: Vec<String>) {

  for f in files {

    println!("ingesting {}", f);

  }

}
EOF

########################################
# ARROW BRIDGE
########################################

DIR="arrow_bridge/src"

create_file "$DIR/lib.rs"

create_module "$DIR" ffi
create_module "$DIR" numpy
create_module "$DIR" conversion

cat >> "$DIR/conversion.rs" <<'EOF'
pub fn arrow_to_numpy() {

  println!("zero copy placeholder");

}
EOF

########################################
# CV
########################################

DIR="cv/src"

create_file "$DIR/lib.rs"

create_module "$DIR" image
create_module "$DIR" video
create_module "$DIR" transforms
create_module "$DIR" batching
create_module "$DIR" gpu

cat >> "$DIR/image.rs" <<'EOF'
pub fn load_image(path: &str) {

  println!("loading image {}", path);

}
EOF

########################################
# EXPERIMENT
########################################

DIR="experiment/src"

create_file "$DIR/lib.rs"

create_module "$DIR" mlflow
create_module "$DIR" wandb
create_module "$DIR" dvc
create_module "$DIR" lakefs

cat >> "$DIR/mlflow.rs" <<'EOF'
pub fn log_metric(name: &str, value: f64) {

  println!("mlflow metric {} {}", name, value);

}
EOF

########################################
# VISUALIZATION
########################################

DIR="visualization/src"

create_file "$DIR/lib.rs"

create_module "$DIR" metrics
create_module "$DIR" aggregation
create_module "$DIR" export

cat >> "$DIR/export.rs" <<'EOF'
pub fn export_numpy() {

  println!("export numpy arrays");

}
EOF

########################################
# INSTALL DEPENDENCIES
########################################

echo "Installing dependencies..."

cd nautilus_core
cargo add num_cpus serde anyhow
cargo add pyo3 --features extension-module
cd ..

cd parallel
cargo add rayon
cd ..

cd io
cargo add memmap2
cd ..

cd storage
cargo add rayon aws-sdk-s3 azure_storage azure_storage_blobs
cd ..

cd dataset
cargo add arrow parquet polars rayon
cd ..

cd arrow_bridge
cargo add arrow pyo3 numpy
cd ..

cd cv
cargo add opencv rayon
cd ..

cd experiment
cargo add serde reqwest
cd ..

cd visualization
cargo add arrow serde
cd ..

########################################

cd ..

# ========================================
# Create Python virtual environment with uv
# ========================================
PYTHON_ENV=".venv"

# Create or activate uv environment
if [ ! -d "$PYTHON_ENV" ]; then
    echo "Creating Python environment via uv in $PYTHON_ENV..."
    uv venv
fi

source "$PYTHON_ENV/bin/activate"

echo "Python environment activated via uv: $(which python)"

echo ""
echo "Nautilus Rust workspace created."
echo ""
echo "Build with:"
echo ""
echo "cd $PROJECT/rust"
echo "cargo build"
