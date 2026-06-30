#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: set tabstop=2 shiftwidth=2 softtabstop=2 expandtab:


import time
import logging

from rich.console import Console
from rich.status import Status


class SubseaComponent :

  """
  Base class for all Subsea components.

  Guarantees:
  - structured logging
  - Rich narration
  - explainable execution
  """

  console = Console( )

  def __init__( self ) :

    self.log = logging.getLogger(
      f'Subsea.{self.__class__.__name__}'
    )

  def step( self, message ) :

    """
    Announce a logical step.
    """

    self.log.info( message )
    self.console.log( f'[bold cyan]{message}' )


def trace( label = None ) :

  """
  Decorator for observable execution.
  """

  def decorator( fn ) :

    name = label or fn.__name__

    def wrapper( self, *args, **kwargs ) :

      full = f'{self.__class__.__name__}.{name}'

      start = time.time( )

      self.log.info( f'start {full}' )

      with Status(
        f'[green]Running {full}...',
        console = self.console
      ) :

        try :
          result = fn( self, *args, **kwargs )

          elapsed = time.time( ) - start

          self.log.info(
            f'end {full} elapsed={elapsed:.2f}s'
          )

          self.console.log(
            f'[green]Completed {full} in {elapsed:.2f}s'
          )

          return result

        except Exception as e :

          elapsed = time.time( ) - start

          self.log.exception(
            f'failed {full} after {elapsed:.2f}s'
          )

          self.console.log(
            f'[bold red]Failed {full}: {e}'
          )

          raise

    return wrapper

  return decorator
