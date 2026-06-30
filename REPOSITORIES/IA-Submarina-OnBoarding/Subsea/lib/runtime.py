#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: set tabstop=2 shiftwidth=2 softtabstop=2 expandtab:


import os

from concurrent.futures import ProcessPoolExecutor

from Subsea.observability import SubseaComponent, trace


class Runtime( SubseaComponent ) :

  def __init__( self, workers = None ) :

    super( ).__init__()

    self.workers = (
      workers or max(
        1,
        os.cpu_count( ) - 1
      )
    )

  @trace( )
  def map( self, fn, items ) :

    self.step(
      "Executing with %d workers" %
      self.workers
    )

    with ProcessPoolExecutor(
      self.workers
    ) as exe :

      return list(
        exe.map( fn, items )
      )


