#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: set tabstop=2 shiftwidth=2 softtabstop=2 expandtab:





from pyspark.sql import SparkSession

from Subsea.observability import SubseaComponent, trace


class SparkAdapter( SubseaComponent ) :

  def __init__( self ) :

    super( ).__init__()

    self.spark = SparkSession.builder.getOrCreate( )

  @trace( )
  def read_parquet( self, path ) :

    return self.spark.read.parquet(
      path
    )


