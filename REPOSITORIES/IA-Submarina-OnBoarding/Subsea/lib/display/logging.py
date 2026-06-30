#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: set tabstop=2 shiftwidth=2 softtabstop=2 expandtab:


import logging

from rich.logging import RichHandler

from Subsea.config import CONFIG


def setup_logging( ) :

  logging.basicConfig(
    level = logging.INFO,
    handlers = [
      logging.FileHandler(
        CONFIG.paths.log_file
      )
    ],
    format = '%(asctime)s %(levelname)s %(name)s %(message)s',
  )


