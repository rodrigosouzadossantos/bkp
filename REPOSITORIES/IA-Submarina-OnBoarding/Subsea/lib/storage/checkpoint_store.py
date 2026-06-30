#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: set tabstop=2 shiftwidth=2 softtabstop=2 expandtab:


import logging

from typing import Iterable, List, Callable, TypeVar

from Subsea.observability.tracing import TracingPolicy
from .object_store import ObjectStore


T = TypeVar( 'T' )


class CheckpointStore :

  '''
  Generic ObjectStore-backed checkpoint manager.

  A checkpoint is identified by a key and stores
  serialized state.

  This class is intentionally generic.
  '''

  def __init__(
    self,
    store : ObjectStore,
    checkpoint_key : str,
    logger : logging.Logger | None = None,
    tracing : bool = True,
  ) :

    self.store = store
    self.key = checkpoint_key

    self.log = logger or logging.getLogger(
      f'CheckpointStore[{checkpoint_key}]'
    )

    self.tracing = TracingPolicy(
      name = 'CheckpointStore',
      logger = self.log,
      enabled = tracing,
    )


  def exists( self ) -> bool :

    return self.store.exists(
      self.key
    )


  def load_lines( self ) -> List[ str ] :

    '''
    Load checkpoint as newline-delimited text.

    This is suitable for:
    - object keys
    - ids
    - filenames
    '''

    with self.tracing.operation(
      'load_lines',
      key = self.key,
    ) :

      if not self.exists() :

        self.log.info(
          'No checkpoint found'
        )

        return [ ]

      self.log.info(
        'Loading checkpoint %s',
        self.key,
      )

      lines : List[ str ] = [ ]

      with self.store.open_reader(
        self.key
      ) as reader :

        for raw in reader :

          line = raw.decode(
            'utf-8'
          ).strip()

          if line :
            lines.append( line )

      return lines


  def save_lines(
    self,
    lines : Iterable[ str ],
  ) -> None :

    '''
    Save checkpoint as newline-delimited text.
    '''

    with self.tracing.operation(
      'save_lines',
      key = self.key,
    ) :

      self.log.info(
        'Saving checkpoint %s',
        self.key,
      )

      with self.store.open_writer(
        self.key
      ) as writer :

        for line in lines :

          writer.write(
            ( line + '\n' ).encode(
              'utf-8'
            )
          )


  def load_custom(
    self,
    decoder : Callable[ [ bytes ], T ],
  ) -> T :

    '''
    Load checkpoint using a custom decoder.

    Example:
      json.loads
      pickle.loads
    '''

    with self.tracing.operation(
      'load_custom',
      key = self.key,
    ) :

      with self.store.open_reader(
        self.key
      ) as reader :

        data = reader.read( )

      return decoder( data )


  def save_custom(
    self,
    data : T,
    encoder : Callable[ [ T ], bytes ],
  ) -> None :

    '''
    Save checkpoint using a custom encoder.

    Example:
      json.dumps(...).encode()
      pickle.dumps
    '''

    with self.tracing.operation(
      'save_custom',
      key = self.key,
    ) :

      with self.store.open_writer(
        self.key
      ) as writer :

        writer.write(
          encoder( data )
        )

