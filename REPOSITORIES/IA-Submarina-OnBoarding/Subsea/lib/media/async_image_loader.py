#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: set tabstop=2 shiftwidth=2 softtabstop=2 expandtab:


import asyncio
from io import BytesIO

import numpy as np
from PIL import Image as PILImage

from .image import Image


class AsyncImageLoader :

  def __init__(
    self,
    storage,
    *,
    cache = None,
    concurrency : int = 32,
  ):

    self._storage = storage
    self._cache = cache
    self._sem = asyncio.Semaphore(
      concurrency
    )

  async def _load_one(
    self,
    key : str,
  ) -> Image :

    if self._cache:
      cached = self._cache.get( key )
      if cached is not None:
        return Image( array = cached )

    async with self._sem:
      data = await self._storage.read_bytes_async(
        key
      )

    pil = PILImage.open(
      BytesIO( data )
    ).convert( 'RGB' )

    arr = np.asarray( pil )

    if self._cache:
      self._cache.put( key, arr )

    return Image(
      array = arr,
      path = key,
    )

  async def load_many(
    self,
    keys,
  ):

    tasks = [
      asyncio.create_task(
        self._load_one( k )
      )
      for k in keys
    ]

    return await asyncio.gather(
      *tasks
    )
