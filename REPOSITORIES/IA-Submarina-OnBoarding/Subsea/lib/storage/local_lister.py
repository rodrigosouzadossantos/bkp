#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: set tabstop=2 shiftwidth=2 softtabstop=2 expandtab:


import os
from typing import Iterable


class LocalLister :

  '''
  Local filesystem object lister.
  '''

  def __init__(
    self,
    root : str,
  ) :

    self.root = root


  def list_objects(
    self,
    prefix : str = '',
  ) -> Iterable[ str ] :

    base = os.path.join(
      self.root,
      prefix,
    )

    for root, _, files in os.walk(
      base
    ) :

      for name in files :

        yield os.path.relpath(
          os.path.join(
            root,
            name,
          ),
          self.root,
        )
