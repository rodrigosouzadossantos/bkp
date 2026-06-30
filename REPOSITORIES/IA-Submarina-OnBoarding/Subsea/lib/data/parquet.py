#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: set tabstop=2 shiftwidth=2 softtabstop=2 expandtab:





import polars as pl

from Subsea.observability import SubseaComponent, trace


class ParquetStore( SubseaComponent ) :

  @trace( )
  def write( self, df, path ) :

    self.step(
      "Writing parquet %s" % path
    )

    df.write_parquet(
      path
    )

  @trace( )
  def read( self, path ) :

    self.step(
      "Reading parquet %s" % path
    )

    return pl.read_parquet(
      path
    )


