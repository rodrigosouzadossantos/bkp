#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: set tabstop=2 shiftwidth=2 softtabstop=2 noexpandtab:

import polars as pl

import plotly.express as px
import plotly.graph_objects as go

#from . import data_size
#from .data_size import data_size_total
from .data_size import data_size_total as ds_total
from .dashboard import build_dashboard

def load( ) -> pl.DataFrame :
	from pathlib import Path
	data = Path(__file__).parent.parent.parent.resolve() / 'data/raw/dados-submarinos'
	return pl.read_parquet(  f'{data}.parquet' )

def data_size( df ) -> pl.DataFrame :
  return df.select(
    pl.col( 'files_size' ).sum( )
  ).with_columns(
    human_bytes( pl.col( 'files_size' ) )
  )

# -----------------------------
# Human-readable bytes function
# (vectorized)
# -----------------------------

def human_bytes_IEC( col ) :
  return (
    pl.when( col < ( 2**10 ) ).then( col.cast(pl.Utf8) + " B" )
      .when( col < ( 2**10 )**2 ).then( ( col / ( 2**10 ) ).round( 2 ).cast( pl.Utf8 ) + " KiB" )
      .when( col < ( 2**10 )**3 ).then( ( col / ( 2**10 )**2 ).round( 2 ).cast( pl.Utf8 ) + " MiB" )
      .when( col < ( 2**10 )**4 ).then( ( col / ( 2**10 )**3 ).round( 2 ).cast( pl.Utf8 ) + " GiB" )
      .when( col < ( 2**10 )**5 ).then( ( col / ( 2**10 )**4 ).round( 2 ).cast( pl.Utf8 ) + " TiB" )
      .when( col < ( 2**10 )**6 ).then( ( col / ( 2**10 )**5 ).round( 2 ).cast( pl.Utf8 ) + " PiB" )
      .when( col < ( 2**10 )**7 ).then( ( col / ( 2**10 )**6 ).round( 2 ).cast( pl.Utf8 ) + " EiB" )
      .when( col < ( 2**10 )**8 ).then( ( col / ( 2**10 )**7 ).round( 2 ).cast( pl.Utf8 ) + " ZiB" )
      .otherwise( ( col / ( 2**10 )**8 ).round( 2 ).cast( pl.Utf8 ) + " YiB" )
)

def human_bytes( col ) :
  return (
    pl.when( col < ( 10**3 ) ).then( col.cast(pl.Utf8) + " B" )
      .when( col < ( 10**3 )**2 ).then( ( col / ( 10**3 ) ).round( 2 ).cast( pl.Utf8 ) + " KB" )
      .when( col < ( 10**3 )**3 ).then( ( col / ( 10**3 )**2 ).round( 2 ).cast( pl.Utf8 ) + " MB" )
      .when( col < ( 10**3 )**4 ).then( ( col / ( 10**3 )**3 ).round( 2 ).cast( pl.Utf8 ) + " GB" )
      .when( col < ( 10**3 )**5 ).then( ( col / ( 10**3 )**4 ).round( 2 ).cast( pl.Utf8 ) + " TB" )
      .when( col < ( 10**3 )**6 ).then( ( col / ( 10**3 )**5 ).round( 2 ).cast( pl.Utf8 ) + " PB" )
      .when( col < ( 10**3 )**7 ).then( ( col / ( 10**3 )**6 ).round( 2 ).cast( pl.Utf8 ) + " EB" )
      .when( col < ( 10**3 )**8 ).then( ( col / ( 10**3 )**7 ).round( 2 ).cast( pl.Utf8 ) + " ZB" )
      .otherwise( ( col / ( 10**3 )**8 ).round( 2 ).cast( pl.Utf8 ) + " YB" )
)


def data_monthly( df: pl.DataFrame, dims: list[ str ] = [ ] ) -> pl.DataFrame :
  """
  Group dataframe by:
  - year_month (derived from date column)
  - dynamic list of dimensions (dims)
  and compute human-readable file sizes.
  """

  return (
    df.group_by( [
        pl.col("date")
          #.dt.truncate( '1mo' )
          .dt.strftime( '%Y-%m' )
          .alias( 'year_month' )
      ] + [ pl.col( c ) for c in dims ] )
      .agg(
        pl.col( 'files_size' )
          .sum( )
          .alias( 'bytes_total' )
      )
      .with_columns(
        human_bytes( pl.col( 'bytes_total' ) )
          .alias("size")
      )
      .sort(
        [ 'year_month', 'bytes_total' ],
        descending = [ False, True ]
      )
  )

