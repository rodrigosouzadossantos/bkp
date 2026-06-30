#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: set tabstop=2 shiftwidth=2 softtabstop=2 expandtab:


from typing import List, Dict, Tuple

from .polygon import Polygon
from .rasterizer import PolygonRasterizer

from ..image import Image
from ..image_overlay import ImageOverlayStack


class PolygonOverlay :

    '''
    Applies polygon annotations as overlays using
    the existing Image overlay infrastructure.

    Does NOT draw directly.
    Does NOT bypass ImageOverlayStack.
    '''

    def apply(
        self,
        image : Image,
        polygons : List[ Polygon ],
        *,
        colors : Dict[ int, Tuple[ int, int, int ] ] | None = None,
        alpha  : float = 0.5,
    ) -> Image :

        colors = colors or { }

        stack = ImageOverlayStack( image )

        height, width = image.numpy.shape[ : 2 ]

        for polygon in polygons :

            #mask = PolygonRasterizer.to_mask(
            #    polygon,
            #    image_height = height,
            #    image_width  = width,
            #)
            mask = PolygonRasterizer.to_contour_mask(
                polygon,
                image_height = height,
                image_width  = width,
                thickness    = 5,
            )

            color = colors.get(
                polygon.label,
                ( 0, 0, 255 ),
            )

            stack.add(
                mask,
                color = color,
                alpha = alpha,
            )

        return stack.render( )

