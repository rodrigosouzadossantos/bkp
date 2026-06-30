#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: set tabstop=2 shiftwidth=2 softtabstop=2 expandtab:

import numpy as np

from typing import List, Tuple

from sklearn.metrics.pairwise import cosine_similarity


def find_similar_images(
  embeddings : np.ndarray,
  paths : List[ str ],
  threshold : float = 0.90,
) -> List[ Tuple[ str, str, float ] ] :

  sim = cosine_similarity( embeddings )
  n = len( paths )
  pairs = [ ]

  for i in range( n ):
    for j in range( i + 1, n ):
      if sim[ i, j ] >= threshold:
        pairs.append(
          (
            str( paths[ i ] ),
            str( paths[ j ] ),
            float( sim[ i, j ] ),
          )
        )

  return pairs


def find_duplicates(
  similar_pairs : List[ Tuple[ str, str, float ] ],
  strong_threshold : float = 0.98,
) -> List[ Tuple[ str, str, float ] ] :

  return [
    p for p in similar_pairs
    if p[ 2 ] >= strong_threshold
  ]

