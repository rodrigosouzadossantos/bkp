#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: set tabstop=2 shiftwidth=2 softtabstop=2 expandtab:



import logging

from rich.console import Console
from rich.logging import RichHandler

from .config import SubseaConfig

class SubseaLogger :

  console = Console( )

  @classmethod
  def setup( cls ) :

    SubseaConfig.ensure_dirs( )

    logging.basicConfig(
      level = logging.INFO,
      format = '%(asctime)s %(levelname)s %(message)s',
      handlers = [
        RichHandler( console = cls.console ),
        logging.FileHandler(
          SubseaConfig.LOG_DIR / 'processing.log'
        )
      ]
    )

    return logging.getLogger( 'Subsea' )


