#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: set tabstop=2 shiftwidth=2 softtabstop=2 expandtab:


import logging

from typing import Iterator, Iterable, List, Dict, Optional

from Subsea import CONFIG
from Subsea import STORAGE
from Subsea import CONSOLE

from .corals_view import CoralsView

from Subsea.observability.tracing import TracingPolicy


class Corals :

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
    bucket : str,
    prefix : str = '',
    logger : Optional[ logging.Logger ] = None,
  ) -> None :

    self.bucket = bucket
    self.prefix = prefix

    self.log = logger or logging.getLogger(
      self.__class__.__name__
    )

    self.tracing = TracingPolicy(
      name = __class__.__name__,
      logger = self.log,
    )

    self._images : Optional[ dict ] = None
    self._objects : Optional[ List[ str ] ] = None

    # simple model registry (symbolic)
    #self._models : Dict[ str, Dict[ str, str ] ] = {
    #  'resnet50': {
    #    'framework': 'torch',
    #    'weights': 'IMAGENET1K_V2',
    #  },
    #}
    self._models : Optional[ List[ str ] ] = None

    self._load_objects( )

  # --------------------------------------------------
  # Bucket / iterable behavior
  # --------------------------------------------------

  def _load_objects( self ) -> None :

    if self._objects is not None:
      return

    with self.tracing.operation(
      'Loading Objects',
      prefix = self.prefix,
    ) :

        self.log.info(
          f'Listing objects | bucket = { self.bucket } | prefix = { self.prefix }'
        )
    
        store = STORAGE.store(
          bucket = self.bucket
        )
    
        lister = STORAGE.parallel_lister(
          store = store,
          max_workers = 32,
        )
    
        keys = lister.list_objects(
          prefix = self.prefix,
        )
    
        self._objects = self.s3_structure( [
          f's3://{ self.bucket }/{ k }'
          for k in keys
        ] )
    
        self._images = self.filter_tree(
          self._objects,
          self.IMAGE_EXTENSIONS,
          invert = True,
        )
    
        self._models = self.filter_tree(
          self._objects,
          ( '.pt', 'keras' ),
        )

  #def __iter__( self ) -> Iterator[ str ] :

  #  self._load_objects( )
  #  return iter( self._objects )

  #def __len__( self ) -> int :

  #  self._load_objects( )
  #  return len( self._objects )

  def s3_structure(
    self,
    uris : list[ str ],
  ) -> dict :

    tree : dict = { }

    for uri in uris:

      if not uri.startswith( 's3://' ):
        continue

      # remove scheme
      path = uri[ 5: ]

      # split parts
      parts = path.split( '/' )

      # prepend scheme as root
      parts = [ 's3' ] + parts

      node = tree

      for i, part in enumerate( parts ):

        is_last = i == len( parts ) - 1

        if is_last:
          # file
          node.setdefault( part, None )
        else:
          node = node.setdefault( part, { } )

    return tree

  @staticmethod
  def filter_tree(
    node : dict,
    extensions : tuple[ str, ... ] = None,
    *,
    invert : bool = False,
  ) -> dict :

    result = { }

    for key, value in node.items():

      # -------------------------------
      # File
      # -------------------------------

      if value is None:

        matches = key.lower().endswith( extensions ) if extensions else True 

        if matches ^ invert :
          result[ key ] = None


      # -------------------------------
      # Directory
      # -------------------------------

      elif isinstance( value, dict ):

        filtered = Corals.filter_tree(
          value,
          extensions,
          invert = invert,
        )

        if filtered:
          result[ key ] = filtered

    return result



  @property
  def images( self ) : #-> dict :

    '''
    Explicit iterator over image paths.
    '''

    self._load_objects( )
    return CoralsView( self._images )

  @property
  def objects( self ) : #-> Iterable[ str ] :

    '''
    Available model identifiers.
    '''

    self._load_objects( )
    return CoralsView( self._objects )

  # --------------------------------------------------
  # Model registry
  # --------------------------------------------------

  @property
  def models( self ) : #-> Iterable[ str ] :

    '''
    Available model identifiers.
    '''

    self._load_objects( )
    return CoralsView( self._models )

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

