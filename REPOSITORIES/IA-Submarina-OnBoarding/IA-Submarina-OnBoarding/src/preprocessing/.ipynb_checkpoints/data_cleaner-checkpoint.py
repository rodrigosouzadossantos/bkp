#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import polars as pl

# ============================================
# Define schema based on your description
# ============================================

schema = {
  'id'     : pl.Int32,

  'os'     : pl.Utf8,
  'group'  : pl.Categorical,
  'desc'   : pl.Utf8,
  'date'   : pl.Date,
  'class'  : pl.Categorical,
  'un'     : pl.Categorical,

  'field_number'   : pl.Int16,
  'field_location' : pl.Categorical,
  'depth'          : pl.Int32, # could not parse '87693' as dtype 'i16' at column 'depth'

  'suit'     : pl.Categorical,
  'shipment' : pl.Utf8,

  'company'  : pl.Categorical,
  'resource' : pl.Categorical,
  'vessel'   : pl.Categorical,
  'relatbar' : pl.Utf8,
  'n1710'    : pl.Utf8,

  'files_count' : pl.Int64,
  'files_size'  : pl.Float64,
  'files_missing_count' : pl.Int64,
  'files_missing_size'  : pl.Float64,
  'files_oldest'     : pl.Date,
  'files_newest'     : pl.Date,
  'inventory_first'  : pl.Date,
  'inventory_newest' : pl.Date,
  'files_missing_lastseen' : pl.Date,

  'bucket' : pl.Categorical,
  'base'   : pl.Utf8,
  'folder' : pl.Utf8,
  'path'   : pl.Utf8,
}

# ============================================
# Load CSV with forced schema
# ============================================

from pathlib import Path
data = Path(__file__).parent.parent.resolve() / 'data/raw/dados-submarinos'

df = pl.read_excel(
  f'{data}.xlsx',
  engine = 'calamine',
  sheet_id = 0,
  schema_overrides = schema,
  infer_schema_length = None
)

# -----------------------------
# 
# -----------------------------

for key, sheet in df.items( ) :
  df[ key ] = sheet.with_columns(
    pl.lit( key ).alias( 'source' )
  )

# -----------------------------
# 
# -----------------------------

df = pl.concat( df.values( ) )


# ============================================
#
# ============================================

for col, dtype in df.schema.items():
  if dtype == pl.Categorical:

    phys_name  = f'{col}_physical'
    count_name = f'{col}_count'
    norm_name =  f'{col}_norm'

    df = df.with_columns(

      pl.col( col )
        .cast( pl.String )
        .str.to_lowercase( )
        .str.strip_chars( )
        .str.normalize( 'NFKD' )
        .str.replace_all( r'[\u0300-\u036f]', '' )        
        .cast( pl.Categorical )
        .alias( norm_name ),

      pl.col( col )
        .to_physical( )
        .alias( phys_name ),

      pl.col( col )
        .count( )
        .over( col )
        .alias( count_name )

    )

    # -----------------------------
    # rearrange so the physical
    # column is placed immediately
    # after the original
    # -----------------------------
    cols = df.columns

    cols.remove( count_name )
    cols.insert(
      cols.index( col ) + 1, count_name
    )

    cols.remove( phys_name )
    cols.insert(
      cols.index( col ) + 1, phys_name
    )

    cols.remove( norm_name )
    cols.insert(
      cols.index( col ) + 1, norm_name
    )

    df = df.select( cols )

# -----------------------------
#
# -----------------------------
df = df.with_columns(
  pl.col( 'company' )
    .fill_null(
      pl.col( 'company' )
      .forward_fill( )
      .over( 'vessel' )
    )
)

# -----------------------------
#
# -----------------------------
df = df.with_columns(
    pl.col( 'desc' )
        .str.to_lowercase( )
        .str.strip_chars( )
        .str.normalize( 'NFKD' )
        .str.replace_all( r'[\u0300-\u036f]', '' ),
).with_columns(
    pl.struct( [ 'desc', 'field_location_norm', 'class_norm' ] ).map_elements(
        lambda row: (
            ( row[ 'desc' ] or '' )
            .lower( )
            .strip( )
            if not row[ 'field_location_norm' ] and not row[ 'class_norm' ]
            else ( row[ 'desc' ] or '' )
                .lower( )
                .strip( )
                .replace( row[ 'field_location_norm' ], '' )
                .replace( ( row[ 'class_norm' ] or '' ), '' )
                .strip( )
        ),
        return_dtype = pl.String
    )
    .str.replace_all( r'[/]', ' ' )
    .str.replace_all( r'\s+', ' ' )
    .str.strip_chars( ).alias( 'desc_norm' )
)

cols = df.columns
cols.remove( 'desc_norm' )
cols.insert(
  cols.index( 'desc' ) + 1, 'desc_norm'
)

df = df.select( cols )

# ============================================
# Save as Parquet
# ============================================
df.write_parquet( f'{data}.parquet' )

print( df.sample( ) )
