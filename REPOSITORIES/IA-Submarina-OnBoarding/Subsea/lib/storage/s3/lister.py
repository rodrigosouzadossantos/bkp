#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: set tabstop=2 shiftwidth=2 softtabstop=2 expandtab:


import logging

from typing import Iterable
from concurrent.futures import ThreadPoolExecutor, as_completed

from .store import S3ObjectStore


class S3ParallelLister :

  '''
  S3-specific high-performance object lister.

  Uses prefix partitioning + parallel pagination.
  '''

  def __init__(
    self,
    store : S3ObjectStore,
    max_workers : int = 32,
    logger : logging.Logger | None = None,
  ) :

    self.store = store
    self.max_workers = max_workers

    self.log = logger or logging.getLogger(
      f'S3ParallelLister[{store.client.bucket}]'
    )


  def _list_prefix(
    self,
    prefix : str,
  ) -> list[ str ] :

    keys = [ ]

    for page in self.store.paginate_objects(
      prefix
    ) :

      for obj in page.get(
        'Contents',
        [ ]
      ) :

        keys.append(
          obj[ 'Key' ]
        )

    return keys


  def list_objects(
    self,
    prefix : str = '',
  ) -> Iterable[ str ] :

    prefixes = (
      [ prefix ] if prefix is not None
          else list( self.store.list_common_prefixes( ) or [ ] )
    )

    with ThreadPoolExecutor(
      max_workers = self.max_workers
    ) as exe :

      futures = {
        exe.submit(
          self._list_prefix,
          p,
        ) : p
        for p in prefixes
      }

      for future in as_completed(
        futures
      ) :

        for key in future.result( ) :
          yield key
