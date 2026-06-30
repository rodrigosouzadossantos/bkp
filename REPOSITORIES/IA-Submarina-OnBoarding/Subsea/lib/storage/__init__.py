#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: set tabstop=2 shiftwidth=2 softtabstop=2 expandtab:

import sys
import importlib
from pathlib import Path
from typing import Set

from Subsea import CONFIG
#from Subsea.storage._base import Storage

class StorageError( RuntimeError ) :
  pass

def _available_storages( ) -> Set[ str ] :
  '''
  Discover storage plugins implemented as packages.
  '''
  base = Path( __file__ ).resolve( ).parent
  return {
    p.name
      for p in base.iterdir( )
        if p.is_dir( )
          and not p.name.startswith( '_' )
          and ( p / '__init__.py' ).exists( )
    }


def _load_storage( ) :#-> Storage :

  storage_type = CONFIG.storage.type
  valid_storages = _available_storages( )

  if storage_type not in valid_storages :
    raise StorageError(
        f'Invalid storage.type "{storage_type}". '
        f'Available: {sorted(valid_storages)}'
    )

  #package_name = Path( __file__ ).resolve( ).parents[ 1 ].name
  #module_path = f'{package_name}.storage.{storage_type}'

  module_path = f'{__name__}.{storage_type}'
  storage = importlib.import_module(
    module_path,
  )

  #if not isinstance( storage, Storage ):
  #  raise StorageError(
  #      f'Storage '{storage_type}' does not implement required interface'
  #  )

  try :
    return storage
  finally :
    sys.modules.pop( module_path, None )


# ---- Public, singleton-like storage instance ----
STORAGE = _load_storage( )

from .object_store import ObjectStore
from .local_store import LocalObjectStore
from .checkpoint_store import CheckpointStore
from .object_lister import ObjectLister

__all__ = [
  'STORAGE',
  'ObjectStore',
  'LocalObjectStore',
  'CheckpointStore',
  'ObjectLister',
]


__path__ = [ ]

def __getattr__( name ):

  raise AttributeError(
    "Direct access to storage internals is forbidden. "
    "Use `from Subsea.storage import STORAGE` only."
  )

def __dir__( ):
  return __all__


