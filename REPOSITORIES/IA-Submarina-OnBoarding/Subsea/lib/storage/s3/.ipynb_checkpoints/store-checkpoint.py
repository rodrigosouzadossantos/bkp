#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: set tabstop=2 shiftwidth=2 softtabstop=2 expandtab:


import io
import logging

from typing import Iterable, List

from Subsea.storage.object_store import ObjectStore
from Subsea.storage.s3 import S3Client
from Subsea.observability.tracing import TracingPolicy


class S3ObjectStore( ObjectStore ) :

  '''
  S3-backed ObjectStore implementation.

  Wraps S3Client and exposes ObjectStore semantics.
  '''

  def __init__(
    self,
    client : S3Client,
    logger : logging.Logger | None = None,
    tracing : bool = True,
  ) :

    self.client = client

    self.log = logger or logging.getLogger(
      f'S3ObjectStore[{client.bucket}]'
    )

    self.tracing = TracingPolicy(
      name = 'S3ObjectStore',
      logger = self.log,
      enabled = tracing,
    )

    self.log.info(
      'Initialized S3ObjectStore bucket=%s',
      client.bucket,
    )


  def get_paginator(
    self,
    operation : str,
  ):

    return self.client.get_paginator(
      operation
    )

  def exists( self, key : str ) -> bool :

    self.log.debug(
      'exists key=%s',
      key,
    )

    return self.client.exists(
      key
    )


  def open_writer( self, key : str ) -> io.BufferedWriter :

    return self.client.open_multipart_writer( key )


  def open_reader( self, key : str ) -> io.BufferedReader :

    return self.client.open_stream_reader( key )


  def download(
    self,
    key : str,
    dest_path : str,
  ) -> None :

    with self.tracing.operation(
      'download',
      key = key,
      dest = dest_path,
    ) :

      self.client.download_file(
        key,
        dest_path,
      )


  def upload(
    self,
    src_path : str,
    key : str,
  ) -> None :

    with self.tracing.operation(
      'upload',
      src = src_path,
      key = key,
    ) :

      self.client.upload_file(
        src_path,
        key,
      )


  def stream(
    self,
    key : str,
    chunk_size : int = 8 * 1024 * 1024,
  ) -> Iterable[ bytes ] :

    def generator() :

      with self.tracing.operation(
        'stream',
        key = key,
        chunk_size = chunk_size,
      ) :

        for chunk in self.client.stream(
          key,
          chunk_size,
        ) :

          yield chunk

    return generator()


  def list(
    self,
    prefix : str = '',
    suffix : str | None = None,
  ) -> Iterable[ str ] :

    def generator() :

      with self.tracing.operation(
        'list',
        prefix = prefix,
        suffix = suffix,
      ) :

        for key in self.client.list(
          prefix,
          suffix,
        ) :

          yield key

    return generator()


  def delete(
    self,
    key : str,
    version_id : str | None = None,
  ) -> None :

    with self.tracing.operation(
      'delete',
      key = key,
      version_id = version_id,
    ) :

      self.client.delete(
        key,
        version_id,
      )

  def list_common_prefixes(
    self,
    delimiter : str = '/',
  ) -> List[ str ] :

    response = self.client.client.list_objects_v2(
      Bucket = self.client.bucket,
      Delimiter = delimiter,
    )

    return [
      p[ 'Prefix' ]
      for p in response.get(
        'CommonPrefixes',
        [ ]
      )
    ]

  def paginate_objects(
    self,
    prefix : str,
  ) :

    '''
    Yield pages of objects under a prefix.

    This is the ONLY place that knows boto3 pagination.
    '''

    for page in self.client.paginate_objects(
      prefix
    ) :

      yield page

