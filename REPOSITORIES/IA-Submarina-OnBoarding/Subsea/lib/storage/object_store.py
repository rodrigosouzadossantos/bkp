#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: set tabstop=2 shiftwidth=2 softtabstop=2 expandtab:


from typing import (
  Iterable,
  Protocol,
  BinaryIO
)

class ObjectStore( Protocol ) :

  """
  Abstract object storage interface.

  Pipelines and datasets must depend ONLY on this interface.
  Implementations must not add new public methods.
  """

  def exists( self, key : str ) -> bool :
    ...

  def open_writer(
    self,
    key : str,
  ) -> BinaryIO :
    ...

  def open_reader(
    self,
    key : str,
  ) -> BinaryIO :
    ...

  def download(
    self,
    key : str,
    dest_path : str,
  ) -> None :
    ...


  def upload(
    self,
    src_path : str,
    key : str,
  ) -> None :
    ...


  def stream(
    self,
    key : str,
    chunk_size : int = 8 * 1024 * 1024,
  ) -> Iterable[ bytes ] :
    ...


  def list(
    self,
    prefix : str = '',
    suffix : str | None = None,
  ) -> Iterable[ str ] :
    ...


  def delete(
    self,
    key : str,
    version_id : str | None = None,
  ) -> None :
    ...

