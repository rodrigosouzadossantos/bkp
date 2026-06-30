Below is the **Repository Blueprint** for **Nautilus ML**.
This is the artifact large ML infrastructure teams maintain so the **entire
repository can be recreated instantly**.

It is designed so that **if you paste it later, I can regenerate the full
project automatically**.

---

# Nautilus ML — Repository Blueprint

Deep-Sea AI/ML/CV platform inspired by Twenty Thousand Leagues Under the Sea by
Jules Verne.

Python package:

```text
nautilus_ml
```

---

# 1. Repository Root Layout

```text
nautilus-ml/
│
├── rust/
│   ├── Cargo.toml
│   ├── storage/
│   ├── dataset/
│   ├── cv/
│   ├── experiment/
│   └── visualization/
│
├── python/
│   ├── pyproject.toml
│   ├── nautilus_ml/
│   │   ├── __init__.py
│   │   ├── storage.py
│   │   ├── dataset.py
│   │   ├── cv.py
│   │   ├── experiment.py
│   │   └── visualization.py
│   │
│   └── tests/
│
├── scripts/
│   ├── bootstrap.sh
│   ├── build_all.sh
│   └── run_pipeline.sh
│
├── configs/
│   ├── mlflow.yaml
│   ├── wandb.yaml
│   ├── dvc.yaml
│   └── lakefs.yaml
│
├── docs/
│   ├── architecture.md
│   ├── data_flow.md
│   └── system_design.md
│
├── .github/
│   └── workflows/
│       └── ci.yml
│
├── tests/
│   ├── integration/
│   └── performance/
│
└── README.md
```

---

# 2. Rust Workspace

Rust workspace root:

```text
rust/Cargo.toml
```

Workspace definition:

```
[workspace]
members = [
  "storage",
  "dataset",
  "cv",
  "experiment",
  "visualization"
]
```

---

# 3. Rust Crate Dependency Graph

```text
           storage
              │
              ▼
           dataset
              │
              ▼
             cv
              │
              ▼
          experiment
              │
              ▼
        visualization
```

Meaning:

* **storage** fetches raw data
* **dataset** structures it
* **cv** processes images/video
* **experiment** handle experiments with model
  and log everything - model, metrics, artifacts, datasets used, etc.
* **visualization** prepares plotting data

---

# 4. Rust Crate Internal Layout

Each crate follows this structure:

```text
crate_name/
│
├── Cargo.toml
├── src/
│   ├── lib.rs
│   ├── api.rs
│   ├── parallel.rs
│   ├── pipeline.rs
│   └── bindings.rs
│
├── tests/
│   └── integration.rs
│
└── benches/
    └── performance.rs
```

---

# 5. Python Package Layout

```text
python/nautilus_ml/
```

Modules:

| Module           | Purpose                  |
| ---------------- | ------------------------ |
| storage.py       | cloud storage operations |
| dataset.py       | ingestion pipelines      |
| cv.py            | CV preprocessing         |
| experiment.py    | experiment tracking      |
| visualization.py | plotting wrappers        |

Purpose:

Provide Pythonic interface to Rust backend.

Example:

```text
import nautilus_ml as nm

# list buckets in cloud Storage
# it is mandatory to be trasparent where data is stored,
# so we can easily switch between local and cloud storage
# and also to be able to use both at the same time
# the same applies to all other layers - dataset, cv,
# experiment, visualization
# the reference to data location is found in the config file
# it is mandatory to be able to access date without exposeing
# the storage details, so we can easily switch between different
# storage providers and also to be able to use both at the same time
# so, neither the storage provider nor the data location should be
# exposed in the code, but only in the config file - or even better,
# in the environment variables. The code must not contain any
# reference to the storage provider or the data location, but
# only to the dataset name or ID, which is then resolved to the
# actual data location by the storage layer.
# the storage layer must be able to resolve the dataset name or
# ID to the actual data location, and then load the data from
# there and return it the storage layer must be able to handle
# both local and cloud storage, and also to switch between
# them seamlessly, so the code that uses the storage layer
# must not be aware of where the data is actually stored,
# but only of the dataset name or ID, which is then resolved
# to the actual data location by the storage layer, and any
# reference to the storage provider or the data location are
# denyed in the code and must be only found in the config file
# or environment variables
# the storage layer must be split into pluggable modules for
# different storage providers, so we can easily add support
# for new providers in the future without changing the code
# that uses the storage layer, and also to be able to use
# multiple providers at the same time if needed - everything
# must be in rust, in separate modules inside the storage
# crate, and the python bindings must be implemented in a
# way that they can access the same data loaded from storage
# without copying it, so we can efficiently feed it to python
# ml libraries - for example, by using arrow format and
# zero-copy conversion to numpy arrays.
buckets = nm.Storage.list()

# all data processing pipelines are defined in Rust and
# exposed via Python bindings, so we can run them with
# a single line of code
# the data read from storage is automatically converted to
# Arrow format and then to NumPy arrays without copying,
# so we can efficiently feed it to Python ML libraries
# the pipeline must access the same data loaded from storage,
# without copying it
dataset = nm.Dataset.ingest(["img1.jpg"])

frames = nm.CVPipeline.frames("rov_video.mp4")

nm.Experiment.log_metric("accuracy", 0.94)
```

