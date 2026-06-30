#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: set tabstop=2 shiftwidth=2 softtabstop=2 expandtab:


from pathlib import Path


class SubseaConfig :

  WORK_DIR = Path( './work' )
  LOG_DIR  = WORK_DIR / 'logs'
  DATA_DIR = WORK_DIR / 'data'

  LOG_FILE = LOG_DIR / 'subsea.log'

  ENABLE_GPU = True

  def __init__( self ) :

    self.ensure_dirs()

  @classmethod
  def ensure_dirs( cls ) :

    for d in [ cls.WORK_DIR, cls.LOG_DIR, cls.DATA_DIR ] :
      d.mkdir( parents = True, exist_ok = True )

CONFIG = SubseaConfig( )


#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: set tabstop=2 shiftwidth=2 softtabstop=2 expandtab:
#
#
import os
from pathlib import Path
#
#
class SubseaConfig :
#
  """
  Central configuration and runtime environment.
  """
#
  # --------------------------------------------------
  # Resolve base directory
  # --------------------------------------------------
#
  _BASE_DIR = Path(
    os.environ.get(
      'SUBSEA_BASE_DIR',
      Path( __file__ ).resolve().parents[ 1 ]
    )
  )
#
  # --------------------------------------------------
  # Working directories
  # --------------------------------------------------
#
  WORK_DIR = _BASE_DIR / 'work'
  LOG_DIR  = WORK_DIR / 'logs'
  DATA_DIR = WORK_DIR / 'data'
#
  LOG_FILE = LOG_DIR / 'subsea.log'
#
  ENABLE_GPU = True
#
  def __init__( self ) :
#
    self.ensure_dirs()
#
  @classmethod
  def ensure_dirs( cls ) :
#
    for d in ( cls.WORK_DIR, cls.LOG_DIR, cls.DATA_DIR ) :
      d.mkdir( parents = True, exist_ok = True )
#
#
# Singleton instance (forces initialization)
CONFIG = SubseaConfig( )