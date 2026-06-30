#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: set tabstop=2 shiftwidth=2 softtabstop=2 expandtab:


import time
import logging

from contextlib import contextmanager

from rich.console import Console
from rich.status import Status


class TracingPolicy :

  """
  Centralized tracing policy.

  Responsibilities:
  - decide when tracing is applied
  - unify Rich UI and logging
  - avoid decorator abuse
  - keep tracing explicit and semantic
  """

  def __init__(
    self,
    name : str,
    logger : logging.Logger,
    console : Console | None = None,
    enabled : bool = True,
  ) :

    self.name = name
    self.log = logger
    self.log.propagate = False
    self.console = console or Console()
    self.enabled = enabled


  @contextmanager
  def operation(
    self,
    op : str,
    **context,
  ) :

    """
    Trace a semantic operation.

    Usage:
      with tracing.operation('download_file', key=key):
        ...
    """

    if not self.enabled :

      yield
      return

    label = f'{self.name}.{op}'

    ctx = ' '.join(
      f'{k}={v}'
      for k, v in context.items()
    )

    start = time.time()

    self.log.info(
      'start %s %s',
      label,
      ctx,
    )

    with Status(
      f'[green]Running {label}...',
      console = self.console,
    ) :

      try :

        yield

        elapsed = time.time() - start

        self.log.info(
          'end %s elapsed=%.2fs %s',
          label,
          elapsed,
          ctx,
        )

        self.console.log(
          f'[green]Completed {label} in {elapsed:.2f}s'
        )

      except Exception :

        elapsed = time.time() - start

        self.log.exception(
          'failed %s after %.2fs %s',
          label,
          elapsed,
          ctx,
        )

        self.console.log(
          f'[red]Failed {label}'
        )

        raise