---

# 6. Rust ↔ Python Binding Layout

Bindings handled via:

```text
PyO3
maturin
Arrow FFI
```

Binding location:

```text
rust/*/src/bindings.rs
```

Binding pipeline:

```text
Rust Function
      │
      ▼
PyO3 wrapper
      │
      ▼
Python module
```

Example:

```text
Rust:
dataset::arrow_to_numpy()

Python:
nautilus_ml.Dataset.arrow_to_numpy()
```

---

# 7. Zero-Copy Memory Pipeline

```text
Image Files
      │
      ▼
Rust Dataset Engine
      │
      ▼
Arrow Table
      │
      ▼
Arrow FFI
      │
      ▼
NumPy View
      │
      ▼
Python ML
```

Libraries used:

Rust:

```
arrow
polars
pyo3
numpy
```

Python:

```
pyarrow
numpy
```

---

# 8. Build System

Build steps:

```text
1 bootstrap.sh
2 cargo build
3 maturin develop
4 uv run python
```

---

# 9. Python Environment

Python dependencies managed via:

```
uv
```

Example workflow:

```bash
uv init
uv add numpy
uv add torch
uv add mlflow
uv add wandb
uv run python
```

---

# 10. Data Pipeline Example

```text
S3 bucket
  │
  ▼
Rust Storage
  │
  ▼
Rust Dataset Engine
  │
  ▼
CV Processing
  │
  ▼
Experiment Logging
  │
  ▼
Visualization
  │
  ▼
Python Notebook / Script
```

---

# 11. CI Pipeline

GitHub workflow:

```text
.github/workflows/ci.yml
```

Pipeline:

```text
checkout repo
install rust
install python
install uv
cargo build
cargo test
pytest
ruff
clippy
```

---

# 12. Performance Test Layer

Directory:

```text
tests/performance
```

Benchmarks include:

* ingestion throughput
* CV pipeline throughput
* Arrow conversion speed
* GPU inference latency

---

# 13. Configuration Layer

Directory:

```text
configs/
```

Configs:

| file        | purpose            |
| ----------- | ------------------ |
| mlflow.yaml | MLFlow server      |
| wandb.yaml  | experiment logging |
| dvc.yaml    | dataset tracking   |
| lakefs.yaml | data versioning    |

---

# 14. Scripts

### bootstrap.sh

Creates full project automatically.

Responsibilities:

```
create workspace
generate crates
write files
install dependencies
setup uv
setup CI
```

---

### build_all.sh

Compiles Rust crates and Python bindings.

---

### run_pipeline.sh

Runs full pipeline:

```
ingestion → CV → experiment → visualization
```

---

# 15. HPC Resource Usage Model

CPU usage:

```
rayon threadpool
= 96 cores
```

GPU usage:

```
H100
CUDA pipelines
```

Memory:

```
Arrow columnar buffers
```

---

# 16. Repository Dependency Layers

```text
Cloud Storage
      │
      ▼
Rust Storage
      │
      ▼
Dataset Engine
      │
      ▼
CV Engine
      │
      ▼
Experiment Tracking
      │
      ▼
Visualization
      │
      ▼
Python API
```

---

# 17. Future Scaling Architecture

Potential distributed architecture:

```text
Kubernetes
   │
   ▼
Worker Nodes
   │
   ▼
Rust ingestion pipelines
   │
   ▼
Arrow dataset shards
```

Possible additions:

```
Arrow Flight
Ray distributed
Spark integration
GPU cluster
```

---

# 18. Repository Recovery Instructions

If project context is lost:

Paste:

```
Nautilus ML Repository Blueprint
```

and this document.

Then say:

```
Regenerate Nautilus ML project bootstrap
```

The system can then recreate:

* repository layout
* crate architecture
* Python package
* build scripts

---

# 19. Status of Current Work

Completed:

✔ architecture design
✔ crate structure
✔ Python interface concept
✔ dependency model
✔ HPC strategy

Next step:

