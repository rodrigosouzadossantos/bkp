#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: set tabstop=2 shiftwidth=2 softtabstop=2 expandtab:


from __future__ import annotations

from pathlib import Path
from typing import Optional, Tuple

import numpy as np


class Image :

  '''
  Canonical Image object.

  - Single instance across the pipeline
  - Canonical representation: NumPy RGB (HWC, uint8)
  - Lazy adapters: PIL / OpenCV / PyTorch / TensorFlow
  - Supports inference, similarity, overlays, Grad-CAM
  '''

  # ==================================================
  # Construction
  # ==================================================

  def __init__(
    self,
    *,
    array : np.ndarray,
    path : str | Path | None = None,
  ) -> None :

    if not isinstance( array, np.ndarray ):
      raise TypeError(
        'array must be a numpy.ndarray'
      )

    if array.ndim != 3 or array.shape[ 2 ] not in ( 1, 3, 4 ):
      raise ValueError(
        'array must be HWC with 1, 3 or 4 channels'
      )

    # Normalize to RGB uint8
    if array.dtype != np.uint8:
      array = np.clip( array, 0, 255 ).astype( np.uint8 )

    if array.shape[ 2 ] == 4:  # RGBA → RGB
      array = array[ :, :, :3 ]

    self._np : np.ndarray = array
    self._path : Optional[ Path ] = (
      Path( path ).expanduser( ).resolve( )
      if path is not None
      else None
    )

    # Lazy adapters
    self._pil = None
    self._cv = None
    self._torch = None
    self._tf = None

  # ==================================================
  # Core data
  # ==================================================

  @property
  def numpy( self ) -> np.ndarray :
    '''
    Canonical RGB NumPy array (HWC, uint8).
    '''
    return self._np

  @property
  def shape( self ):
    return self._np.shape

  @property
  def size( self ) -> Tuple[ int, int ] :
    h, w = self._np.shape[ :2 ]
    return ( w, h )

  @property
  def path( self ) -> Optional[ Path ] :
    return self._path

  # ==================================================
  # PIL adapter
  # ==================================================

  @property
  def pil( self ):

    if self._pil is None:
      from PIL import Image as PILImage
      self._pil = PILImage.fromarray(
        self._np,
        mode = 'RGB',
      )

    return self._pil

  # ==================================================
  # OpenCV adapter (BGR)
  # ==================================================

  @property
  def cv( self ):

    if self._cv is None:
      import cv2
      self._cv = cv2.cvtColor(
        self._np,
        cv2.COLOR_RGB2BGR,
      )

    return self._cv

  # ==================================================
  # PyTorch adapter (CHW, float32, CUDA if available)
  # ==================================================

  @property
  def torch( self ):

    if self._torch is None:
      import torch

      arr = self._np.transpose( 2, 0, 1 )
      t = torch.from_numpy(
        arr
      ).float( ) / 255.0

      if torch.cuda.is_available( ) :
        t = t.cuda( non_blocking = True )

      self._torch = t

    return self._torch

  # ==================================================
  # TensorFlow / Keras adapter (HWC, float32, GPU)
  # ==================================================

  @property
  def tf( self ):

    if self._tf is None:
      import tensorflow as tf

      t = tf.convert_to_tensor(
        self._np,
        dtype = tf.float32,
      ) / 255.0

      if tf.config.list_physical_devices( 'GPU' ):
        with tf.device( '/GPU:0' ):
          t = tf.identity( t )

      self._tf = t

    return self._tf

  # ==================================================
  # Display
  # ==================================================

  def show( self ) -> None :
    '''
    Display image using PIL backend.
    '''
    self.pil.show( )

  # ==================================================
  # Functional helpers
  # ==================================================

  def copy( self ) -> Image :
    '''
    Functional copy (new Image instance).
    '''
    return Image(
      array = self._np.copy( ),
      path = self._path,
    )

  # ==================================================
  # Inference helpers
  # ==================================================

  def infer_torch(
    self,
    model,
  ):

    import torch

    model.eval( )

    x = self.torch.unsqueeze( 0 )

    with torch.no_grad( ) :
      return model( x )

  def infer_tf(
    self,
    model,
  ):

    x = self.tf[ None, ... ]
    return model( x )

  # ==================================================
  # Embeddings / similarity
  # ==================================================

  def embedding_torch(
    self,
    model,
  ) -> np.ndarray :

    out = self.infer_torch( model )
    return out.squeeze( ).detach( ).cpu( ).numpy( )

  @staticmethod
  def cosine_similarity(
    emb1 : np.ndarray,
    emb2 : np.ndarray,
  ) -> float :

    from numpy.linalg import norm

    return float(
      np.dot( emb1, emb2 )
      / ( norm( emb1 ) * norm( emb2 ) )
    )

  # ==================================================
  # Overlays
  # ==================================================

  def overlay_mask(
    self,
    mask : np.ndarray,
    *,
    color = ( 255, 0, 0 ),
    alpha : float = 0.5,
  ) -> Image :

    import cv2

    if mask.shape != self._np.shape[ :2 ]:
      raise ValueError(
        'Mask must have same HxW as image'
      )

    base = self.cv.copy( )
    overlay = base.copy( )

    overlay[ mask > 0 ] = color

    blended = cv2.addWeighted(
      overlay,
      alpha,
      base,
      1 - alpha,
      0,
    )

    return Image(
      array = blended[ :, :, ::-1 ],
      path = self._path,
    )

  # ==================================================
  # Grad-CAM (PyTorch)
  # ==================================================

  def grad_cam(
    self,
    model,
    target_layer,
  ) -> np.ndarray :

    import torch

    activations = None
    gradients = None

    def fwd_hook( m, i, o ):
      nonlocal activations
      activations = o

    def bwd_hook( m, gi, go ):
      nonlocal gradients
      gradients = go[ 0 ]

    h1 = target_layer.register_forward_hook(
      fwd_hook
    )
    h2 = target_layer.register_backward_hook(
      bwd_hook
    )

    x = self.torch.unsqueeze( 0 )
    x.requires_grad_( True )

    out = model( x )
    out.max( ).backward( )

    h1.remove( )
    h2.remove( )

    weights = gradients.mean(
      dim = ( 2, 3 )
    )

    cam = (
      weights[ :, :, None, None ]
      * activations
    ).sum( 1 )

    cam = torch.relu( cam )
    cam = cam.squeeze( ).detach( ).cpu( ).numpy( )

    cam = cam / ( cam.max( ) + 1e-8 )

    return cam

  # ==================================================
  # Representation
  # ==================================================

  def __repr__( self ) -> str :

    src = (
      str( self._path )
      if self._path
      else 'array'
    )

    return (
      f'Image('
      f'source={src!r}, '
      f'shape={self.shape}'
      f')'
    )

  def _repr_png_( self ):
    '''
    Jupyter inline display.
    '''
    return self.pil._repr_png_()
