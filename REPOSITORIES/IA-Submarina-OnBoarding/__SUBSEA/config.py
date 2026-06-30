#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: set tabstop=2 shiftwidth=2 softtabstop=2 expandtab:



from pathlib import Path

class SubseaConfig :

  WORK_DIR = Path( './work' )
  LOG_DIR  = WORK_DIR / 'logs'
  DATA_DIR = WORK_DIR / 'data'

  ENABLE_GPU = True

  @classmethod
  def ensure_dirs( cls ) :

    for d in [ cls.WORK_DIR, cls.LOG_DIR, cls.DATA_DIR ] :
      d.mkdir( parents = True, exist_ok = True )


