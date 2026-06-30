#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: set tabstop=2 shiftwidth=2 softtabstop=2 expandtab:


from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple

import numpy as np


@dataclass( frozen = True )
class Polygon :

    '''
    Polygon annotation ( geometric domain entity ).

    DESIGN INVARIANTS :
      - points are ALWAYS normalized ( 0 – 1 )
      - geometry only ( no pixels, no image knowledge )
      - immutable

    Safe for :
      - images
      - video frames
      - augmentation pipelines
      - tracking
    '''

    label : int
    points : np.ndarray   # shape ( N , 2 ) , float , normalized

    # --------------------------------------------------
    # Validation
    # --------------------------------------------------

    def __post_init__( self ) :

        if not isinstance( self.points , np.ndarray ) :
            raise TypeError( 'points must be a numpy.ndarray' )

        if self.points.ndim != 2 or self.points.shape[ 1 ] != 2 :
            raise ValueError( 'points must have shape ( N , 2 )' )

        if self.points.shape[ 0 ] < 3 :
            raise ValueError( 'polygon must have at least 3 points' )

        if not np.issubdtype( self.points.dtype , np.floating ) :
            raise TypeError( 'points must be floating point values' )

        if not ( ( 0.0 <= self.points ).all( ) and ( self.points <= 1.0 ).all( ) ) :
            raise ValueError( 'points must be normalized in range [ 0 , 1 ]' )

    # --------------------------------------------------
    # Basic properties
    # --------------------------------------------------

    @property
    def num_points( self ) -> int :

        return int( self.points.shape[ 0 ] )

    # --------------------------------------------------
    # Geometric properties ( normalized space )
    # --------------------------------------------------

    @property
    def centroid( self ) -> Tuple[ float , float ] :

        '''
        Geometric centroid ( mean of vertices ).
        Normalized coordinates.
        '''

        x = float( self.points[ : , 0 ].mean( ) )
        y = float( self.points[ : , 1 ].mean( ) )

        return x , y

    @property
    def bounding_box( self ) -> Tuple[ float , float , float , float ] :

        '''
        Normalized bounding box : ( xmin , ymin , xmax , ymax ).
        '''

        xs = self.points[ : , 0 ]
        ys = self.points[ : , 1 ]

        return (
            float( xs.min( ) ) ,
            float( ys.min( ) ) ,
            float( xs.max( ) ) ,
            float( ys.max( ) ) ,
        )

    @property
    def area( self ) -> float :

        '''
        Polygon area ( Shoelace formula ).
        Area is in normalized units.
        '''

        x = self.points[ : , 0 ]
        y = self.points[ : , 1 ]

        return float(
            0.5 * abs(
                np.dot( x , np.roll( y , -1 ) )
                - np.dot( y , np.roll( x , -1 ) )
            )
        )

    @property
    def perimeter( self ) -> float :

        '''
        Polygon perimeter ( sum of edge lengths ).
        Normalized units.
        '''

        pts = np.vstack( [ self.points , self.points[ 0 ] ] )
        diffs = np.diff( pts , axis = 0 )

        return float(
            np.linalg.norm( diffs , axis = 1 ).sum( )
        )

    @property
    def is_clockwise( self ) -> bool :

        '''
        Returns True if polygon vertices are ordered clockwise.
        '''

        x = self.points[ : , 0 ]
        y = self.points[ : , 1 ]

        signed_area = (
            np.dot( x , np.roll( y , -1 ) )
            - np.dot( y , np.roll( x , -1 ) )
        )

        return signed_area < 0

    # --------------------------------------------------
    # Functional helper
    # --------------------------------------------------

    def with_points( self , points : np.ndarray ) -> Polygon :

        '''
        Returns a new Polygon with replaced points.
        Preserves immutability.
        '''

        return Polygon(
            label = self.label ,
            points = points ,
        )

