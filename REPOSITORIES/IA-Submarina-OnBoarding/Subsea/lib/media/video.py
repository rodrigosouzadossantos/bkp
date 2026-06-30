#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: set tabstop=2 shiftwidth=2 softtabstop=2 expandtab:





import cv2

from Subsea.observability import SubseaComponent, trace


class VideoSource( SubseaComponent ) :

  def __init__( self, path ) :

    super( ).__init__()

    self.cap = cv2.VideoCapture(
      path
    )

  @trace( )
  def frames( self ) :

    while True :

      ret, frame = self.cap.read( )

      if not ret :

        break

      yield frame


