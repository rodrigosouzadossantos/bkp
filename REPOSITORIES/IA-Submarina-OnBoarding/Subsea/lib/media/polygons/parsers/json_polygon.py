#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: set tabstop=2 shiftwidth=2 softtabstop=2 expandtab:


import json
from typing import Iterable , Tuple

from .base import AnnotationParser


class JsonPolygonParser( AnnotationParser ) :

    '''
    Example JSON format:

    [
      {
        "label": 1,
        "points": [ [ x , y ] , [ x , y ] , ... ]
      }
    ]
    '''

    def parse(
        self ,
        raw : str ,
    ) -> Iterable[ Tuple[ int , list[ Tuple[ float , float ] ] ] ] :

        data = json.loads( raw )

        for item in data :

            label = int( item[ 'label' ] )
            points = [
                ( float( x ) , float( y ) )
                for x , y in item[ 'points' ]
            ]

            if len( points ) >= 3 :
                yield label , points

