#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: set tabstop=2 shiftwidth=2 softtabstop=2 expandtab:

from dataclasses import dataclass
from pathlib import Path


@dataclass( frozen = True )
class PathsConfig :
  base_dir : Path
  work_dir : Path
  data_dir : Path
  log_dir  : Path
  log_file : Path
  checkpoint_dir : Path

@dataclass( frozen = True )
class StorageConfig :
  type : str

@dataclass( frozen = True )
class RuntimeConfig :
  enable_gpu: bool

@dataclass( frozen = True )
class CoreConfig :
  ensure_directories : bool

@dataclass( frozen = True )
class PipelineConfig:
    bucket: str
    prefix: str

@dataclass( frozen = True )
class SubseaConfig :
  core  : CoreConfig
  paths : PathsConfig
  storage : StorageConfig
  runtime : RuntimeConfig
  pipelines: dict[ str, PipelineConfig ]
