#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: set tabstop=2 shiftwidth=2 softtabstop=2 expandtab:


import logging
import os
import sys
import io
import json
import csv
import uuid
import signal
import threading
import multiprocessing as mp

from typing import Iterable, List, Tuple, Dict, Any, Optional, Set
from pathlib import Path
from queue import Queue
from threading import Thread
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq

from PIL import Image, ExifTags, UnidentifiedImageError

import torch
from torch import Tensor
from torchvision import models

from rich import pretty
from rich.console import Console
from rich.progress import (
  Progress,
  SpinnerColumn,
  BarColumn,
  TextColumn,
  TimeElapsedColumn,
)
from rich.panel import Panel

from sklearn.metrics.pairwise import cosine_similarity

from Subsea.config import CONFIG
from Subsea.storage import STORAGE
from Subsea.observability.tracing import TracingPolicy
from Subsea.storage import ObjectStore
from Subsea.storage import ObjectLister
from Subsea.storage import LocalObjectStore
from Subsea.storage import CheckpointStore


# ============================================================
# Shutdown handling
# ============================================================

SHUTDOWN : threading.Event = threading.Event( )

def handle_shutdown( signum : int, frame : Any ) -> None :
  log.warning(
    f'Received signal { signum } — shutting down gracefully'
  )
  SHUTDOWN.set( )

signal.signal( signal.SIGTERM, handle_shutdown )
signal.signal( signal.SIGINT, handle_shutdown )


# ============================================================
# Logging ( Rich )
# ============================================================

console : Console = Console( )

from rich.logging import RichHandler
logging.basicConfig(
  level = logging.INFO,
  format = '%(message)s',
  datefmt = '[%X]',
  handlers = [
    RichHandler(
      console = console,
      rich_tracebacks = True,
      show_level = True,
      show_path = False,
    )
  ],
)

log : logging.Logger = logging.getLogger( 'image-pipeline' )

logging.getLogger( 'boto3' ).setLevel( logging.WARNING )
logging.getLogger( 'botocore' ).setLevel( logging.WARNING )
logging.getLogger( 'botocore.credentials' ).setLevel( logging.WARNING )
logging.getLogger( 'botocore.utils' ).setLevel( logging.WARNING )


# ============================================================
# CUDA tuning ( main process only )
# ============================================================

torch.backends.cuda.matmul.allow_tf32 = True
torch.backends.cudnn.allow_tf32 = True
torch.backends.cudnn.benchmark = True

torch.cuda.set_device( 0 )
torch.set_num_threads( 1 )


# ============================================================
# Checkpoint helpers
# ============================================================

CHECKPOINT_FILE : str = f'{ CONFIG.paths.work_dir }/checkpoint.json'

def load_checkpoint( ) -> Set[ str ] :
  if not os.path.exists( CHECKPOINT_FILE ):
    return set( )
  with open( CHECKPOINT_FILE ) as f:
    return set( json.load( f ) )

def save_checkpoint( done : Set[ str ] ) -> None :
  log.info(
    f'Checkpoint saved | total_done = { len( done ) }'
  )
  with open( CHECKPOINT_FILE, 'w' ) as f:
    json.dump( sorted( done ), f )


# ============================================================
# Parquet dataset writer ( append‑safe )
# ============================================================

def append_to_parquet(
  rows : List[ Dict[ str, Any ] ],
  output_dir : str,
) -> None :

  if not rows:
    return

  os.makedirs( output_dir, exist_ok = True )

  table : pa.Table = pa.Table.from_pylist( rows )

  part_path : str = os.path.join(
    output_dir,
    f'part-{ uuid.uuid4( ).hex }.parquet',
  )

  pq.write_table(
    table,
    part_path,
    compression = 'zstd',
  )


# ============================================================
# Bad image logging
# ============================================================

BAD_IMAGE_LOG : str = f'{ CONFIG.paths.work_dir }/bad_images.jsonl'

def log_bad_image( path : str, reason : str ) -> None :

  record : Dict[ str, str ] = {
    'path': path,
    'reason': reason,
  }

  try:
    with open( BAD_IMAGE_LOG, 'a' ) as f:
      f.write( json.dumps( record ) + '\n' )
  except Exception:
    pass

  log.warning(
    f'[bad-image] skipped { path } → { reason }'
  )


# ============================================================
# Metadata extraction ( CPU )
# ============================================================

def extract_metadata_from_image(
  img : Image.Image,
  arr : np.ndarray,
  path : str,
) -> Dict[ str, Any ] :

  data : Dict[ str, Any ] = {
    'filename': str( path ),
    'format': img.format,
    'mode': img.mode,
    'width': img.size[ 0 ],
    'height': img.size[ 1 ],
    'mean': float( arr.mean( ) ),
    'std': float( arr.std( ) ),
    'min': int( arr.min( ) ),
    'max': int( arr.max( ) ),
  }

  exif_data : Dict[ str, Any ] = { }
  try:
    if hasattr( img, '_getexif' ) and img._getexif( ):
      for t, v in img._getexif( ).items( ):
        exif_data[
          ExifTags.TAGS.get( t, t )
        ] = v
  except Exception:
    pass

  data[ 'exif' ] = (
    json.dumps( exif_data )
    if exif_data
    else None
  )

  return data


