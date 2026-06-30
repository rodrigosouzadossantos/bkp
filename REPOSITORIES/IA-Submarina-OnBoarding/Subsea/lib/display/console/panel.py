#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: set tabstop=2 shiftwidth=2 softtabstop=2 expandtab:


from rich.panel import Panel

from .console import console


def info( message : str ) -> None :

  console.print(
    Panel(
      message,
      title = 'INFO',
      border_style = 'cyan',
    )
  )


def warning( message : str ) -> None :

  console.print(
    Panel(
      message,
      title = 'WARNING',
      border_style = 'yellow',
    )
  )


def error( message : str ) -> None :

  console.print(
    Panel(
      message,
      title = 'ERROR',
      border_style = 'red',
    )
  )

__all__ = [
  'info',
  'warning',
  'error',
]

