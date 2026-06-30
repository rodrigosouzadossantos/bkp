#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: set tabstop=2 shiftwidth=2 softtabstop=2 expandtab:


from __future__ import annotations

from typing import List, Tuple

import numpy as np

from .image import Image


class ImageOverlayStack :

  '''
  Stack of overlays (masks / heatmaps).

  Applies multiple overlays sequentially.
  '''

  def __init__(
    self,
    base : Image,
  ) -> None :

    self.base = base
    self._overlays : List[ Tuple[ np.ndarray, Tuple[int,int,int], float ] ] = [ ]

  def add(
    self,
    mask : np.ndarray,
    *,
    color : Tuple[ int, int, int ] = ( 255, 0, 0 ),
    alpha : float = 0.5,
  ) -> ImageOverlayStack :

    if mask.shape != self.base.numpy.shape[ :2 ]:
      raise ValueError(
        'Mask shape must match image'
      )

    self._overlays.append(
      ( mask, color, alpha )
    )

    return self

  def render( self ) -> Image :

    img = self.base

    for mask, color, alpha in self._overlays:
      img = img.overlay_mask(
        mask,
        color = color,
        alpha = alpha,
      )

    return img

