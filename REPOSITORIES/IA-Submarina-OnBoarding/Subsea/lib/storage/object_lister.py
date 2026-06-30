#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: set tabstop=2 shiftwidth=2 softtabstop=2 expandtab:


from typing import Iterable, Protocol


class ObjectLister( Protocol ) :

  '''
  Abstract object listing interface.

  Implementations may optimize listing
  depending on backend characteristics.
  '''

  def list_objects(
    self,
    prefix : str = '',
  ) -> Iterable[ str ] :
    ...

