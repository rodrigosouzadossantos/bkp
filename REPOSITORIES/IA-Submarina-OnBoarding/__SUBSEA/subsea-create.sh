#!/usr/bin/env bash

set -e

PROJECT='SUBSEA'

echo 'Initializing Subsea project (blank-line safe)...'

mkdir -p \
  ${PROJECT}/storage \
  ${PROJECT}/media \
  ${PROJECT}/cv \
  ${PROJECT}/plotting \
  ${PROJECT}/pipelines \
  ${PROJECT}/docs


write_file() {
  local file="$1"
  local content="$2"

  if [ ! -f "$file" ]; then
    echo "Creating $file"
    cat <<EOF > "$file"
$content
EOF
  else
    echo "Skipping $file (already exists)"
  fi
}


# ======================
# ROOT DOCUMENTATION
# ======================

write_file "${PROJECT}/README.md" \
"# Subsea

Subsea is a modular Computer Vision runtime focused on large-scale
image and video processing with observability, transactional
checkpoints, and GPU acceleration.

## Key Features

- Semantic, class-driven architecture
- Crash-safe and resumable pipelines
- Polars + Parquet as default data format
- CPU multiprocessing and GPU/CUDA support
- Rich-based UI with full logging

## Quick Start

\`\`\`bash
python -m Subsea
\`\`\`

See docs/quickstart.md for usage examples.

"


write_file "${PROJECT}/PROJECT.md" \
"# Subsea Project Overview

## Mission

Provide a robust, observable, and extensible runtime
for Computer Vision pipelines at scale.

## What Subsea Is

- A CV execution environment
- A pipeline orchestration framework
- A foundation for image and video analytics

## What Subsea Is Not

- Not a web framework
- Not a notebook-only tool
- Not a low-level CV library

"


write_file "${PROJECT}/ARCHITECTURE.md" \
"# Subsea Architecture

## Core Principles

1. Local-first execution
2. Best-effort remote replication
3. Observability by default
4. Semantic class boundaries
5. GPU acceleration whenever available

## Layers

- Media Layer (image / video access)
- CV Operations Layer
- Runtime Layer
- Storage Layer
- Pipeline Layer

## Execution Flow

Input → Media → CV → Runtime → Storage → Observability

"


write_file "${PROJECT}/CONTRIBUTING.md" \
"# Contributing to Subsea

## Rules

- Every public class must have a clear semantic meaning
- Logging is mandatory
- Parquet is the default persistence format
- No business logic outside classes

## Style

- Explicit spacing
- No mandatory auto-formatters
- Readability over brevity

"


# ======================
# DOCS
# ======================

write_file "${PROJECT}/docs/index.md" \
"# Subsea Documentation

## Contents

- installation.md
- quickstart.md
- pipelines.md
- runtime.md
- storage.md
- observability.md
- roadmap.md

"


write_file "${PROJECT}/docs/installation.md" \
"# Installation

## Requirements

- Python 3.10+
- OpenCV (CUDA optional)
- Polars
- Rich

## Install Dependencies

\`\`\`bash
pip install polars rich opencv-python
\`\`\`

"


write_file "${PROJECT}/docs/quickstart.md" \
"# Quickstart

\`\`\`python
from Subsea.pipelines.image_pipeline import ImagePipeline

pipeline = ImagePipeline()

df = pipeline.run( [ 'image1.jpg', 'image2.jpg' ] )

print( df )
\`\`\`

"


write_file "${PROJECT}/docs/pipelines.md" \
"# Pipelines

Pipelines orchestrate media access, CV operations,
runtime execution, and structured output.

"


write_file "${PROJECT}/docs/runtime.md" \
"# Runtime

The runtime decides how work is executed:

- CPU multiprocessing
- GPU acceleration
- Automatic fallback

"


write_file "${PROJECT}/docs/storage.md" \
"# Storage

Default format: Parquet

Default engine: Polars

Other supported engines:

- DuckDB
- PySpark

"


write_file "${PROJECT}/docs/observability.md" \
"# Observability

All stages are observable:

- start and end events
- execution time
- warnings and errors

Implemented via decorators and logging.

"


write_file "${PROJECT}/docs/roadmap.md" \
"# Roadmap

## Short Term

- Video pipelines
- Transactional checkpoints

## Medium Term

- Feature stores
- Similarity search

## Long Term

- Distributed execution
- Plugin system

"


# ======================
# PYTHON MODULE
# ======================

write_file "${PROJECT}/__init__.py" \
"# Subsea package

"


write_file "${PROJECT}/__main__.py" \
"from Subsea.logging import SubseaLogger
from Subsea.pipelines.image_pipeline import ImagePipeline

def main( ) :

  SubseaLogger.setup()

  pipeline = ImagePipeline()

  df = pipeline.run( [] )

  print( df )

if __name__ == '__main__' :

  main()

"


write_file "${PROJECT}/config.py" \
"from pathlib import Path

class SubseaConfig :

  WORK_DIR = Path( './work' )
  LOG_DIR  = WORK_DIR / 'logs'
  DATA_DIR = WORK_DIR / 'data'

  ENABLE_GPU = True

  @classmethod
  def ensure_dirs( cls ) :

    for d in [ cls.WORK_DIR, cls.LOG_DIR, cls.DATA_DIR ] :
      d.mkdir( parents = True, exist_ok = True )

"


write_file "${PROJECT}/logging.py" \
"import logging

from rich.console import Console
from rich.logging import RichHandler

from .config import SubseaConfig

class SubseaLogger :

  console = Console()

  @classmethod
  def setup( cls ) :

    SubseaConfig.ensure_dirs()

    logging.basicConfig(
      level = logging.INFO,
      format = '%(asctime)s %(levelname)s %(message)s',
      handlers = [
        RichHandler( console = cls.console ),
        logging.FileHandler(
          SubseaConfig.LOG_DIR / 'processing.log'
        )
      ]
    )

    return logging.getLogger( 'Subsea' )

"


write_file "${PROJECT}/decorators.py" \
"import time
import logging

from functools import wraps

def observed( name = None ) :

  def decorator( fn ) :

    label = name or fn.__name__

    @wraps( fn )
    def wrapper( *args, **kwargs ) :

      log = logging.getLogger( 'Subsea' )
      start = time.time()

      log.info( f'start {label}' )

      try :
        return fn( *args, **kwargs )
      finally :
        elapsed = time.time() - start
        log.info( f'end {label} elapsed={elapsed:.2f}s' )

    return wrapper

  return decorator

"


write_file "${PROJECT}/runtime.py" \
"import os

from concurrent.futures import ProcessPoolExecutor

class ExecutionRuntime :

  def __init__( self, max_workers = None ) :

    self.max_workers = (
      max_workers or max( 1, os.cpu_count() - 1 )
    )

  def map_cpu( self, fn, items ) :

    with ProcessPoolExecutor( self.max_workers ) as exe :
      return list( exe.map( fn, items ) )

  def gpu_available( self ) :

    try :
      import cv2
      return cv2.cuda.getCudaEnabledDeviceCount() > 0
    except Exception :
      return False

"


write_file "${PROJECT}/media/image.py" \
"import cv2
from pathlib import Path

class ImageSource :

  def __init__( self, paths ) :

    self.paths = [ Path( p ) for p in paths ]

  def __iter__( self ) :

    for p in self.paths :
      yield p, cv2.imread( str( p ) )

"


write_file "${PROJECT}/cv/blur.py" \
"import cv2

class BlurDetector :

  def score( self, gray ) :

    if cv2.cuda.getCudaEnabledDeviceCount() > 0 :
      g = cv2.cuda_GpuMat()
      g.upload( gray )
      lap = cv2.cuda.Laplacian( g, cv2.CV_32F )
      return cv2.cuda.sum( lap )[ 0 ]

    return cv2.Laplacian( gray, cv2.CV_32F ).var()

"


write_file "${PROJECT}/pipelines/image_pipeline.py" \
"import cv2
import polars as pl

from ..decorators import observed
from ..media.image import ImageSource
from ..cv.blur import BlurDetector

class ImagePipeline :

  def __init__( self ) :

    self.blur = BlurDetector()

  @observed( 'image_pipeline.run' )
  def run( self, paths ) :

    rows = []

    for path, img in ImageSource( paths ) :

      if img is None :
        continue

      gray = cv2.cvtColor( img, cv2.COLOR_BGR2GRAY )
      score = self.blur.score( gray )

      rows.append( {
        'path': str( path ),
        'blur_score': score
      } )

    return pl.DataFrame( rows )

"


echo 'Subsea project initialized successfully (no empty lines).'
