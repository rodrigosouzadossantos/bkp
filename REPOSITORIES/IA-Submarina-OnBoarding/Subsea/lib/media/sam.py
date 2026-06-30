#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: set tabstop=2 shiftwidth=2 softtabstop=2 expandtab:


from typing import List

import numpy as np

from .image import Image


class SAMSegmenter :

  '''
  Thin wrapper for Segment Anything Model.

  Expects a pre-loaded SAM predictor.
  '''

  def __init__(
    self,
    predictor,
  ) -> None :

    self._predictor = predictor

  def segment(
    self,
    image : Image,
    *,
    points = None,
    labels = None,
  ) -> List[ np.ndarray ] :

    self._predictor.set_image(
      image.numpy
    )

    masks, scores, _ = self._predictor.predict(
      point_coords = points,
      point_labels = labels,
      multimask_output = True,
    )

    return masks
