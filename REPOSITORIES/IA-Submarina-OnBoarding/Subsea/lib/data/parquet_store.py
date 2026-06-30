#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: set tabstop=2 shiftwidth=2 softtabstop=2 expandtab:


import io
import logging

from typing import Any, Literal

import polars as pl

from Subsea.storage.object_store import ObjectStore
from Subsea.observability.tracing import TracingPolicy


Engine = Literal[
  'polars',
  'duckdb',
  'spark',
]


class ParquetStore :

  '''
  ParquetStore manages Parquet datasets on top of an ObjectStore.

  Responsibilities:
  - decide Parquet dataset location (key layout)
  - read/write Parquet using selected engine
  - remain fully storage-agnostic

  Storage backends (S3, local, etc.) are provided via ObjectStore.
  '''

  def __init__(
    self,
    store : ObjectStore,
    base_prefix : str,
    engine : Engine = 'polars',
    logger : logging.Logger | None = None,
    tracing : bool = True,
  ) :

    self.store = store
    self.base_prefix = base_prefix.rstrip( '/' )
    self.engine = engine

    self.log = logger or logging.getLogger(
      f'ParquetStore[{self.base_prefix}]'
    )

    self.tracing = TracingPolicy(
      name = 'ParquetStore',
      logger = self.log,
      enabled = tracing,
    )

    self.log.info(
      'Initialized ParquetStore prefix=%s engine=%s',
      self.base_prefix,
      engine,
    )


  def _key(
    self,
    name : str,
  ) -> str :

    return f'{self.base_prefix}/{name}.parquet'


  # =========================================================
  # Public API
  # =========================================================

  def write(
    self,
    name : str,
    data : Any,
  ) -> None :

    key = self._key( name )

    with self.tracing.operation(
      'write',
      dataset = name,
      key = key,
      engine = self.engine,
    ) :

      self.log.info(
        'Writing Parquet dataset %s',
        name,
      )

      if self.engine == 'polars' :

        self._write_polars(
          key,
          data,
        )

      elif self.engine == 'duckdb' :

        self._write_duckdb(
          key,
          data,
        )

      elif self.engine == 'spark' :

        self._write_spark(
          key,
          data,
        )

      else :

        raise ValueError(
          f'Unsupported engine: {self.engine}'
        )


  def read(
    self,
    name : str,
  ) -> Any :

    key = self._key( name )

    with self.tracing.operation(
      'read',
      dataset = name,
      key = key,
      engine = self.engine,
    ) :

      self.log.info(
        'Reading Parquet dataset %s',
        name,
      )

      if self.engine == 'polars' :

        return self._read_polars(
          key,
        )

      elif self.engine == 'duckdb' :

        return self._read_duckdb(
          key,
        )

      elif self.engine == 'spark' :

        return self._read_spark(
          key,
        )

      raise ValueError(
        f'Unsupported engine: {self.engine}'
      )


  # =========================================================
  # Polars engine
  # =========================================================

  def _write_polars(
    self,
    key : str,
    data : Any,
  ) -> None :

    if not isinstance(
      data,
      pl.DataFrame,
    ) :

      raise TypeError(
        'Polars engine expects pl.DataFrame'
      )

    with self.store.open_writer(
      key,
    ) as writer :

      data.write_parquet(
        writer,
      )


  def _read_polars(
    self,
    key : str,
  ) -> pl.DataFrame :

    with self.store.open_reader(
      key,
    ) as reader :

      return pl.read_parquet(
        reader,
      )


  # =========================================================
  # DuckDB engine
  # =========================================================

  def _write_duckdb(
    self,
    key : str,
    data : Any,
  ) -> None :

    import duckdb

    if not isinstance(
      data,
      pl.DataFrame,
    ) :

      raise TypeError(
        'DuckDB engine expects pl.DataFrame'
      )

    with self.store.open_writer(
      key,
    ) as writer :

      buffer = io.BytesIO( )

      duckdb.query(
        'COPY (SELECT * FROM data) TO ? (FORMAT PARQUET)',
        [ buffer ],
      )

      buffer.seek( 0 )

      writer.write(
        buffer.read( )
      )


  def _read_duckdb(
    self,
    key : str,
  ) -> Any :

    import duckdb

    with self.store.open_reader(
      key,
    ) as reader :

      buffer = io.BytesIO(
        reader.read( )
      )

      return duckdb.query(
        'SELECT * FROM read_parquet(?)',
        [ buffer ],
      ).df( )


  # =========================================================
  # Spark engine
  # =========================================================

  def _write_spark(
    self,
    key : str,
    data : Any,
  ) -> None :

    from pyspark.sql import DataFrame

    if not isinstance(
      data,
      DataFrame,
    ) :

      raise TypeError(
        'Spark engine expects pyspark.sql.DataFrame'
      )

    with self.store.open_writer(
      key,
    ) as writer :

      buffer = io.BytesIO( )

      data.write.mode(
        'overwrite'
      ).parquet(
        buffer,
      )

      buffer.seek( 0 )

      writer.write(
        buffer.read( )
      )


  def _read_spark(
    self,
    key : str,
  ) -> Any :

    from pyspark.sql import SparkSession

    spark = SparkSession.builder.getOrCreate( )

    with self.store.open_reader(
      key,
    ) as reader :

      buffer = io.BytesIO(
        reader.read( )
      )

      return spark.read.parquet(
        buffer,
      )

