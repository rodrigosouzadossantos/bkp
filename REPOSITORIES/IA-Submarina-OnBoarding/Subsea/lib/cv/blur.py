#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: set tabstop=2 shiftwidth=2 softtabstop=2 expandtab:





import cv2

from Subsea.observability import SubseaComponent, trace


class BlurDetector( SubseaComponent ) :

  @trace( )
  def score( self, gray ) :

    self.step(
      "Computing blur score"
    )

    if cv2.cuda.getCudaEnabledDeviceCount( ) > 0 :

      g = cv2.cuda_GpuMat( )
      g.upload(
        gray
      )

      lap = cv2.cuda.Laplacian(
        g,
        cv2.CV_32F
      )

      return cv2.cuda.sum(
        lap
      )[ 0 ]

    return cv2.Laplacian(
      gray,
      cv2.CV_32F
    ).var( )


