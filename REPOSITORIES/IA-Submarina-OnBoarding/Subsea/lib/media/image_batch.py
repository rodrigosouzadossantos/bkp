#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: set tabstop=2 shiftwidth=2 softtabstop=2 expandtab:


from __future__ import annotations

from typing import List, Tuple

import torch

from .image import Image


class ImageBatch :

  '''
  Batch of Image objects.

  - Pads to max HxW
  - Stacks to torch.Tensor (N, C, H, W)
  - CUDA-ready
  '''

  def __init__(
    self,
    images : List[ Image ],
    *,
    pad_value : float = 0.0,
  ) -> None :

    if not images:
      raise ValueError( 'ImageBatch cannot be empty' )

    self.images = images
    self.pad_value = pad_value

  # --------------------------------------------------
  # Padding + stacking
  # --------------------------------------------------

  def to_torch(
    self,
  ) -> torch.Tensor :

    tensors = [
      img.torch
      for img in self.images
    ]

    max_h = max(
      t.shape[ 1 ] for t in tensors
    )
    max_w = max(
      t.shape[ 2 ] for t in tensors
    )

    padded = [ ]

    for t in tensors:

      _, h, w = t.shape

      pad_h = max_h - h
      pad_w = max_w - w

      padded.append(
        torch.nn.functional.pad(
          t,
          ( 0, pad_w, 0, pad_h ),
          value = self.pad_value,
        )
      )

    batch = torch.stack(
      padded,
      dim = 0,
    )

    return batch

  # --------------------------------------------------
  # PyTorch Dataset interface
  # --------------------------------------------------

  def __len__( self ):
    return len( self.images )

  def __getitem__( self, idx ):
    return self.images[ idx ].torch

