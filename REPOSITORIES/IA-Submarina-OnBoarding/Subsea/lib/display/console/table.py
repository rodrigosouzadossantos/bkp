#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: set tabstop=2 shiftwidth=2 softtabstop=2 expandtab:


from rich.table import Table

from .console import console


def show_table(
  title : str,
  columns : list[ str ],
  rows : list[ list ],
) -> None :

  table = Table(
    title = title,
    show_header = True,
    header_style = 'bold magenta',
  )

  for col in columns:
    table.add_column( col )

  for row in rows:
    table.add_row(
      *[ str( cell ) for cell in row ]
    )

  console.print( table )

__all__ = [ 'show_table' ]

