#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: set tabstop=2 shiftwidth=2 softtabstop=2 expandtab:


from io import BytesIO
from functools import lru_cache
from concurrent.futures import ThreadPoolExecutor

import numpy as np
from PIL import Image as PILImage

from .image import Image


class ImageLoader :

  def __init__(
    self,
    storage,
    *,
    cache = None,
    max_workers : int = 8,
  ) -> None :

    self._storage = storage
    self._cache = cache

    self._pool = ThreadPoolExecutor(
      max_workers = max_workers
    )

  def _load_one(
    self,
    key : str,
  ) -> Image :

    if self._cache:
      cached = self._cache.get( key )
      if cached is not None:
        return Image( array = cached )

    # ----
    #data = self._storage.read_bytes( key )

    #pil = PILImage.open(
    #  BytesIO( data )
    #).convert( 'RGB' )

    buf : BytesIO = BytesIO( )

    self._storage.client( 'analise-dados' ).client.download_fileobj(
      'analise-dados',
      key,
      buf,
    )

    pil = PILImage.open( buf ).convert( 'RGB' )
    # ----

    arr = np.asarray( pil )

    if self._cache:
      self._cache.put( key, arr )

    return Image(
      array = arr,
      path = key,
    )

  def load(
    self,
    key : str,
  ) -> Image :

    return self._load_one( key )

  def load_many(
    self,
    keys,
  ):

    futures = [
      self._pool.submit(
        self._load_one,
        k,
      )
      for k in keys
    ]

    return [
      f.result( )
      for f in futures
    ]

  def prefetch(
    self,
    keys,
  ):

    for k in keys:
      self._pool.submit(
        self._load_one,
        k,
      )