# ============================================================
# CPU worker ( NO CUDA, NO TORCH )
# ============================================================

def process_one_image(
  path : str,
) -> Optional[ Tuple[ np.ndarray, Dict[ str, Any ] ] ] :

  os.environ[ 'CUDA_VISIBLE_DEVICES' ] = ''

  try:
    buf : io.BytesIO = io.BytesIO( )

    STORAGE.client( 'analise-dados' ).client.download_fileobj(
      'analise-dados',
      path[ len( 's3://analise-dados/' ) : ],
      buf,
    )

    buf.seek( 0 )
    img : Image.Image = Image.open( buf ).convert( 'RGB' )
    arr : np.ndarray = np.array( img, dtype = np.uint8 )

    meta : Dict[ str, Any ] = extract_metadata_from_image(
      img, arr, path
    )

    return arr, meta

  except (
    Image.DecompressionBombError,
    UnidentifiedImageError,
    OSError,
    ValueError,
  ) as e:

    log_bad_image( path, str( e ) )
    return None


# ============================================================
# GPU + CPU pipeline
# ============================================================

def process_images_parallel(
  locations : List[ str ],
) -> Tuple[
  List[ Dict[ str, Any ] ],
  List[ np.ndarray ],
] :

  try:

    done : Set[ str ] = load_checkpoint( )

    locations = [
      p for p in locations
      if p not in done
    ]

    log.info(
      f'Pipeline start | remaining = { len( locations ) }'
    )

    device : str = 'cuda'
    cpu_workers : int = 32
    micro_batch_size : int = 32
    max_inflight : int = 4096

    output_parquet : str = (
      f'{ CONFIG.paths.work_dir }/embeddings'
    )

    model : torch.nn.Module = models.resnet50(
      weights = 'IMAGENET1K_V2'
    )
    model.to( device )
    model.eval( )

    image_queue : Queue = Queue( maxsize = max_inflight )

    def image_producer( ) -> None :

      log.info(
        f'Producer started | cpu_workers = { cpu_workers }'
      )

      with ProcessPoolExecutor(
        max_workers = cpu_workers
      ) as executor:

        for item in executor.map(
          process_one_image,
          locations,
          chunksize = 2,
        ):

          if SHUTDOWN.is_set( ):
            break

          if item is not None:
            image_queue.put( item )

      image_queue.put( None )
      log.info( 'Producer finished' )

    producer : Thread = Thread(
      target = image_producer,
      daemon = True,
    )
    producer.start( )

    metadata : List[ Dict[ str, Any ] ] = [ ]
    embeddings : List[ np.ndarray ] = [ ]

    with Progress(
      SpinnerColumn( ),
      TextColumn(
        '[progress.description]{task.description}'
      ),
      BarColumn( ),
      TimeElapsedColumn( ),
    ) as progress:

      task = progress.add_task(
        'Processing images...',
        total = len( locations ),
      )

      tensors : List[ np.ndarray ] = [ ]
      metas : List[ Dict[ str, Any ] ] = [ ]

      while True:

        if SHUTDOWN.is_set( ):
          break

        item = image_queue.get( )

        if item is None:
          break

        arr, meta = item
        tensors.append( arr )
        metas.append( meta )

        if len( tensors ) >= micro_batch_size:

          gpu_tensors : List[ Tensor ] = [ ]

          for a in tensors:

            t : Tensor = torch.from_numpy( a ).to(
              device,
              non_blocking = True,
            )

            t = t.permute( 2, 0, 1 ).float( ) / 255.0

            t = torch.nn.functional.interpolate(
              t.unsqueeze( 0 ),
              size = ( 224, 224 ),
              mode = 'bilinear',
              align_corners = False,
            ).squeeze( 0 )

            gpu_tensors.append( t )

          batch : Tensor = torch.stack( gpu_tensors )

          with torch.no_grad( ):
            with torch.cuda.amp.autocast( ):
              embs : np.ndarray = (
                model( batch ).cpu( ).numpy( )
              )

          rows : List[ Dict[ str, Any ] ] = [ ]

          for m, e in zip( metas, embs ):

            r : Dict[ str, Any ] = dict( m )
            r[ 'embedding' ] = e.tolist( )
            rows.append( r )

            metadata.append( m )
            embeddings.append( e )
            done.add( m[ 'filename' ] )

            progress.update( task, advance = 1 )

          append_to_parquet(
            rows,
            output_parquet,
          )
          save_checkpoint( done )

          tensors.clear( )
          metas.clear( )

    producer.join( )

    log.info(
      f'Pipeline finished | processed = { len( metadata ) }'
    )

    return metadata, embeddings

  except Exception:

    log.exception( 'Fatal pipeline error' )
    raise


