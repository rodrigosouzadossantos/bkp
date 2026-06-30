#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: set tabstop=2 shiftwidth=2 softtabstop=2 noexpandtab:

import polars as pl
import numpy as np
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import plotly.graph_objects as go


def data_size_total( df ):
  from .easy_search import human_bytes
  pivoted = (
    df.filter(
      pl.col( 'files_size' ).is_not_null() )
    .with_columns(
      pl.col( 'date' ).cast(
        pl.Datetime ).dt.strftime( '%Y-%m' )
      .alias( 'year_month' ) ).group_by(
        [ 'un', 'year_month' ] ).agg( [
          pl.col( 'files_size' ).sum().alias(
            'total_bytes' ),
        ] ).pivot(
          values = 'total_bytes',
          index = 'un',
          on = 'year_month',
        ) )

  if "null" in pivoted.columns:
    pivoted = pivoted.drop( 'null' )

  month_cols = [
    c for c in pivoted.columns if c != 'un'
  ]

  sorted_pivot = (
    pivoted.filter(
      pl.col( 'un' ) != 'cat' ).with_columns(
        pl.sum_horizontal( [
          pl.col( c ) for c in month_cols
        ] ).alias( 'total_bytes' ) ).sort(
          'total_bytes', descending = True ) )

  sorted_month_cols = sorted(
    month_cols, reverse = True )
  column_order = [ 'un', 'total_bytes'
                  ] + sorted_month_cols
  sorted_pivot = sorted_pivot.select(
    column_order )

  result_numeric = sorted_pivot.clone()

  result_human = (
    sorted_pivot.with_columns( [
      human_bytes( pl.col( c ) ).alias( c )
      for c in [ 'total_bytes' ] +
      sorted_month_cols
    ] ).fill_null( '-' ) )

  # Convert tables to pandas
  pdf_numeric = result_numeric.to_pandas()
  pdf_human = result_human.to_pandas()

  # Extract index and columns
  un_list = pdf_numeric[ 'un' ].tolist()
  month_cols = [
    c for c in pdf_numeric.columns
    if c not in [ 'un', 'total_bytes' ]
  ]

  # --------------------------
  # Build numeric matrix
  # --------------------------
  matrix_numeric = pdf_numeric[
    month_cols ].to_numpy( dtype = float )

  # --------------------------
  # Build human matrix
  # --------------------------
  matrix_human = pdf_human[ month_cols ].replace(
    '-', np.nan ).to_numpy()

  def yearly_un():
    years = sorted(
      { m[ : 4 ]
        for m in month_cols },
      reverse = True )

    # --------------------------------------
    # numeric yearly matrix
    # --------------------------------------
    year_matrix = []
    for row in matrix_numeric:
      yearly = []
      for y in years:
        vals = [
          row[ i ]
          for i, m in enumerate( month_cols )
          if m.startswith( y )
        ]
        total = np.nansum( vals )
        yearly.append( np.nan if total ==
                       0 else total )
      year_matrix.append( yearly )

    # --------------------------------------
    # human readable yearly matrix
    # --------------------------------------
    year_human_matrix = []
    for row in pdf_human[ month_cols ].to_numpy():
      yearly = []
      for y in years:
        vals = [
          row[ i ]
          for i, m in enumerate( month_cols )
          if m.startswith( y )
        ]
        vals = [ v for v in vals if v != '-' ]
        yearly.append( '-' if len( vals ) ==
                       0 else vals[ 0 ] )
      year_human_matrix.append( yearly )

    num_years = len( years )
    annot_font = max( 6, int( 70 / num_years ) )

    plt.figure(
      figsize = ( len( years ) * 1.4,
                  len( un_list ) * 0.7 ) )

    ax = sns.heatmap(
      year_matrix,
      cmap = 'YlGnBu',
      linewidths = 0.5,
      linecolor = 'gray',
      square = True,
      annot = year_human_matrix,
      fmt = '',
      annot_kws = {
        'fontsize': annot_font
      },
      cbar_kws = {
        'label': 'Total Bytes (per year)'
      },
    )

    ax.set_xticklabels(
      years,
      rotation = 45,
      ha = 'right',
      fontsize = 10 )
    ax.set_yticklabels(
      un_list, rotation = 0, fontsize = 10 )

    plt.title(
      'Yearly Aggregated Storage per UN',
      fontsize = 14 )
    plt.tight_layout()
    plt.show()

  def monthly_un_line():
    fig = go.Figure()

    step = 4
    tickvals = [
      month_cols[ i ]
      for i in range( 0, len( month_cols ), step )
    ]
    hover_human = pdf_human[ month_cols ].replace(
      '-', np.nan ).to_numpy()

    for idx, un in enumerate( un_list ):
      y = matrix_numeric[ idx ]
      custom_hover = hover_human[ idx ]
      visible = True if idx < 4 else 'legendonly'  # first → fourth visible
      fig.add_trace(
        go.Scatter(
          x = month_cols,
          y = y,
          mode = 'lines+markers',
          name = un,
          visible = visible,
          customdata = custom_hover,
          hovertemplate =
          'UN: %{fullData.name}<br>' +
          'Month: %{x}<br>' +
          'Total: %{customdata}<extra></extra>' )
      )

    fig.update_layout(
      title = 'Monthly Storage Evolution per UN',
      width = 1100,
      height = 500,
      margin = dict(
        l = 60, r = 200, t = 60, b = 120 ),
      xaxis = dict(
        tickmode = 'array',
        tickvals = tickvals,
        ticktext = tickvals,
        tickangle = 45 ),
      yaxis = dict( title = 'Bytes (numeric)' ),
      legend = dict(
        x = 1.02,
        y = 1,
        xanchor = 'left',
        yanchor = 'top',
        bgcolor = 'rgba(255,255,255,0.85)',
        borderwidth = 1,
        font = dict( size = 10 ) ) )

    fig.show()

  def monthly_un_heatmap():
    num_cols = len( month_cols )
    annot_font = max( 6, int( 50 / num_cols ) )
    plt.figure(
      figsize = ( len( month_cols ) * 1.2,
                  len( un_list ) * 0.6 ) )
    ax = sns.heatmap(
      matrix_numeric,
      annot = matrix_human,
      fmt = '',
      cmap = 'YlGnBu',
      linewidths = 0.5,
      linecolor = 'gray',
      square = True,
      annot_kws = {
        'fontsize': annot_font
      },
      cbar_kws = {
        'label': 'Total Bytes (numeric)'
      },
    )
    ax.set_xticklabels(
      month_cols,
      rotation = 45,
      ha = 'right',
      fontsize = 9 )
    ax.set_yticklabels(
      un_list, rotation = 0, fontsize = 9 )
    plt.title(
      'Heatmap: Total Bytes per UN per Month',
      fontsize = 14 )
    plt.tight_layout()
    plt.show()

  def monthly_un_heatmap_logscale():
    num_cols = len( month_cols )
    annot_font = max( 6, int( 80 / num_cols ) )
    plt.figure(
      figsize = ( len( month_cols ) * 1.2,
                  len( un_list ) * 0.6 ) )
    matrix_log = np.where( matrix_numeric <= 0,
                           np.nan,
                           matrix_numeric )
    ax = sns.heatmap(
      matrix_log,
      norm = 'log',
      cmap = 'YlOrRd',
      linewidths = 0.5,
      linecolor = "gray",
      square = True,
      annot = matrix_human,
      fmt = '',
      annot_kws = {
        'fontsize': annot_font
      },
      cbar_kws = {
        'label': 'Bytes (log scale)'
      },
    )
    ax.set_xticklabels(
      month_cols,
      rotation = 45,
      ha = 'right',
      fontsize = 9 )
    ax.set_yticklabels(
      un_list, rotation = 0, fontsize = 9 )
    plt.title(
      'Log-Scale Heatmap: Total Bytes per UN per Month',
      fontsize = 14 )
    plt.tight_layout()
    plt.show()

  return ( yearly_un, monthly_un_line,
           monthly_un_heatmap,
           monthly_un_heatmap_logscale )
