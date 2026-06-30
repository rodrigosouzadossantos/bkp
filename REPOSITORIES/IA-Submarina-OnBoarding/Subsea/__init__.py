#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: set tabstop=2 shiftwidth=2 softtabstop=2 expandtab:


import sys

from .lib.display import observability
sys.modules[ __name__ + '.observability' ] = observability

from . import pipelines
sys.modules[ __name__ + '.pipelines' ] = pipelines

from .lib.config import CONFIG
sys.modules[ __name__ + '.CONFIG' ] = CONFIG

from .lib.display import console as CONSOLE

from .lib import storage
sys.modules[ __name__ + '.storage' ] = storage

from .lib.storage import STORAGE
sys.modules[ __name__ + '.STORAGE' ] = STORAGE



class Error( Exception ) :
  '''Subsea Exception'''


from .core.pipeline import Pipeline, get_active_pipeline
def run( ) :
  pipeline = Pipeline._active_instance
  if pipeline is None:
    pipeline_cls = get_active_pipeline( )
    pipeline = pipeline_cls( )

  if not getattr(pipeline, "_base_initialized", False):
    raise RuntimeError(
      f'{pipeline.__class__.__name__}.__init__() '
       'must call super().__init__()'
    )

  try :
    pipeline.run( )
  except Exception as e :
    raise SubseaError( '' ) from None


__all__ = [
  'Error',

  'observability',
  'pipelines',
  'storage',

  'CONFIG',
  'CONSOLE',
  'STORAGE',

  'run',
  'Pipeline',
]
