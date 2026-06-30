#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: set tabstop=2 shiftwidth=2 softtabstop=2 expandtab:

from pathlib import Path
import os
import yaml

from ._model import (
  SubseaConfig,
  CoreConfig,
  PathsConfig,
  StorageConfig,
  RuntimeConfig,
  PipelineConfig,
)

class ConfigError( RuntimeError ) :
  pass


def _resolve_path( value : str, base_dir : Path ) -> Path :
  '''
  If path starts with '/', treat as absolute.
  Otherwise, resolve relative to base_dir.
  '''

  p = Path( value )
  return p if p.is_absolute( ) else base_dir / p


def _load_config( ) -> SubseaConfig :
  # ---------------- BASE DIR ----------------
  package_dir = Path( __file__ ).resolve( ).parents[ 1 ]
  base_dir = package_dir

  # ---------------- CONFIG FILE ----------------
  #config_path = Path( __file__ ).resolve( ).parent / 'config.yaml'
  #config_path = package_dir / 'config.yaml'

  config_env = os.environ.get( 'SUBSEA_CONFIG' )

  if not config_env :
    raise RuntimeError(
      'SUBSEA_CONFIG environment variable is not set'
    )

  config_path = Path( config_env ).expanduser( ).resolve( )

  if not config_path.exists( ):
    raise FileNotFoundError(
      f'SUBSEA_CONFIG points to non-existent file: { config_path }'
    )

  if not config_path.is_file( ):
    raise RuntimeError(
      f'SUBSEA_CONFIG must point to a file, got: { config_path }'
    )

  if not config_path.exists( ) :
    raise ConfigError( f'Config file not found : {config_path}' )

  with config_path.open( 'r', encoding = 'utf-8' ) as c :
    raw = yaml.safe_load( c ) or { }

  # ---------------- CORE ----------------
  ensure_dirs = raw.get( 'core', { } ).get( 'ensure_directories', True )
  
  if not isinstance( ensure_dirs, bool ) :
    raise ConfigError( 'core.ensure_directories must be boolean' )
  
  # ---------------- PATHS ----------------
  try :
    work_dir = _resolve_path(
      raw[ 'paths' ][ 'work' ],
      base_dir
    )
    data_dir = _resolve_path(
      raw[ 'paths' ][ 'data' ],
      work_dir
    )
    checkpoint_dir = _resolve_path(
      raw[ 'paths' ][ 'checkpoint'],
      work_dir
    )
    log_dir = _resolve_path(
      raw[ 'paths' ]['logs'],
      work_dir
    )
    log_file = _resolve_path(
      raw[ 'logging']['file'],
      log_dir
    )
  except KeyError as e :
    raise ConfigError( f'Missing path configuration: {e}' ) from e
  
  # ---------------- STORAGE ----------------
  storage_type = raw.get( 'storage', { } ).get( 'type' )
  storage_type = os.getenv( 'SUBSEA_STORAGE_TYPE', storage_type )
  
  if not storage_type :
    raise ConfigError( 'storage.type is required' )
  
  # ---------------- RUNTIME ----------------
  enable_gpu = raw.get( 'runtime', { } ).get( 'enable_gpu', False )
  
  if not isinstance( enable_gpu, bool ) :
    raise ConfigError( 'runtime.enable_gpu must be boolean' )
  
  # ---------------- CREATE DIRECTORIES ----------------
  if ensure_dirs :
    for d in (
      work_dir,
      data_dir,
      checkpoint_dir,
      log_dir
    ) :
      d.mkdir( parents = True, exist_ok = True )
  
  return SubseaConfig(
    core = CoreConfig( ensure_directories = ensure_dirs ),
    paths = PathsConfig(
      base_dir = base_dir,
      work_dir = work_dir,
      data_dir = data_dir,
      checkpoint_dir = checkpoint_dir,
      log_dir = log_dir,
      log_file = log_file,
      ),
    storage = StorageConfig( type = storage_type ),
    runtime = RuntimeConfig( enable_gpu = enable_gpu ),
    pipelines = {
      name: PipelineConfig( **cfg )
        for name, cfg in raw[ 'pipeline' ].items( )
    }
  )


CONFIG = _load_config( )
