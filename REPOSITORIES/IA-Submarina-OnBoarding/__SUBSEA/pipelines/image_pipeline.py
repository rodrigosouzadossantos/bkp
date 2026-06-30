#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: set tabstop=2 shiftwidth=2 softtabstop=2 expandtab:



import cv2
import polars as pl

from Subsea.observability import SubseaComponent, trace
from ..media.image import ImageSource
from ..cv.blur import BlurDetector



class ImagePipeline( SubseaComponent ) :

  def __init__( self ) :

    super( ).__init__( )
    self.blur = BlurDetector( )

  @trace( )
  def run( self, paths ) :

    self.step( f'Processing {len(paths)} images' )

    rows = [ ]

    for path, img in ImageSource( paths ) :

      self.step( f'Reading image {path}' )

      if img is None :
        self.log.warning( f'Unreadable image: {path}' )
        continue

      gray = cv2.cvtColor( img, cv2.COLOR_BGR2GRAY )
      score = self.blur.score( gray )

      rows.append( {
        'path': str( path ),
        'blur_score': score
      } )

    self.step( 'Image pipeline completed' )

    return pl.DataFrame( rows )
