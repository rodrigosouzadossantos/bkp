#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: set tabstop=2 shiftwidth=2 softtabstop=2 expandtab:


import os
import logging

from typing import Iterable, BinaryIO

from .object_store import ObjectStore
from Subsea.observability.tracing import TracingPolicy


class LocalObjectStore( ObjectStore ) :

  """
  Local filesystem implementation of ObjectStore.

  Intended for:
  - development
  - testing
  - local batch processing
  """

  def __init__(
    self,
    root : str,
    logger : logging.Logger | None = None,
    tracing : bool = True,
  ) :

    self.root = root

    self.log = logger or logging.getLogger(
      f'LocalObjectStore[{root}]'
    )

    self.tracing = TracingPolicy(
      name = 'LocalObjectStore',
      logger = self.log,
      enabled = tracing,
    )

    self.log.info(
      'Initialized LocalObjectStore root=%s',
      root,
    )


  def _path( self, key : str ) -> str :

    return os.path.join(
      self.root,
      key,
    )


  def exists( self, key : str ) -> bool :

    path = self._path( key )

    exists = os.path.exists( path )

    self.log.debug(
      'exists key=%s path=%s result=%s',
      key,
      path,
      exists,
    )

    return exists


  def open_writer( self, key : str ) -> BinaryIO :

    path = self._path( key )
    os.makedirs( os.path.dirname( path ), exist_ok = True )
    return open( path, 'wb' )


  def open_reader( self, key : str ) -> BinaryIO :

    return open( self._path( key ), 'rb' )


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

      src = self._path( key )

      if not os.path.exists( src ) :
        raise FileNotFoundError( src )

      os.makedirs(
        os.path.dirname( dest_path ) or '.',
        exist_ok = True,
      )

      self.log.info(
        'Copying %s -> %s',
        src,
        dest_path,
      )

      with open( src, 'rb' ) as fsrc, \
           open( dest_path, 'wb' ) as fdst :

        while True :

          chunk = fsrc.read(
            8 * 1024 * 1024
          )

          if not chunk :
            break

          fdst.write( chunk )


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

      if not os.path.exists( src_path ) :
        raise FileNotFoundError( src_path )

      dst = self._path( key )

      os.makedirs(
        os.path.dirname( dst ) or '.',
        exist_ok = True,
      )

      self.log.info(
        'Copying %s -> %s',
        src_path,
        dst,
      )

      with open( src_path, 'rb' ) as fsrc, \
           open( dst, 'wb' ) as fdst :

        while True :

          chunk = fsrc.read(
            8 * 1024 * 1024
          )

          if not chunk :
            break

          fdst.write( chunk )


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

        path = self._path( key )

        self.log.info(
          'Streaming %s',
          path,
        )

        with open( path, 'rb' ) as f :

          while True :

            chunk = f.read(
              chunk_size
            )

            if not chunk :
              break

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

        base = self._path(
          prefix
        )

        self.log.info(
          'Listing under %s',
          base,
        )

        if not os.path.exists( base ) :
          return

        for root, _, files in os.walk(
          base
        ) :

          for name in files :

            if suffix and not name.endswith(
              suffix
            ) :
              continue

            full = os.path.join(
              root,
              name,
            )

            yield os.path.relpath(
              full,
              self.root,
            )

    return generator()


  def delete(
    self,
    key : str,
    version_id : str | None = None,
  ) -> None :

    with self.tracing.operation(
      'delete',
      key = key,
    ) :

      path = self._path( key )

      if not os.path.exists( path ) :

        self.log.warning(
          'File already deleted: %s',
          path,
        )

        return

      self.log.info(
        'Deleting %s',
        path,
      )

      os.remove( path )

