#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: set tabstop=2 shiftwidth=2 softtabstop=2 expandtab:


from typing import List
from io import BytesIO

import numpy as np

from .raw_polygon import RawPolygon
from .parsers.base import AnnotationParser


class PolygonLoader :

    '''
    Loads polygon annotations using a parser and a storage backend.

    Responsibilities:
      - read raw bytes from storage
      - decode text
      - parse annotations
      - detect normalization

    Does NOT:
      - normalize without image size
      - access filesystem directly
    '''

    def __init__(
        self ,
        parser : AnnotationParser ,
        storage ,
        * ,
        encoding : str = 'utf-8' ,
    ) :

        self._parser = parser
        self._storage = storage
        self._encoding = encoding

    def load(
        self ,
        path : str ,
    ) -> List[ RawPolygon ] :

        # ------------------------------------------
        # Read from storage
        # ------------------------------------------

        buf : BytesIO = BytesIO( )

        self._storage.client( 'analise-dados' ).client.download_fileobj(
            'analise-dados' ,
            path ,
            buf ,
        )

        raw_text = buf.getvalue( ).decode( self._encoding )

        # ------------------------------------------
        # Parse polygons
        # ------------------------------------------

        polygons : List[ RawPolygon ] = [ ]

        for label , pts in self._parser.parse( raw_text ) :

            points = np.array(
                pts ,
                dtype = np.float32 ,
            )

            normalized = bool(
                ( points >= 0.0 ).all( )
                and ( points <= 1.0 ).all( )
            )

            polygons.append(
                RawPolygon(
                    label      = label ,
                    points     = points ,
                    normalized = normalized ,
                )
            )

        return polygons

