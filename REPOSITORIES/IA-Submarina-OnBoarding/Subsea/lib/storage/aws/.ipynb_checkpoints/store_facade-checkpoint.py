#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: set tabstop=2 shiftwidth=2 softtabstop=2 expandtab:


from typing import Any, overload

from Subsea.storage.object_store import ObjectStore

from .store import S3ObjectStore


class S3ObjectStoreFacade :

  '''
  Transparent facade for creating S3ObjectStore instances.

  This facade is designed to be exposed as STORAGE.store.

  It supports:

    1. Legacy usage (explicit client):

       store = STORAGE.store(
         client = STORAGE.client(
           bucket = 'analise-dados',
           region = 'us-east-1',
         ),
       )

    2. Preferred usage (implicit client creation):

       store = STORAGE.store(
         bucket = 'analise-dados',
         region = 'us-east-1',
       )

  The underlying S3ObjectStore implementation remains unchanged.
  '''

  def __init__(
    self,
    client_factory,
  ) -> None :

    # client_factory is typically S3Client
    self._client_factory = client_factory

  # --------------------------------------------------
  # Client factory (pass-through)
  # --------------------------------------------------

  def client(
    self,
    *,
    bucket : str,
    region : str | None = None,
    **kwargs : Any,
  ):

    return self._client_factory(
      bucket = bucket,
      region = region,
      **kwargs,
    )

  # --------------------------------------------------
  # Type-safe overloads
  # --------------------------------------------------

  @overload
  def store(
    self,
    *,
    client,
    logger = None,
    tracing : bool = True,
  ) -> ObjectStore :
    ...

  @overload
  def store(
    self,
    *,
    bucket : str,
    region : str | None = None,
    logger = None,
    tracing : bool = True,
    **kwargs : Any,
  ) -> ObjectStore :
    ...

  # --------------------------------------------------
  # Runtime implementation
  # --------------------------------------------------

  def store(
    self,
    *,
    client = None,
    bucket : str | None = None,
    region : str | None = None,
    logger = None,
    tracing : bool = True,
    **kwargs : Any,
  ) -> ObjectStore :

    # ----------------------------------------------
    # Preferred path: implicit client creation
    # ----------------------------------------------

    if client is None:

      if bucket is None:
        raise ValueError(
          'bucket must be provided when client is not given'
        )

      client = self.client(
        bucket = bucket,
        region = region or 'us-east-1',
        **kwargs,
      )

    # ----------------------------------------------
    # Delegate to real S3ObjectStore
    # ----------------------------------------------

    return S3ObjectStore(
      client = client,
      logger = logger,
      tracing = tracing,
    )

