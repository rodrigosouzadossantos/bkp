#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: set tabstop=2 shiftwidth=2 softtabstop=2 expandtab:


from rich.progress import (
  Progress,
  SpinnerColumn,
  BarColumn,
  TextColumn,
  TimeElapsedColumn,
)

def create_progress(
  *,
  show_spinner : bool = True,
) -> Progress :

  columns = [ ]

  if show_spinner:
    columns.append( SpinnerColumn() )

  columns.extend(
    [
      TextColumn(
        '[progress.description]{task.description}'
      ),
      BarColumn(),
      TimeElapsedColumn(),
    ]
  )

  return Progress( *columns )

__all__ = [ 'create_progress' ]

