#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: set tabstop=2 shiftwidth=2 softtabstop=2 expandtab:

from pathlib import Path
import os
import yaml

from ._model import SubseaConfig, StorageConfig

class ConfigError( RuntimeError ) :
    pass

def _load_config( ) -> SubseaConfig :
  config_path = Path( __file__ ).resolve( ).parent / 'config.yaml'

  if not config_path.exists( ) :
    raise ConfigError( f'Config file not found: {config_path}' )

  with config_path.open( 'r', encoding = 'utf-8' ) as c :
    raw = yaml.safe_load( c ) or { }

  # --- Validation ---
  if 'storage' not in raw or 'type' not in raw[ 'storage' ] :
    raise ConfigError( 'Missing required config: storage.type' )

  storage_type = raw[ 'storage' ][ 'type' ]

  # --- Environment override ---
  storage_type = os.getenv( 'SUBSEA_STORAGE_TYPE', storage_type )

  if not isinstance( storage_type, str ) or not storage_type :
    raise ConfigError( 'storage.type must be a non-empty string' )

  return SubseaConfig(
    storage = StorageConfig( type = storage_type )
  )

CONFIG = _load_config( )