# ============================================================
# ImagePipeline entry point ( PRESERVED )
# ============================================================

class ImagePipeline :

  '''
  Backend‑agnostic image discovery pipeline.
  '''

  IMAGE_EXTENSIONS : Tuple[ str, ... ] = (
    '.jpg',
    '.jpeg',
    '.png',
    '.webp',
    '.tif',
    '.tiff',
  )

  def __init__(
    self,
    store : ObjectStore,
    lister : ObjectLister,
    bucket_name : str,
    logger : Optional[ logging.Logger ] = None,
  ) -> None :

    self.store = store
    self.lister = lister
    self.bucket = bucket_name

    self.log = logger or logging.getLogger(
      'ImagePipeline'
    )

    self.tracing = TracingPolicy(
      name = 'ImagePipeline',
      logger = self.log,
    )

    mp.set_start_method( 'spawn', force = True )

  def run(
    self,
    prefix : str = '',
  ) -> pa.Table :

    with self.tracing.operation(
      'run',
      prefix = prefix,
    ) :

      checkpoint_store = LocalObjectStore(
        root = str( CONFIG.paths.checkpoint_dir ),
        logger = self.log,
      )

      checkpoint = CheckpointStore(
        store = checkpoint_store,
        checkpoint_key = f'image_keys_{ prefix or "root" }.txt',
        logger = self.log,
      )

      #if checkpoint.exists( ):
      #  keys = checkpoint.load_lines( )
      #else:
      keys = list(
        self.lister.list_objects( prefix )
      )
      #  checkpoint.save_lines( keys )

    with self.tracing.operation(
      '>> build_arrow_table <<',
      rows = len( keys ),
    ) :

      locations : List[ str ] = [
        f's3://{ self.bucket }/{ k }'
        for k in keys
        if k.lower( ).endswith(
          self.IMAGE_EXTENSIONS
        )
      ]

      print( len( locations ) )

      #metadata, embeddings = process_images_parallel(
      #  locations
      #)

      #embeddings = np.asarray( embeddings )

      #similar = find_similar_images(
      #  embeddings,
      #  locations,
      #)

      #duplicates = find_duplicates( similar )

      #show_final_panel(
      #  total_images = len( locations ),
      #  similar_count = len( similar ),
      #  duplicates_count = len( duplicates ),
      #)

      #save_reports(
      #  metadata,
      #  similar,
      #  duplicates,
      #)

      return pa.Table.from_arrays(
        [
          pa.array(
            locations,
            type = pa.string( ),
          )
        ],
        names = [ 'image_location' ],
      )


# ============================================================
# Analysis helpers
# ============================================================

def find_similar_images(
  embeddings : np.ndarray,
  paths : List[ str ],
  threshold : float = 0.90,
) -> List[ Tuple[ str, str, float ] ] :

  sim : np.ndarray = cosine_similarity( embeddings )
  n : int = len( paths )
  pairs : List[ Tuple[ str, str, float ] ] = [ ]

  for i in range( n ):
    for j in range( i + 1, n ):
      if sim[ i, j ] >= threshold:
        pairs.append(
          (
            str( paths[ i ] ),
            str( paths[ j ] ),
            float( sim[ i, j ] ),
          )
        )

  return pairs

def find_duplicates(
  similar_pairs : List[ Tuple[ str, str, float ] ],
  strong_threshold : float = 0.98,
) -> List[ Tuple[ str, str, float ] ] :

  return [
    p for p in similar_pairs
    if p[ 2 ] >= strong_threshold
  ]


# ============================================================
# Presentation / reports
# ============================================================

def show_final_panel(
  total_images : int,
  similar_count : int,
  duplicates_count : int,
) -> None :

  panel = Panel.fit(
    f'[bold cyan]Final Pipeline Summary[/]\n\n'
    f'[white]Images processed:[/] [bold]{ total_images }[/]\n'
    f'[white]Similar pairs:[/] [bold]{ similar_count }[/]\n'
    f'[white]Duplicate pairs:[/] [bold]{ duplicates_count }[/]\n',
    title = '[green]Pipeline Completed[/]',
    border_style = 'bright_blue',
  )
  console.print( panel )

def save_reports(
  metadata : List[ Dict[ str, Any ] ],
  similar : List[ Tuple[ str, str, float ] ],
  duplicates : List[ Tuple[ str, str, float ] ],
) -> None :

  keys = sorted(
    { k for m in metadata for k in m if k != 'exif' }
  )

  with open( 'image_summary.csv', 'w', newline = '' ) as f:
    writer = csv.writer( f )
    writer.writerow( keys )
    for m in metadata:
      writer.writerow(
        [ m.get( k, '' ) for k in keys ]
      )

  with open( 'similar_images.json', 'w' ) as f:
    json.dump( similar, f, indent = 2 )

  with open( 'duplicate_images.json', 'w' ) as f:
    json.dump( duplicates, f, indent = 2 )


# ============================================================
# END
# ============================================================

pretty.install( )
