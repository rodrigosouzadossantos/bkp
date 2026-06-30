#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: set tabstop=2 shiftwidth=2 softtabstop=2 expandtab:





import cv2
import polars as pl

from Subsea.observability import SubseaComponent, trace
from Subsea.media.image import ImageSource
from Subsea.cv.blur import BlurDetector


class ImagePipeline( SubseaComponent ) :

  def __init__( self ) :

    super( ).__init__( )

    self.blur = BlurDetector( )

  @trace( )
  def run( self, paths ) :

    rows = [ ]

    for path, img in ImageSource(
      paths
    ) :

      if img is None :

        self.log.warning(
          "Unreadable image %s" %
          path
        )

        continue

      gray = cv2.cvtColor(
        img,
        cv2.COLOR_BGR2GRAY
      )

      score = self.blur.score(
        gray
      )

      rows.append( {
        "path": str( path ),
        "blur_score": score
      } )

    return pl.DataFrame(
      rows
    )


