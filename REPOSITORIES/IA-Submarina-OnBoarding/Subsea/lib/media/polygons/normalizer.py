#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: set tabstop=2 shiftwidth=2 softtabstop=2 expandtab:


from typing import List

import numpy as np

from .raw_polygon import RawPolygon
from .polygon import Polygon


class PolygonNormalizer :

    '''
    Converts RawPolygon into canonical Polygon.

    Responsibilities :
      - normalize pixel coordinates to [ 0 , 1 ]
      - validate normalized data

    Requires :
      - image_height
      - image_width
    '''

    @staticmethod
    def normalize(
        raw : RawPolygon ,
        * ,
        image_height : int ,
        image_width  : int ,
    ) -> Polygon :

        if image_height <= 0 or image_width <= 0 :
            raise ValueError( 'image dimensions must be positive' )

        points = raw.points.copy( )

        if not raw.normalized :

            points[ : , 0 ] /= image_width
            points[ : , 1 ] /= image_height

        # Final safety clip
        points = np.clip( points , 0.0 , 1.0 )

        return Polygon(
            label  = raw.label ,
            points = points ,
        )

    @staticmethod
    def normalize_many(
        raws : List[ RawPolygon ] ,
        * ,
        image_height : int ,
        image_width  : int ,
    ) -> List[ Polygon ] :

        return [
            PolygonNormalizer.normalize(
                raw ,
                image_height = image_height ,
                image_width  = image_width ,
            )
            for raw in raws
        ]

