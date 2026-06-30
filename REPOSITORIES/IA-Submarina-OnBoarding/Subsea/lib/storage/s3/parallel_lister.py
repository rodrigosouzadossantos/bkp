#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: set tabstop=2 shiftwidth=2 softtabstop=2 expandtab:


import logging

from concurrent.futures import ThreadPoolExecutor, as_completed

from .storage import S3ObjectStore


class S3ParallelLister :

  '''
  Parallel S3 object lister using prefix partitioning.

  This is an S3‑specific optimization helper.
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

    for page in self.client.paginate_objects(
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


  def list_all(
    self,
  ) -> list[ str ] :

    self.log.info(
      'Listing S3 prefixes for bucket=%s',
      self.store.client.bucket,
    )

    prefixes = self.store.list_common_prefixes( )

    self.log.info(
      'Found %d prefixes',
      len( prefixes ),
    )

    all_keys : list[ str ] = [ ]

    with ThreadPoolExecutor(
      max_workers = self.max_workers
    ) as exe :

      futures = {
        exe.submit(
          self._list_prefix,
          prefix,
        ) : prefix
        for prefix in prefixes
      }

      for future in as_completed(
        futures
      ) :

        prefix = futures[ future ]

        try :

          keys = future.result( )

          self.log.info(
            'Prefix %s -> %d objects',
            prefix,
            len( keys ),
          )

          all_keys.extend(
            keys
          )

        except Exception as e :

          self.log.error(
            'Failed listing prefix %s: %s',
            prefix,
            e,
          )

          raise

    return all_keys

