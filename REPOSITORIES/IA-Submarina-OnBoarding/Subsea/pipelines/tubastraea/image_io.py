#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: set tabstop=2 shiftwidth=2 softtabstop=2 expandtab:


import os
import json
import uuid
import logging

import pyarrow as pa
import pyarrow.parquet as pq

from typing import List, Dict, Any, Set

from rich.console import Console

from Subsea.config import CONFIG


log = logging.getLogger( 'image-pipeline' )
console = Console( )


CHECKPOINT_FILE = f'{ CONFIG.paths.work_dir }/checkpoint.json'
BAD_IMAGE_LOG = f'{ CONFIG.paths.work_dir }/bad_images.jsonl'


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


def append_to_parquet(
  rows : List[ Dict[ str, Any ] ],
  output_dir : str,
) -> None :

  if not rows:
    return

  os.makedirs( output_dir, exist_ok = True )

  table = pa.Table.from_pylist( rows )

  part_path = os.path.join(
    output_dir,
    f'part-{ uuid.uuid4( ).hex }.parquet',
  )

  pq.write_table(
    table,
    part_path,
    compression = 'zstd',
  )


def log_bad_image(
  path : str,
  reason : str,
) -> None :

  record = {
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


def show_final_panel(
  total_images : int,
  similar_count : int,
  duplicates_count : int,
) -> None :

  from rich.panel import Panel

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
  similar : List,
  duplicates : List,
) -> None :

  import csv

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

