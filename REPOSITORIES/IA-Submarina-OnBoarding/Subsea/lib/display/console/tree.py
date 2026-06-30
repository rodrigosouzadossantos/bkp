#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: set tabstop=2 shiftwidth=2 softtabstop=2 expandtab:


from rich.tree import Tree

from .console import console

def count_files( node : dict ) -> int :

  count = 0

  for value in node.values():

    if not isinstance( value, dict ) :
      count += 1

    elif isinstance( value, dict ) :
      count += count_files( value )

  return count

def build_rich_tree(
  node : dict,
  tree : Tree,
  *,
  show_files : bool = True,
) -> None :

  for key, value in node.items():

    if not isinstance( value, dict ) :

      if not show_files:
        continue

      tree.add( f'{ key }' )
      continue

    file_count = count_files( value )

    branch = tree.add( f'{ key } (#{file_count})' )

    build_rich_tree(
      value,
      branch,
      show_files = show_files,
    )


def show_tree(
  root_label : str,
  data : dict,
  *,
  show_files : bool = True,
) -> None :

  '''
  Render a nested dict structure as a Rich tree.

  Directories -> dict
  Files       -> None
  '''

  tree = Tree( root_label )

  build_rich_tree(
    data,
    tree,
    show_files = show_files,
  )

  console.print( tree )

__all__ = [ 'show_tree' ]

