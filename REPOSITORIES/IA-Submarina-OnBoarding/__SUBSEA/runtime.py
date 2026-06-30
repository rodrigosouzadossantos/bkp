#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: set tabstop=2 shiftwidth=2 softtabstop=2 expandtab:



import os

from concurrent.futures import ProcessPoolExecutor

class ExecutionRuntime :

  def __init__( self, max_workers = None ) :

    self.max_workers = (
      max_workers or max( 1, os.cpu_count( ) - 1 )
    )

  def map_cpu( self, fn, items ) :

    with ProcessPoolExecutor( self.max_workers ) as exe :
      return list( exe.map( fn, items ) )

  def gpu_available( self ) :

    try :
      import cv2
      return cv2.cuda.getCudaEnabledDeviceCount( ) > 0
    except Exception :
      return False


