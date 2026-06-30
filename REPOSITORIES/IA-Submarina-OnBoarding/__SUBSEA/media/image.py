#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: set tabstop=2 shiftwidth=2 softtabstop=2 expandtab:



import cv2
from pathlib import Path

class ImageSource :

  def __init__( self, paths ) :

    self.paths = [ Path( p ) for p in paths ]

  def __iter__( self ) :

    for p in self.paths :
      yield p, cv2.imread( str( p ) )


