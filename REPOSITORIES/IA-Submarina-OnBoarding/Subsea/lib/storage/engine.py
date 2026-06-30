#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: set tabstop=2 shiftwidth=2 softtabstop=2 expandtab:

from pathlib import Path
import importlib

from Subsea.config import CONFIG
from Subsea.storage import available_storages
from Subsea.storage._base import Storage

class StorageError(RuntimeError):
    pass


def load_storage( ) -> Storage :

  storage_type = CONFIG.storage.type
  valid_storages = available_storages( )

  if storage_type not in valid_storages:
    raise StorageError(
      f"Invalid storage.type '{storage_type}'. "
      f"Available: {sorted(valid_storages)}"
    )

  # Infer package name dynamically
  package_name = Path( __file__ ).resolve( ).parents[ 1 ].name

  module_path = f"{package_name}.storage.{storage_type}"
  storage = importlib.import_module( module_path )
 
  if not isinstance( storage, Storage ) :
    raise StorageError(
      f"Storage '{storage_type}' does not implement required interface"
    )

  return storage
