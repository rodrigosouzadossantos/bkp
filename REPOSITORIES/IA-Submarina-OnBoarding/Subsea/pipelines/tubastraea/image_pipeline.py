#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: set tabstop=2 shiftwidth=2 softtabstop=2 expandtab:


import multiprocessing as mp

import numpy as np
import pyarrow as pa

from typing import List

from Subsea.observability.tracing import TracingPolicy
from Subsea.storage.object_store import ObjectStore
from Subsea.storage.object_lister import ObjectLister
from Subsea.storage.local_store import LocalObjectStore
from Subsea.storage.checkpoint_store import CheckpointStore

from .image_gpu import process_images_parallel
from .image_analysis import (
  find_similar_images,
  find_duplicates,
)
from .image_io import (
  show_final_panel,
  save_reports,
)


class ImagePipeline :

  IMAGE_EXTENSIONS = (
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
    logger = None,
  ) :

    self.store = store
    self.lister = lister
    self.bucket = bucket_name

    self.log = logger

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

      if checkpoint.exists( ):
        keys = checkpoint.load_lines( )
      else:
        keys = list(
          self.lister.list_objects( prefix )
        )
        checkpoint.save_lines( keys )

    with self.tracing.operation(
      'build_arrow_table',
      rows = len( keys ),
    ) :

      locations : List[ str ] = [
        f's3://{ self.bucket }/{ k }'
        for k in keys
        if k.lower( ).endswith(
          self.IMAGE_EXTENSIONS
        )
      ]

      metadata, embeddings = process_images_parallel(
        locations
      )

      embeddings = np.asarray( embeddings )

      similar = find_similar_images(
        embeddings,
        locations,
      )

      duplicates = find_duplicates( similar )

      show_final_panel(
        total_images = len( locations ),
        similar_count = len( similar ),
        duplicates_count = len( duplicates ),
      )

      save_reports(
        metadata,
        similar,
        duplicates,
      )

      return pa.Table.from_arrays(
        [
          pa.array(
            locations,
            type = pa.string( ),
          )
        ],
        names = [ 'image_location' ],
      )

