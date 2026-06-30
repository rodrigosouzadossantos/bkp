#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: set tabstop=2 shiftwidth=2 softtabstop=2 expandtab:


from Subsea import CONSOLE



class CoralsView :

  def __init__( self, tree : dict ) -> None :
    self._tree = tree

  def __getitem__( self, key ):
    return self._tree[ key ]

  def _resolve_path(
    self,
    path : str | None,
  ) -> dict :

    if path is None or path == '':
      return self._tree

    parts = [
      p for p in path.strip( '/' ).split( '/' )
      if p
    ]

    node = self._tree

    for part in parts:

      if part not in node:
        raise KeyError(
          f'Path not found: { path }'
        )

      node = node[ part ]

      if node is None:
        raise KeyError(
          f'Path points to a file: { path }'
        )

    return node

  def __call__(
    self,
    *,
    path : str | None = None,
    show_files : bool = True,
    extensions : tuple[ str, ... ] = None,
    invert : bool = False,
  ):

    from .corals import Corals

    tree = Corals.filter_tree(
      self._resolve_path( path ),
      extensions = extensions,
      invert = invert,
    )

    CONSOLE.show_tree(
      path or 'root',
      tree,
      show_files = show_files,
    )

  def raw( self ) -> dict :
    return self._tree

