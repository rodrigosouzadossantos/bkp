#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: set tabstop=2 shiftwidth=2 softtabstop=2 expandtab:





import duckdb

from Subsea.observability import SubseaComponent, trace


class DuckDBAdapter( SubseaComponent ) :

  @trace( )
  def query( self, sql ) :

    return duckdb.query(
      sql
    ).df( )


