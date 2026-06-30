#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: set tabstop=2 shiftwidth=2 softtabstop=2 expandtab:

import threading

import numpy as np

from typing import List, Tuple, Dict, Any

from queue import Queue
from threading import Thread
from concurrent.futures import ProcessPoolExecutor

import torch
from torch import Tensor
from torchvision import models

from rich.progress import (
  Progress,
  SpinnerColumn,
  BarColumn,
  TextColumn,
  TimeElapsedColumn,
)

from Subsea.config import CONFIG

from .image_workers import process_one_image
from .image_io import (
  append_to_parquet,
  load_checkpoint,
  save_checkpoint,
)

SHUTDOWN = threading.Event( )


def process_images_parallel(
  locations : List[ str ],
) -> Tuple[
  List[ Dict[ str, Any ] ],
  List[ np.ndarray ],
] :

  done = load_checkpoint( )

  locations = [
    p for p in locations
    if p not in done
  ]

  device = 'cuda'
  cpu_workers = 32
  micro_batch_size = 32
  max_inflight = 4096

  output_parquet = (
    f'{ CONFIG.paths.work_dir }/embeddings'
  )

  model = models.resnet50(
    weights = 'IMAGENET1K_V2'
  )
  model.to( device )
  model.eval( )

  image_queue = Queue( maxsize = max_inflight )

  def image_producer( ) -> None :

    with ProcessPoolExecutor(
      max_workers = cpu_workers
    ) as executor:

      for item in executor.map(
        process_one_image,
        locations,
        chunksize = 2,
      ):
        if item is not None:
          image_queue.put( item )

    image_queue.put( None )

  producer = Thread(
    target = image_producer,
    daemon = True,
  )
  producer.start( )

  metadata = [ ]
  embeddings = [ ]

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

    tensors = [ ]
    metas = [ ]

    while True:

      item = image_queue.get( )

      if item is None:
        break

      arr, meta = item
      tensors.append( arr )
      metas.append( meta )

      if len( tensors ) >= micro_batch_size:

        gpu_tensors = [ ]

        for a in tensors:

          t = torch.from_numpy( a ).to(
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

        batch = torch.stack( gpu_tensors )

        with torch.no_grad( ):
          with torch.cuda.amp.autocast( ):
            embs = model( batch ).cpu( ).numpy( )

        rows = [ ]

        for m, e in zip( metas, embs ):

          r = dict( m )
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

  return metadata, embeddings

