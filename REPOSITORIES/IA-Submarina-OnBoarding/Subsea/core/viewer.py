#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: set tabstop=2 shiftwidth=2 softtabstop=2 expandtab:


import logging

from typing import (
  Dict,
  List,
  Iterator,
  Iterable,
  Optional,
)

from Subsea import (
  Error,
  CONFIG,
  STORAGE,
  CONSOLE,
)

from ..lib.media.image import Image
from ..lib.media.image_loader import ImageLoader

from Subsea.observability.tracing import TracingPolicy


class Viewer :
  def __init__( self, root : str, tree : dict, filter_tree ) -> None :
    self.root = root
    self._tree = tree
    self.filter_tree = filter_tree

  def __getitem__( self, key ) :
    return self._tree[ key ]

  def __call__(
    self,
    *,
    path : str | None = None,
    show_files : bool = True,
    extensions : tuple[ str, ... ] = None,
    invert : bool = False,
    render : bool = False,
  ) -> dict :

    tree = self.filter_tree(
      self._resolve_path( path ),
      extensions = extensions,
      invert = invert,
    )

    if render :
      CONSOLE.show_tree(
        path or 'root',
        tree,
        show_files = show_files,
      )

    return tree

  @property
  def raw( self ) -> dict :
    return self._tree

  def _resolve_path(
    self,
    path : str | None,
  ) -> dict :

    if path is None or path == '':
      return self._tree

    path = f'{ self.root }/{ path }'


    def _normalize_path(
      path : str,
    ) -> list[ str ] :

      scheme = None

      if ':' in path:
          scheme, path = path.split(':', 1)

      parts = [
          p for p in path.strip('/').split('/')
          if p
      ]

      return ([scheme] if scheme else []) + parts

    parts = _normalize_path( path )

    node = self._tree

    def get_node_by_path( node : dict, parts : list[ str ] ) -> dict :
        current = node
        for part in parts :
            if part not in current :
                raise KeyError( f'Missing path element: "{part}"' )
            current = current[ part ]
        return current

    return get_node_by_path( node, parts )


  # --------------------------------------------------
  # Jupyter image display
  # --------------------------------------------------

  def show_images(
    self,
    *,
    path : str | None = None,
    max_images : int | None = None,
    grid : bool = False,
    cols : int = 4,
    figsize : tuple[ int, int ] = ( 12, 12 ),
    captions : bool = True,
    caption_fn = None,
    overlays = None,
    overlay_kwargs : dict | None = None,
  ) -> None :

    tree = self( path = path, render = False )

    images = [ ]

    def collect( node, parts ):
      for key, value in node.items():
        if isinstance( value, dict ):
          collect( value, parts + [ key ] )
        else:
          images.append(
            ( parts, key, value )
          )

    collect( tree, [ ] )

    if max_images:
      images = images[ : max_images ]

    if not images:
      return

    overlay_kwargs = overlay_kwargs or { }

    # ------------------------------------------
    # Helper: build caption
    # ------------------------------------------

    def make_caption( parts, filename, img ):

      if not captions:
        return None

      if caption_fn:
        return caption_fn( parts, filename, img )

      if parts:
        parent = parts[ -1 ]
        return f'{ parent } / { filename }'

      return filename

    # ------------------------------------------
    # Helper: apply overlay
    # ------------------------------------------

    def apply_overlay( img ):

      if overlays is None:
        return img

      mask = overlays( img )

      if mask is None:
        return img

      return img.overlay_mask(
        mask,
        **overlay_kwargs,
      )

    # ------------------------------------------
    # LINEAR DISPLAY
    # ------------------------------------------

    if not grid:

      for parts, name, img in images:

        rendered = apply_overlay( img )

        caption = make_caption( parts, name, img )

        if caption:
          print( caption )

        display( rendered )

      return

    # ------------------------------------------
    # GRID DISPLAY
    # ------------------------------------------

    import math
    import matplotlib.pyplot as plt

    n = len( images )
    rows = math.ceil( n / cols )

    fig, axes = plt.subplots(
      rows,
      cols,
      figsize = figsize,
    )

    axes = axes.flatten( )

    for ax, ( parts, name, img ) in zip( axes, images ):

      rendered = apply_overlay( img )

      ax.imshow( rendered.numpy )
      ax.axis( 'off' )

      caption = make_caption( parts, name, img )

      if caption:
        ax.set_title(
          caption,
          fontsize = 8,
        )

    # Hide unused axes
    for ax in axes[ n: ]:
      ax.axis( 'off' )

    plt.tight_layout( )
    plt.show( )

