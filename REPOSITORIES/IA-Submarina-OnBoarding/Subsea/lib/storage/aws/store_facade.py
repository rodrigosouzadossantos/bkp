
from typing import Any, overload

from Subsea.storage.object_store import ObjectStore

from .store import S3ObjectStore


class S3ObjectStoreFacade :

  '''
  Transparent facade for creating S3ObjectStore instances.

  Exposed as STORAGE.store.

  Supports:
    - STORAGE.store( client = ... )
    - STORAGE.store( bucket = ..., region = ... )
  '''

  def __init__(
    self,
    client_factory,
  ) -> None :

    self._client_factory = client_factory

  # --------------------------------------------------
  # Make facade callable (CRITICAL)
  # --------------------------------------------------

  def __call__(
    self,
    *args,
    **kwargs,
  ) -> ObjectStore :

    return self.store(
      *args,
      **kwargs,
    )

  # --------------------------------------------------
  # Client factory
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

    if client is None:

      if bucket is None:
        raise ValueError(
          'bucket must be provided when client is not given'
        )

      client = self.client(
        bucket = bucket,
        region = region,
        **kwargs,
      )

    return S3ObjectStore(
      client = client,
      logger = logger,
      tracing = tracing,
    )

