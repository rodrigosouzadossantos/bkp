#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: set tabstop=2 shiftwidth=2 softtabstop=2 expandtab:


import numpy as np
import cv2

from typing import List , Tuple

from .polygon import Polygon


class PolygonRasterizer :

    '''
    Rasterizes normalized Polygon into pixel space.

    Responsibilities :
      - convert normalized coordinates to pixels
      - clip safely to image bounds
      - generate binary mask ( H , W )

    Does NOT :
      - draw on image
      - know Image class
      - apply augmentations
    '''

    @staticmethod
    def to_mask(
        polygon : Polygon ,
        * ,
        image_height : int ,
        image_width  : int ,
    ) -> np.ndarray :

        if image_height <= 0 or image_width <= 0 :
            raise ValueError( 'image dimensions must be positive' )

        # Convert normalized points to pixel coordinates
        pts = polygon.points.copy( )

        pts[ : , 0 ] *= image_width
        pts[ : , 1 ] *= image_height

        pts = np.round( pts ).astype( np.int32 )

        # Clip points to image bounds
        pts[ : , 0 ] = np.clip( pts[ : , 0 ] , 0 , image_width  - 1 )
        pts[ : , 1 ] = np.clip( pts[ : , 1 ] , 0 , image_height - 1 )

        # Create empty mask
        mask = np.zeros(
            ( image_height , image_width ) ,
            dtype = np.uint8 ,
        )

        # Rasterize polygon
        cv2.fillPoly(
            mask ,
            [ pts.reshape( ( -1 , 1 , 2 ) ) ] ,
            1 ,
        )

        return mask

    @staticmethod
    def to_masks(
        polygons : List[ Polygon ] ,
        * ,
        image_height : int ,
        image_width  : int ,
    ) -> List[ np.ndarray ] :

        return [
            PolygonRasterizer.to_mask(
                polygon ,
                image_height = image_height ,
                image_width  = image_width ,
            )
            for polygon in polygons
        ]

    @staticmethod
    def to_contour_mask(
        polygon : Polygon ,
        * ,
        image_height : int ,
        image_width  : int ,
        thickness    : int = 2 ,
    ) -> np.ndarray :

        import cv2
        import numpy as np

        if image_height <= 0 or image_width <= 0 :
            raise ValueError( 'image dimensions must be positive' )

        pts = polygon.points.copy( )

        pts[ : , 0 ] *= image_width
        pts[ : , 1 ] *= image_height

        pts = pts.astype( np.int32 )

        mask = np.zeros(
            ( image_height , image_width ) ,
            dtype = np.uint8 ,
        )

        cv2.polylines(
            mask ,
            [ pts ] ,
            isClosed = True ,
            color = 1 ,
            thickness = thickness ,
        )

        return mask


    @staticmethod
    def bounding_box_px(
        polygon : Polygon ,
        * ,
        image_height : int ,
        image_width  : int ,
    ) -> Tuple[ int , int , int , int ] :

        '''
        Returns bounding box in pixel space :
        ( xmin , ymin , xmax , ymax )
        '''

        pts = polygon.points.copy( )

        pts[ : , 0 ] *= image_width
        pts[ : , 1 ] *= image_height

        pts = np.round( pts ).astype( np.int32 )

        xmin = int( np.clip( pts[ : , 0 ].min( ) , 0 , image_width  - 1 ) )
        ymin = int( np.clip( pts[ : , 1 ].min( ) , 0 , image_height - 1 ) )
        xmax = int( np.clip( pts[ : , 0 ].max( ) , 0 , image_width  - 1 ) )
        ymax = int( np.clip( pts[ : , 1 ].max( ) , 0 , image_height - 1 ) )

        return xmin , ymin , xmax , ymax

