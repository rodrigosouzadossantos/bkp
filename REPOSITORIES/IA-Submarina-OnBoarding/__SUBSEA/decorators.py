#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: set tabstop=2 shiftwidth=2 softtabstop=2 expandtab:



import time
import logging

from functools import wraps

def observed( name = None ) :

  def decorator( fn ) :

    label = name or fn.__name__

    @wraps( fn )
    def wrapper( *args, **kwargs ) :

      log = logging.getLogger( 'Subsea' )
      start = time.time()

      log.info( f'start {label}' )

      try :
        return fn( *args, **kwargs )
      finally :
        elapsed = time.time() - start
        log.info( f'end {label} elapsed={elapsed:.2f}s' )

    return wrapper

  return decorator


