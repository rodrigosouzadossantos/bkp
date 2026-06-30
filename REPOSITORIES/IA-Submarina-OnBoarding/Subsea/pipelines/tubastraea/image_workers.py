#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: set tabstop=2 shiftwidth=2 softtabstop=2 expandtab:


import os
import io

import numpy as np

from typing import Optional, Tuple

from PIL import Image, UnidentifiedImageError

from Subsea.storage import STORAGE

from .image_types import ImageMetadata
from .image_io import log_bad_image
from .image_metadata import extract_metadata_from_image


def process_one_image(
  path : str,
) -> Optional[ Tuple[ np.ndarray, ImageMetadata ] ] :

  os.environ[ 'CUDA_VISIBLE_DEVICES' ] = ''

  try:
    buf = io.BytesIO( )

    STORAGE.client( 'analise-dados' ).client.download_fileobj(
      'analise-dados',
      path[ len( 's3://analise-dados/' ) : ],
      buf,
    )

    buf.seek( 0 )
    img = Image.open( buf ).convert( 'RGB' )
    arr = np.array( img, dtype = np.uint8 )

    meta = extract_metadata_from_image(
      img,
      arr,
      path,
    )

    return arr, meta

  except (
    Image.DecompressionBombError,
    UnidentifiedImageError,
    OSError,
    ValueError,
  ) as e:

    log_bad_image( path, str( e ) )
    return None

