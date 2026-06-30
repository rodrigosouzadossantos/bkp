#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: set tabstop=2 shiftwidth=2 softtabstop=2 expandtab:


import json

import numpy as np

from typing import Dict, Any

from PIL import Image, ExifTags

from .image_types import ImageMetadata


def extract_metadata_from_image(
  img : Image.Image,
  arr : np.ndarray,
  path : str,
) -> ImageMetadata :

  data : Dict[ str, Any ] = {
    'filename': str( path ),
    'format': img.format,
    'mode': img.mode,
    'width': img.size[ 0 ],
    'height': img.size[ 1 ],
    'mean': float( arr.mean( ) ),
    'std': float( arr.std( ) ),
    'min': int( arr.min( ) ),
    'max': int( arr.max( ) ),
  }

  exif_data : Dict[ str, Any ] = { }
  try:
    if hasattr( img, '_getexif' ) and img._getexif( ):
      for t, v in img._getexif( ).items( ):
        exif_data[
          ExifTags.TAGS.get( t, t )
        ] = v
  except Exception:
    pass

  data[ 'exif' ] = (
    json.dumps( exif_data )
    if exif_data
    else None
  )

  return data

