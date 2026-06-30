#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: set tabstop=2 shiftwidth=2 softtabstop=2 expandtab:


from __future__ import annotations

from typing import List , Dict , Tuple

from ..image import Image

from .polygon import Polygon
from .overlay import PolygonOverlay


class AnnotatedImage :

    '''
    Application-level object that binds an Image
    with its Polygon annotations.

    This is the ONLY place where Image and Polygon meet.
    '''

    def __init__(
        self ,
        image : Image ,
        polygons : List[ Polygon ] ,
    ) -> None :

        self.image = image
        self.polygons = polygons

    # --------------------------------------------------
    # Overlay
    # --------------------------------------------------

    def overlay(
        self ,
        * ,
        colors : Dict[ int , Tuple[ int , int , int ] ] | None = None ,
        alpha  : float = 0.5 ,
    ) -> Image :

        overlay = PolygonOverlay( )

        return overlay.apply(
            self.image ,
            self.polygons ,
            colors = colors ,
            alpha  = alpha ,
        )

    # --------------------------------------------------
    # Access helpers
    # --------------------------------------------------

    @property
    def num_polygons( self ) -> int :

        return len( self.polygons )

    def with_polygons(
        self ,
        polygons : List[ Polygon ] ,
    ) -> AnnotatedImage :

        '''
        Returns a new AnnotatedImage with replaced polygons.
        Image is preserved.
        '''

        return AnnotatedImage(
            image    = self.image ,
            polygons = polygons ,
        )