```
generate final unified bootstrap script, if it is not possible to generate it in
one step, then generate separate scripts for each layer - storage, dataset, cv,
experiment, visualization - and then combine them into one final bootstrap.sh
script

all code generation must be done in Rust, and the Python bindings must be
implemented in a way that they can access the same data loaded from storage
without copying it, so we can efficiently feed it to Python ML libraries - for
example, by using arrow format and zero-copy conversion to numpy arrays.
The data processing pipelines must be defined in Rust and exposed via Python
bindings, so we can run them with a single line of code, and the data read from
storage must be automatically converted to Arrow format and then to NumPy arrays
without copying, so we can efficiently feed it to Python ML libraries.
The storage layer must be able to resolve the dataset name or ID to the actual
data location, and then load the data from there and return it, and the storage
layer must be able to handle both local and cloud storage, and also to switch
between them seamlessly, so the code that uses the storage layer must not be
aware of where the data is actually stored, but only of the dataset name or ID,
which is then resolved to the actual data location by the storage layer, and any
reference to the storage provider or the data location are denyed in the code
and must be only found in the config file or environment variables.
The storage layer must be split into pluggable modules for different storage
providers, so we can easily add support for new providers in the future without
changing the code that uses the storage layer, and also to be able to use
multiple providers at the same time if needed - everything must be in rust, in
separate modules inside the storage crate, and the python bindings must be
implemented in a way that they can access the same data loaded from storage
without copying, so we can efficiently feed it to python ml libraries - for
example, by using arrow format and zero-copy conversion to numpy arrays.
It is mandatory that everything follows the same pattern - storage, dataset, cv,
experiment, visualization - and the SIMPLE principles - single responsibility,
interface segregation, modularity, and pluggability - with hexagonal
architecture is mandatory.

the bash scripts must provide all code necessary to generate the full project
structure, including the Rust workspace, the Python package, the build system,
the CI pipeline, and the performance test layer, so that if we lose the project
context, we can simply run the bootstrap.sh script and it will recreate
everything from scratch, including all files and directories with their
respective content, and also install all necessary dependencies and set up the
environment for development and testing.
The bootstrap.sh script must be idempotent, so we can run it multiple times
without causing any issues, and it must also be able to update the project
structure if there are any changes in the blueprint, so we can easily maintain
and evolve the project over time without losing the ability to recreate it from
scratch if needed.
if necessary, we can also generate separate scripts for each layer - storage,
dataset,cv, experiment, visualization - that can be run independently to set up
each layer of the project, and then combine them into one final bootstrap.sh
script that runs all of them in sequence to set up the entire project structure
at once.
The scripts must also include commands to set up the Python environment using
uv, and to install all necessary Python dependencies, as well as to set up the
CI pipeline with GitHub Actions, and to create the performance test layer with
the necessary benchmarks and tests for each component of the system.
All just for copy-pasting the code from the blueprint into the scripts, so we
can easily generate the full project structure without having to write any code
manually, and also to ensure that everything is consistent with the blueprint
and follows the same architecture and design principles across all layers of the
system.
The scripts must write all code necessary to create the full project structure,
including all files and directories with their respective content, so we can
simply run the bootstrap.sh script and it will recreate everything from scratch,
including the Rust workspace with its crates and modules, the Python package
with its modules and bindings, the build system with its scripts and commands,
the CI pipeline with its workflow and steps, and the performance test layer with
its benchmarks and tests for each component of the system, all following the
same architecture and design principles outlined in the blueprint, so we can
easily maintain and evolve the project over time without losing the ability to
recreate it from scratch if needed, and also to ensure that everything is
consistent and follows the same patterns across all layers of the system, making
it easier for developers to understand and contribute to the project without
having to learn different architectures or design principles for each layer, but
rather following the same simple and modular approach throughout the entire
codebase.
All code generated by the scripts must be well-structured, properly formatted,
and follow best practices for Rust and Python development, using lint/TDD/TDR
principles and clean code guidelines, so we can ensure that the codebase is
maintainable, readable, and easy to understand for developers of all levels of
experience, and also to ensure that the project can be easily extended and
evolved over time without having to rewrite large portions of the codebase or
refactor it significantly, but rather by simply adding new modules or components
that follow the same architecture and design principles outlined in the
blueprint, making it easier for developers to contribute to the project and also
to ensure that the project can grow and adapt to new requirements and challenges
in the future without losing its core structure and design principles.
All operations performed by the code generated by the scripts must be efficient
and optimized for performance, using the best libraries and tools available for
Rust and Python development, and also following best practices for data
processing and machine learning pipelines, so we can ensure that the project can
handle large datasets and complex models without running into performance issues
or bottlenecks, and also to ensure that the project can scale and adapt to new
requirements and challenges in the future without losing its core structure and
design principles. multithreading and parallelism must be used where appropriate
to maximize performance and efficiency, and also to ensure that the project can
handle large datasets and complex models without running into performance issues
or bottlenecks, and also to ensure that the project can scale and adapt to new
requirements and challenges in the future without losing its core structure and
design principles - for example, by using Rayon for Rust and multiprocessing or
concurrent.futures for Python, and also by using efficient data formats and
libraries such as Arrow and NumPy to minimize memory usage and maximize data
processing speed, and also by using GPU acceleration where appropriate to
further improve performance and efficiency, so we can ensure that the project
can handle large datasets and complex models without running into performance
issues or bottlenecks, and also to ensure that the project can scale and adapt
to new requirements and challenges in the future without losing its core
structure and design principles, so the buckets in cloud storage can be listed
in multithreaded way, splitting the workload using the directory structure
as a guide to maximize performance and efficiency, opening multiple connections
and using multiple threads to list each directory in parallel.
so we can ensure that the codebase is maintainable, readable, and easy to
understand for developers of all levels of experience, and also to ensure that
the project can be easily extended and evolved over time without having to
rewrite large portions of the codebase or refactor it significantly, but rather
by simply adding new modules or components that follow the same architecture and
design principles outlined in the blueprint, making it easier for developers to
contribute to the project and also to ensure that the project can grow and adapt
to new requirements and challenges in the future without losing its core
structure and design principles.
```
