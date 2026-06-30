#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: set tabstop=2 shiftwidth=2 softtabstop=2 expandtab:


import logging

from typing import Iterator, Iterable, List, Dict, Optional

from Subsea.config import CONFIG
from Subsea.storage import STORAGE


class tubastraea :

  '''
  Iterable facade over an object bucket.

  Behaves like:

    - an iterable of image paths
    - a lightweight bucket abstraction
    - a model-aware inference interface (pluggable)

  This class does NOT depend on ImagePipeline.
  '''

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
    bucket_name : str,
    prefix : str = '',
    logger : Optional[ logging.Logger ] = None,
  ) -> None :

    self.bucket = bucket_name
    self.prefix = prefix

    self.log = logger or logging.getLogger(
      'tubastraea'
    )

    self._objects : Optional[ List[ str ] ] = None

    # simple model registry (symbolic)
    self._models : Dict[ str, Dict[ str, str ] ] = {
      'resnet50': {
        'framework': 'torch',
        'weights': 'IMAGENET1K_V2',
      },
    }

  # --------------------------------------------------
  # Bucket / iterable behavior
  # --------------------------------------------------

  def _load_objects( self ) -> None :

    if self._objects is not None:
      return

    self.log.info(
      f'Listing objects | bucket = { self.bucket } | prefix = { self.prefix }'
    )

    store = STORAGE.store(
      bucket = self.bucket
    )

    keys = store.list(
      contains = self.prefix
    )

    self._objects = [
      f's3://{ self.bucket }/{ k }'
      for k in keys
      if k.lower( ).endswith(
        self.IMAGE_EXTENSIONS
      )
    ]

  def __iter__( self ) -> Iterator[ str ] :

    self._load_objects( )
    return iter( self._objects )

  def __len__( self ) -> int :

    self._load_objects( )
    return len( self._objects )

  def images( self ) -> Iterable[ str ] :

    '''
    Explicit iterator over image paths.
    '''

    return self.__iter__( )

  # --------------------------------------------------
  # Model registry
  # --------------------------------------------------

  def models( self ) -> Iterable[ str ] :

    '''
    Available model identifiers.
    '''

    return self._models.keys( )

  def model_info( self ) -> Dict[ str, Dict[ str, str ] ] :

    '''
    Metadata about available models.

    Returns
    -------
    dict
      model_name → metadata
    '''

    return dict( self._models )

  # --------------------------------------------------
  # Inference hooks (pluggable)
  # --------------------------------------------------

  def infer(
    self,
    model : str,
    images : Optional[ Iterable[ str ] ] = None,
  ):

    '''
    Placeholder inference hook.

    This method intentionally does NOT implement inference.
    It provides a stable API for plugging external inference
    engines or pipelines.

    Parameters
    ----------
    model : str
      Model identifier.

    images : iterable of str, optional
      Image paths to process. Defaults to all images.

    Yields
    ------
    ( image_path, result )
    '''

    if model not in self._models:
      raise ValueError(
        f'Unknown model: { model }'
      )

    if images is None:
      images = self.images( )

    self.log.info(
      f'Infer called | model = { model } | images = { "all" if images is self._objects else "subset" }'
    )

    for path in images:

      # No actual inference here — this is a hook
      yield {
        'image': path,
        'model': model,
        'result': None,
      }

  def infer_all_models(
    self,
    images : Optional[ Iterable[ str ] ] = None,
  ):

    '''
    Iterate over all models and yield inference hooks.

    Yields
    ------
    ( model_name, iterator )
    '''

    for model in self.models( ):
      yield model, self.infer(
        model = model,
        images = images,
      )

