#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: set tabstop=2 shiftwidth=2 softtabstop=2 expandtab:


from typing import Iterable , Tuple

from .base import AnnotationParser


class TxtPolygonParser( AnnotationParser ) :

    '''
    Generic TXT polygon parser.

    Supported formats per line:

    1) Space-separated ( YOLO-style ):
        <label> x1 y1 x2 y2 ... xn yn

    2) Pair-separated:
        <label> x1,y1; x2,y2; ...; xn,yn
    '''

    def parse(
        self ,
        raw : str ,
    ) -> Iterable[ Tuple[ int , list[ Tuple[ float , float ] ] ] ] :

        for lineno , line in enumerate( raw.splitlines( ) , start = 1 ) :

            line = line.strip( )

            if not line :
                continue

            parts = line.split( )

            if len( parts ) < 7 :
                # Need at least label + 3 points
                continue

            label = int( parts[ 0 ] )
            data  = parts[ 1 : ]

            points = [ ]

            # ------------------------------------------
            # Case 1 : x,y ; x,y
            # ------------------------------------------

            if ',' in line or ';' in line :

                joined = ' '.join( data )

                for pair in joined.split( ';' ) :

                    pair = pair.strip( )

                    if not pair :
                        continue

                    x_str , y_str = pair.split( ',' )

                    points.append(
                        ( float( x_str ) , float( y_str ) )
                    )

            # ------------------------------------------
            # Case 2 : space-separated x y x y (YOLO-style)
            # ------------------------------------------

            else :

                if len( data ) % 2 != 0 :
                    raise ValueError(
                        f'Line { lineno } has odd number of coordinates'
                    )

                it = iter( data )

                for x_str , y_str in zip( it , it ) :

                    points.append(
                        ( float( x_str ) , float( y_str ) )
                    )

            if len( points ) >= 3 :
                yield label , points

