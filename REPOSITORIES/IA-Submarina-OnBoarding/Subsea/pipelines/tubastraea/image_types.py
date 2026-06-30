#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: set tabstop=2 shiftwidth=2 softtabstop=2 expandtab:


from typing import TypedDict, Optional, List, Tuple, Protocol

import numpy as np


class ImageMetadata( TypedDict ):

  filename : str
  format : Optional[ str ]
  mode : Optional[ str ]
  width : int
  height : int
  mean : float
  std : float
  min : int
  max : int
  exif : Optional[ str ]


class SimilarPair( TypedDict ):

  image_a : str
  image_b : str
  score : float


class ImageWorkerResult( Protocol ):

  def __call__(
    self,
    path : str,
  ) -> Optional[ Tuple[ np.ndarray, ImageMetadata ] ] :
    ...