def plot_data_monthly( df_result : pl.DataFrame, dims: list[ str ] = [ ] ) -> pl.DataFrame :
  """
  df_result = output of data_month( )
  dims = same dims passed into data_month( )
  """
  
  # Convert Polars → pandas for Plotly
  pdf = df_result.to_pandas( )

  # Use first dimension for color grouping (if any)
  color_dim = dims[ 0 ] if len( dims ) > 0 else None
  
  fig = px.bar(
    pdf,
    x      = 'year_month',
    y      = 'bytes_total',
    color  = color_dim,     # None → no color grouping
    text   = 'size',         # human-readable labels
    title  = 'Monthly Storage Usage',
    height = 650,
    width  = 1200,
  )
  
  fig.update_traces( textposition = 'outside' )
  fig.update_layout(
    xaxis_title = 'Year-Month',
    yaxis_title = 'Bytes Total',
    xaxis_tickangle = 45
  )
  
  fig.show( )

  return df_result

def data( df : pl.DataFrame, dims : list[ str ] = [ ] ) -> pl.DataFrame :
  return plot_data_monthly( data_monthly( df, dims ), dims )

def plot_data( df : pl.DataFrame, dims : list[ str ] = [ ] ) -> pl.DataFrame :
	df = data_monthly( df, dims )

	plot_monthly_sizes( df, dims )
	plot_monthly_sizes_3d( df, dims )
	plot_monthly_sizes_3d_lines( df, dims )

	return df

def plot_monthly_sizes(df_result: pl.DataFrame, dims: list[str] = [ ] ) :
  """
    df_result: output of sum_files_by_month()
    dims: optional list of grouping dimensions
    Automatically selects the best plot type:
    - 0 dims → simple bar chart
    - 1 dim  → line chart with color
    - 2+ dims → stacked bar chart (first dim used as color)
  """

  pdf = df_result.to_pandas()

  # The dimension used for color grouping (if any)
  color_dim = dims[ 0 ] if len( dims ) > 0 else None

  # ───────────────────────────────
  # CASE A: No dimensions → bar chart
  # ───────────────────────────────
  if len( dims ) == 0 :
    fig = px.bar(
      pdf,
      x="year_month",
      y="bytes_total",
      text="size",
      title="Monthly Storage Usage",
      height=600,
      width=1200,
    )
    fig.update_traces(textposition="outside")
  # ───────────────────────────────
  # CASE B: One dimension → line chart
  # ───────────────────────────────
  elif len(dims) == 1 :
    fig = px.line(
      pdf,
      x="year_month",
      y="bytes_total",
      color=color_dim,
      markers=True,
      title=f"Monthly Storage Usage by {color_dim}",
      height=600,
      width=1200,
    )
    fig.update_traces(text=None)
  # ───────────────────────────────
  # CASE C: Two or more dims → stacked bar
  # ───────────────────────────────
  else :
    fig = px.bar(
      pdf,
      x="year_month",
      y="bytes_total",
      color=color_dim,
      text="size",
      title=f"Monthly Storage Usage grouped by {', '.join(dims)}",
      height=600,
      width=1200,
    )
    fig.update_traces(textposition="outside")

  # Common formatting
  fig.update_layout(
    xaxis_title="Year‑Month",
    yaxis_title="Total Bytes",
    xaxis_tickangle=45,
    yaxis=dict(autorange=True)
  )
  fig.show()



def plot_monthly_sizes_3d(df_result: pl.DataFrame, dims: list[str] = None):
  """
  3D version of monthly storage usage.
  Requires at least 1 grouping dimension.
  """
  if not dims or len(dims) < 1:
        raise ValueError("3D plot requires at least one dimension in `dims`.")
  # Only the first dimension will be used for the 3D Y-axis
  dim = dims[0]
  pdf = df_result.to_pandas()
  fig = px.scatter_3d(
        pdf,
        x="year_month",
        y=dim,
        z="bytes_total",
        color=dim,
        size="bytes_total",
        title=f"3D Monthly Storage Usage by {dim}",
        height=800,
        width=1100
    )
  fig.update_layout(scene=dict(
        xaxis_title="Year-Month",
        yaxis_title=dim,
        zaxis_title="Bytes Total",
    ))
  fig.show()




def plot_monthly_sizes_3d_lines(df_result: pl.DataFrame, dims: list[str] = None):
  if not dims or len(dims) < 1:
        raise ValueError("3D plot requires at least one dimension in `dims`.")
  dim = dims[0]
  pdf = df_result.to_pandas()
  fig = go.Figure()
  for value in pdf[dim].unique():
      dfv = pdf[pdf[dim] == value]
      fig.add_trace(go.Scatter3d(
            x=dfv["year_month"],
            y=dfv[dim],
            z=dfv["bytes_total"],
            mode="lines+markers",
            name=str(value),
            marker=dict(size=3),
            line=dict(width=4),
        ))
  fig.update_layout(
        title=f"3D Monthly Storage Usage by {dim} (Lines)",
        height=800,
        width=1100,
        scene=dict(
            xaxis_title="Year-Month",
            yaxis_title=dim,
            zaxis_title="Bytes Total"
        )
    )
  fig.show()	
