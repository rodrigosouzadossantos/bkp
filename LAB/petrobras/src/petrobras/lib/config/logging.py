#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: set tabstop=2 shiftwidth=2 softtabstop=2 expandtab:

import logging
from logging.handlers import TimedRotatingFileHandler


def configure_observer_logging(
  logfile: str = "petrobras_observer.log",
  level_console: int = logging.INFO,
  level_file: int = logging.DEBUG,
  backup_days: int = 14,
) -> logging.Logger:
  """
  Configure logging for Observer:
    - Console output
    - Daily rotating file
  """

  logger = logging.getLogger("petrobras.observer")
  logger.setLevel(logging.DEBUG)
  logger.propagate = False

  formatter = logging.Formatter(
    "%(asctime)s %(levelname)s %(name)s %(message)s"
  )

  # ---------------- Console handler ----------------
  console_handler = logging.StreamHandler()
  console_handler.setLevel(level_console)
  console_handler.setFormatter(formatter)

  # ---------------- File handler (daily rotation) --
  file_handler = TimedRotatingFileHandler(
    logfile,
    when="midnight",
    interval=1,
    backupCount=backup_days,
    encoding="utf-8",
    utc=False,  # set True if you want UTC rotation
  )
  file_handler.setLevel(level_file)
  file_handler.setFormatter(formatter)

  # Avoid duplicate handlers
  logger.handlers.clear()
  logger.addHandler(console_handler)
  logger.addHandler(file_handler)

  return logger
