#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: set tabstop=2 shiftwidth=2 softtabstop=2 noexpandtab:

import ipywidgets as widgets
from IPython.display import display
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import matplotlib.pyplot as plt
from wordcloud import WordCloud, STOPWORDS

import numpy as np

import polars as pl
from polars import DataFrame

import re


def build_wordcloud( df ) :
    x,y = np.ogrid[ : 300, : 300 ]
    mask = ( x - 150 ) ** 2 + ( y - 150 ) ** 2 > 130 ** 2
    mask = 255 * mask.astype( int )
    sw = set( STOPWORDS )
    sw.update( [ 'e', 'em', 'ou', 'de' ] )
    words = [ ]
    for s in df[ 'class_norm' ].to_list( ) :
        if isinstance( s, str ) :
            [ words.append( w ) for w in s.split( ) ]
    text = ' '.join( words )
    wc = WordCloud(
      width = 350,
      height = 350,
      background_color = 'white',
      colormap = 'viridis',
      max_words = 100,
      stopwords = sw,
      min_font_size = 10,
      mask = mask
    ).generate( text )
    img=wc.to_array( )
    fig = go.Figure( go.Image( z = img ) )
    fig.update_layout(
        width = 350,
        height = 350,
        margin = dict( l = 0, r = 0, t = 0, b = 0 )
    )
    fig.update_xaxes( showticklabels = False )
    fig.update_yaxes( showticklabels = False )
    output = widgets.Output( )
    with output :
      fig.show( )
    return output
  
def build_service_class_tab(df: pl.DataFrame):
    """
    Build content for the 'Service Classes' tab.
    Shows the relationship between service classes and data stored.
    """
    from .easy_search import human_bytes
    
    # ---- 1. Ensure the column exists ----------------------------------------
    if "class" not in df.columns:
        return widgets.HTML(
            "<h3>Service Classes</h3>"
            "<p style='color:red;'>Column 'class' not found in dataframe.</p>"
        )

    # ---- 2. Aggregate storage by class --------------------------------------
    df = df.filter(
      pl.col( 'cluster_label_kb' ).cast( pl.String ).is_in(
        df.filter(
          pl.col( 'class_count' ) > 160
        ).select( 'cluster_label_kb' )
        .to_series( )
        .cast( pl.String )
        .implode( )
    ) )

    df_agg = (
        df
        .group_by( 'cluster_label_kb' )
        .agg( [
            pl.col( 'cluster_label_st' ).first( ),
            pl.col( 'files_size' ).sum( ).alias( 'total_size' ),
            pl.col( 'files_count' ).sum( ).alias( 'total_files' ),
            pl.col( 'files_size' ).mean( ).alias( 'avg_size' ),
            pl.col( 'os' ).n_unique( ).alias( 'os_count' ),
            pl.len( ).alias( 'job_count' )
        ] )
        .sort( 'total_size', descending = True)
    )
  
    # ---- 3. Convert to Python lists for plotting ----------------------------
    classes = df_agg.select(
                pl.all( ).slice( 1 )
               )[ 'cluster_label_kb' ].to_list( )
    total_gb = [ round( x, 2 )
                for x in df_agg[ 'total_size' ].to_list( )
               ]
    total_files = df_agg[ 'total_files' ].to_list( )
    avg_size = df_agg[ 'avg_size' ].to_list( )
  
    # ---- 4. Create a bar chart ---------------------------------------------
    fig = go.Figure( )
    fig.add_bar(
      x = [ re.sub( r"\s*\(.*?\)", "", lbl ) for lbl in classes ],
      y = total_gb,
      marker_color = "#42a5f5",
      name = 'Total Size',
      hovertemplate = '<b>%{x}</b><br>Total Size: %{y}<extra></extra>'
    )
    fig.update_layout(
      title = 'Data Volume by Service Class',
      xaxis_title = 'Service Class',
      yaxis_title = 'Size',
      width = 700,
      height = 350,
      template = 'plotly_white',
      margin = dict( l = 40, r = 40, t = 40, b = 40 )
    )
    fig.update_xaxes( tickangle = 45 )
    output = widgets.Output( )
    with output :
        fig.show( )
    
    # ---- 5. Create summary table -------------------------------------------
    def fmt_dot( n ) :
      return f"{n:,}".replace(',', '.')

    totals = pl.DataFrame( {
      'total_size' : [ df_agg[ 'total_size' ].sum( ) ],
      'job_count'  : [ df_agg[ 'job_count' ].sum( ) ],
      'os_count'   : [ df_agg[ 'os_count' ].sum( ) ]
    } ).with_columns(
      human_bytes( pl.col( 'total_size' ) ),
      pl.col( 'job_count' ).map_elements( lambda x : fmt_dot( x ) ),
      pl.col( 'os_count' ).map_elements( lambda x : fmt_dot( x ) )
    )

    df_agg = df_agg.with_columns(
      ( pl.col( 'job_count' ) / pl.col( 'os_count' ) ).alias( 'ratio' ),
      pl.col( 'job_count' ).map_elements( lambda x : fmt_dot( x ) ),
      pl.col( 'os_count' ).map_elements( lambda x : fmt_dot( x ) )
    )

    table_html = (
      "<style>"
      "table td, table th {text-align: center;}"
      "table td:first-child, table th:first-child {text-align: left;}"
      "</style><table style='border-collapse: collapse; width: 100%;'>"
    )
    th = 'th style="padding:8px;border:1px solid #ccc;"'
    table_html += (
      "<thead><tr !style='background:#f0f0f0;'>"
      f"<{th}>Class</th>"
      f"<{th}>Total Size ({totals['total_size'].item()})</th>"
      f"<{th}>Avg Size</th>"
      f"<{th}>Jobs ({totals['job_count'].item()})</th>"
      f"<{th}>OS ({totals['os_count'].item()})</th>"
      "</tr></thead><tbody>"
    )

    df_agg = df_agg.with_columns( 
      human_bytes( pl.col( 'total_size' ) ),
      human_bytes( pl.col( 'avg_size' ) )
    )

    td = 'td style="padding:6px;border:1px solid #ccc;"'
    for row in df_agg.iter_rows(named=True):
      table_html += (
        "<tr>"
        f"<{td}><strong>{row['cluster_label_kb']}</strong><br/><em>{row['cluster_label_st']}</em></td>"
        f"<{td}>{row['total_size']}</td>"
        f"<{td}>{row['avg_size']}</td>"
        f"<{td}>{row['job_count']}</td>"
        f"<{td}>{row['os_count']} ({str(round(row['ratio'],2)).replace('.', ',')})</td>"
        "</tr>"
      )
    table_html += "</tbody></table>"
    table_widget = widgets.HTML(table_html)

    head = widgets.HBox(
      [
        build_wordcloud( df ),
        widgets.HTML( "<div style='width:20px;'></div>" ),
        output
      ],
      layout = widgets.Layout( width = '100%' )
    )

    # ---- 6. Wrap into a VBox with title ------------------------------------
    tab_content = widgets.VBox(
      [
        widgets.HTML("<h3>Service Class Analysis</h3>"),
        head,
        widgets.HTML("<h4>Summary</h4>"),
        table_widget
      ],
      layout=widgets.Layout(padding="20px")
    )

    return tab_content
