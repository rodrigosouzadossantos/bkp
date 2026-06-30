#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: set tabstop=2 shiftwidth=2 softtabstop=2 noexpandtab:

import ipywidgets as widgets
from IPython.display import display
import plotly.graph_objects as go
import polars as pl
from plotly.subplots import make_subplots

from .service_class import build_service_class_tab
from .sankey import build_sankey_tab


# ===========================================================
# CARD CREATION
# ===========================================================
def create_card( title: str, value: str ) -> widgets.HTML:
  """Create a KPI card widget."""
  style = """
        padding: 20px;
        border-radius: 10px;
        background-color: #1f2937;
        color: white;
        width: 300px;
        text-align: center;
        box-shadow: 0 4px 10px rgba(0,0,0,0.3);
        font-family: Arial, sans-serif;
    """
  html = f"""
        <div style="{style}">
            <div style="font-size: 16px; opacity: 0.8;">{title}</div>
            <div style="font-size: 28px; font-weight: bold; margin-top: 10px;">
                {value}
            </div>
        </div>
    """
  return widgets.HTML( value = html )


def format_tb( value: float ) -> str:
  """Format bytes to TB (assuming value is in bytes)."""
  return "{} TB ({} TiB)".format(
      round( value / ( 1000 ** 5 ), 2 ),
      round( value / ( 1024 ** 5 ), 2 ) )


def create_cards_row( df: pl.DataFrame ) -> widgets.HBox:
  """Build the KPI card row."""

  from .easy_search import human_bytes, human_bytes_IEC

  from datetime import datetime
  from dateutil.relativedelta import relativedelta

  total_storage_tb = df[ "files_size" ].sum()

  months = 18
  last_months_storage = (
      df.filter(
          pl.col( 'files_oldest' )
          >= pl.lit( datetime.now() -
                     relativedelta( months = months ) ),
          pl.col( 'files_oldest' ).is_not_null() )
      .with_columns(
          pl.col( 'files_oldest' ).dt.date().alias(
              'day' ) ).group_by( 'day' ).agg( [
                  pl.col( 'files_size' ).sum(),
              ] ).select(
                  human_bytes(
                      pl.col( 'files_size' ).mean().alias(
                          'avg' ) ),
                  human_bytes_IEC(
                      pl.col( 'files_size' ).mean().alias(
                          'avg_IEC' ) ) ) )

  files_count = df.select(
    pl.col( 'files_count' )
      .sum( )
      .map_elements(
        lambda x :
          f"{x:,}".replace( ',', '.' )
      )
  )

  card_storage = create_card(
      "Total Storage", format_tb( total_storage_tb ) )
  card_ingestion = create_card(
      f'Ingestion Rate / Day ({months} months)',
      "{} ({})".format(
          last_months_storage[ 'avg' ].item(),
          last_months_storage[ 'avg_IEC' ].item() ) )
  card_files = create_card(
    'Files', files_count['files_count'].item( )
  )
  return widgets.VBox(
      [
          card_storage,
          # widgets.HTML( "<div style='width:20px;'></div>" ),
          card_ingestion,
          card_files
      ],
      layout = widgets.Layout(
          justify_content = "flex-start" ) )


# ===========================================================
# 
# ===========================================================

def build_bucket_summary( df ) :
  from .easy_search import human_bytes

  summary = (
    df.group_by( 'bucket' ).agg(
      pl.col( 'files_count' ).sum( ),
      pl.col( 'files_size' ).sum( ).alias( 'total_size' ),
      human_bytes( pl.col( 'files_size' ).sum( ).alias( 'human_size' ) )
    )
    .sort( by = 'files_count', descending = True )
    .with_columns(
      pl.col( 'files_count' ).map_elements(
        lambda x :
          f"{x:,}".replace( ',', '.' )
      )
    )
  )

  labels = summary[ 'bucket' ].to_list( )
  values = summary[ 'total_size' ].to_list( )
  human = summary[ 'human_size' ].to_list( )
  files = summary[ 'files_count' ].to_list( )
  
  fig = go.Figure( data = [
    go.Pie(
      labels = labels,
      values = values,
      hole = 0.55,
      textinfo = 'label+percent',
      # texttemplate = "%{label}<br>%{percent} (%{customdata})",
      texttemplate = "%{label}<br>%{percent} (%{customdata[0]} | %{customdata[1]})",
      customdata = list( zip( human, files ) ),
      hovertemplate = "<b>%{label}</b><br>"+
                    "Size: %{customdata[0][0]}<br>"+
                    "Files: %{customdata[0][1]}<br>"+
                    "Percent: %{percent}"+
                    "<extra></extra>"
    )
  ] )
  fig.update_layout(
    title="Bucket Storage Distribution",
    showlegend=False,
    legend_title="Bucket (Size)",
    margin=dict(l=20,r=20,t=40,b=20)
  )
  out=widgets.Output( )
  with out:
    fig.show( )
  return widgets.HBox( [ out ] )

# ===========================================================
# YEAR SLIDER
# ===========================================================
def create_year_slider(
    df: pl.DataFrame ) -> widgets.IntSlider:
  """Build the year selector slider dynamically from data."""
  df_bounds = (
      df.with_columns(
          pl.col( "files_oldest" ).alias( "date" ) ).select(
              [
                  pl.col( "date" ).dt.year().min().alias(
                      "min_year" ),
                  pl.col( "date" ).dt.year().max().alias(
                      "max_year" )
              ] ) )
  min_year = df_bounds[ "min_year" ][ 0 ]
  max_year = df_bounds[ "max_year" ][ 0 ]
  return widgets.IntSlider(
      value = max_year - 1,
      min = min_year,
      max = max_year,
      step = 1,
      description = "Year:",
      style = {
          "description_width": "70px"
      },
      layout = widgets.Layout( width = "400px" ) )


# ===========================================================
# PREPARE MONTHLY AGGREGATION
# ===========================================================
def compute_monthly( df: pl.DataFrame ):
  """Prepare monthly aggregated data per year."""
  df_parsed = df.with_columns( [
      pl.col( "files_oldest" ).alias( "date" ),
      pl.col( "files_oldest" ).dt.year().alias( "year" ),
      pl.col( "files_oldest" ).dt.month().alias( "month" )
  ] )
  years = sorted( df_parsed[ "year" ].unique().to_list() )
  monthly = (
      df_parsed.group_by( [ "year", "month" ] ).agg( [
          pl.col( "files_size" ).sum().alias(
              "total_size" ),
          pl.col( "files_count" ).sum().alias(
              "total_files" )
      ] ) )
  return years, monthly


# ===========================================================
# BUILD PLOT
# ===========================================================
def build_figure( years, monthly, slider_year,
                  df ) -> ( go.Figure, widgets.Output ):
  """Build the dual-axis time-series chart for all years."""

  def compute_global_ranges( df: pl.DataFrame ):
    # Convert once
    dfp = df.with_columns( [
        pl.col( "files_oldest" ).alias( "date" ),
        pl.col( "files_oldest" ).dt.year().alias( "year" ),
        pl.col( "files_oldest" ).dt.month().alias( "month" )
    ] )
    # Aggregate per month per year
    df_monthly = (
        dfp.group_by( [ "year", "month" ] ).agg( [
            pl.col( "files_size" ).sum().alias(
                "total_size" ),
            pl.col( "files_count" ).sum().alias(
                "total_files" )
        ] ) )
    # Compute global ranges
    size_min = df_monthly[ "total_size" ].min()
    size_max = df_monthly[ "total_size" ].max()
    files_min = df_monthly[ "total_files" ].min()
    files_max = df_monthly[ "total_files" ].max()
    return ( size_min, size_max, files_min, files_max )

  months_labels = [
      "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul",
      "Aug", "Sep", "Oct", "Nov", "Dec"
  ]

  size_min, size_max, files_min, files_max = compute_global_ranges(
      df )
  # add padding to look better
  size_min *= 0.95
  size_max *= 1.05
  files_min = max( 0, files_min * 0.95 )
  files_max *= 1.10

  fig = make_subplots( specs = [ [ {
      "secondary_y": True
  } ] ] )
  for yr in years:
    df_year = monthly.filter(
        pl.col( "year" ) == yr ).sort( "month" )
    size_vals = [ None ] * 12
    count_vals = [ None ] * 12
    for row in df_year.iter_rows( named = True ):
      idx = row[ "month" ] - 1
      size_vals[ idx ] = row[ "total_size" ]
      count_vals[ idx ] = row[ "total_files" ]
    visible = ( yr == slider_year.value )
    # BAR TRACE (right axis)
    fig.add_trace(
        go.Bar(
            x = months_labels,
            y = count_vals,
            name = f"{yr} File Count",
            marker_color = "#90caf9",
            opacity = 0.5,
            visible = visible,
            hovertemplate =
            "<b>%{x}</b><br>Files: %{y}<extra></extra>" ),
        secondary_y = True )
    # LINE TRACE (left axis)
    fig.add_trace(
        go.Scatter(
            x = months_labels,
            y = size_vals,
            mode = "lines+markers",
            line = dict( color = "#00bcd4", width = 3 ),
            name = f"{yr} Data Size",
            visible = visible,
            hovertemplate =
            "<b>%{x}</b><br>Size: %{y} TB<extra></extra>" ),
        secondary_y = False )
  # Layout
  fig.update_layout(
      height = 350,
      margin = dict( l = 40, r = 40, t = 40, b = 40 ),
      template = "plotly_white",
      barmode = "overlay",
      xaxis_title = "Months",
      legend_title = "Legend",
  )
  fig.update_yaxes(
      title = "Data Size",
      range = [ size_min, size_max ],
      showgrid = True,
      gridcolor = "#D0D0D0",
      gridwidth = 1,
      zeroline = False,
      secondary_y = False,
      layer = "above traces",
  )
  fig.update_yaxes(
      title = "File Count",
      range = [ files_min, files_max ],
      showgrid = True,
      gridcolor = "#FFD27F",
      gridwidth = 1,
      griddash = "dash",
      zeroline = False,
      secondary_y = True,
      layer = "below traces",
  )
  output = widgets.Output()
  with output:
    fig.show()
  return fig, output


# ===========================================================
# SLIDER CALLBACK
# ===========================================================
def attach_slider_callback( fig, slider_year, years,
                            output ):
  """Attach callbacks to the year slider for visibility toggling."""

  def on_slider_change( change ):
    selected = change[ "new" ]
    for i, yr in enumerate( years ):
      bar_index = i * 2
      line_index = i * 2 + 1
      visible = ( yr == selected )
      fig.data[ bar_index ].visible = visible
      fig.data[ line_index ].visible = visible
    with output:
      output.clear_output( wait = True )
      fig.show()

  slider_year.observe( on_slider_change, names = "value" )


# ===========================================================
#
# ===========================================================
def compute_monthly_by_bucket( df: pl.DataFrame ):
  """Aggregate files_size per bucket per month per year."""
  dfp = df.with_columns( [
      pl.col( "files_oldest" ).alias( "date" ),
      pl.col( "files_oldest" ).dt.year().alias( "year" ),
      pl.col( "files_oldest" ).dt.month().alias( "month" )
  ] )
  # Expect df["bucket"] to exist
  monthly = (
      dfp.group_by( [ "year", "month", "bucket" ] ).agg( [
          pl.col( "files_size" ).sum().alias( "total_size" )
      ] ) )
  return monthly


def compute_bucket_global_range( monthly: pl.DataFrame,
                                 column = "total_size" ):
  """Compute min/max GB for bucket chart (all years)."""
  # Convert TB → GB if needed (files_size may be TB or bytes, adjust as needed)
  max_val = monthly[ column ].max()
  min_val = monthly[ "total_size" ].min()
  # Add padding
  min_val = max( 0, min_val * 0.95 )
  max_val = max_val * 1.10
  return min_val, max_val


def build_bucket_figure( monthly_bucket, slider_year ):
  """Build second plot: multi-line chart grouped by bucket."""
  months_labels = [
      "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul",
      "Aug", "Sep", "Oct", "Nov", "Dec"
  ]
  # Unique buckets (6 or 7 typically)
  buckets = sorted(
      monthly_bucket[ "bucket" ].unique().to_list() )
  # Prepare figure
  fig = go.Figure()
  # Precompute global Y range
  min_val, max_val = compute_bucket_global_range(
      monthly_bucket )
  for bucket in buckets:
    # Filter bucket for all years
    df_bucket = monthly_bucket.filter(
        pl.col( "bucket" ) == bucket )
    # For slider: show only selected year
    df_year = df_bucket.filter(
        pl.col( "year" ) == slider_year.value )
    # Monthly array padded to 12 positions
    yvals = [ None ] * 12
    for row in df_year.iter_rows( named = True ):
      idx = row[ "month" ] - 1
      yvals[ idx ] = row[ "total_size" ]
    # Line for this bucket
    fig.add_trace(
        go.Scatter(
            x = months_labels,
            y = yvals,
            mode = "lines+markers",
            name = bucket,
            hovertemplate = "<b>%{x}</b><br>"
            f"Bucket: {bucket}<br>"
            "Size: %{y} GB<extra></extra>",
            visible = True  # all buckets visible
        ) )
  fig.update_layout(
      height = 350,
      margin = dict( l = 40, r = 40, t = 40, b = 40 ),
      template = "plotly_white",
      xaxis_title = "Months",
      yaxis_title = "Data Size",
      legend_title = "Bucket",
  )
  fig.update_yaxes(
      range = [ min_val, max_val ],
      showgrid = True,
      gridcolor = "#CCCCCC",
      gridwidth = 1 )
  output = widgets.Output()
  with output:
    fig.show()
  return fig, output, buckets


def attach_bucket_slider_callback( fig, slider_year,
                                   monthly_bucket, output ):
  """Update second plot when year changes."""
  months_labels = [
      "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul",
      "Aug", "Sep", "Oct", "Nov", "Dec"
  ]

  def on_change( change ):
    year = change[ "new" ]
    # Filter data for the year
    df_year = monthly_bucket.filter(
        pl.col( "year" ) == year )
    # Update traces one bucket at a time
    for i, bucket in enumerate(
        sorted( monthly_bucket[ "bucket" ].unique().to_list(
        ) ) ):
      # padded 12 months
      yvals = [ None ] * 12
      df_bucket = df_year.filter(
          pl.col( "bucket" ) == bucket )
      for row in df_bucket.iter_rows( named = True ):
        idx = row[ "month" ] - 1
        yvals[ idx ] = row[ "total_size" ]
      fig.data[ i ].y = yvals
    with output:
      output.clear_output( wait = True )
      fig.show()

  slider_year.observe( on_change, names = "value" )


def build_bucket_cumulative_figure( monthly_bucket,
                                    slider_year ):
  months_labels = [
      "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul",
      "Aug", "Sep", "Oct", "Nov", "Dec"
  ]
  buckets = sorted(
      monthly_bucket[ "bucket" ].unique().to_list() )
  monthly_bucket = monthly_bucket.filter(
      ( pl.col( "year" ) == slider_year.value ) )
  fig = go.Figure()
  min_val = monthly_bucket[ "total_size_cum" ].min()
  max_val = monthly_bucket[ "total_size_cum" ].max()
  min_val = min_val * 0.95
  max_val = max_val * 1.10
  # Gera ticks legíveis
  import numpy as np

  def human_bytes( num_bytes ):
    for unit in [ 'B', 'KB', 'MB', 'GB', 'TB', 'PB' ]:
      if abs( num_bytes ) < 1024.0:
        return f"{num_bytes:.2f} {unit}"
      num_bytes /= 1024.0
    return f"{num_bytes:.2f} PB"

  tickvals = np.linspace( min_val, max_val, num = 8 )
  ticktext = [ human_bytes( val ) for val in tickvals ]
  for bucket in buckets:
    df_bucket = monthly_bucket.filter(
        ( pl.col( "bucket" ) == bucket )
        & ( pl.col( "year" ) == slider_year.value ) )
    # Preenche os 12 meses do ano
    yvals = [ None ] * 12
    for row in df_bucket.iter_rows( named = True ):
      idx = row[ "month" ] - 1
      yvals[ idx ] = row[ "total_size_cum" ]
    fig.add_trace(
        go.Scatter(
            x = months_labels,
            y = yvals,
            mode = "lines+markers",
            name = bucket,
            hovertemplate = "<b>%{x}</b><br>"
            f"Bucket: {bucket}<br>"
            "Cumulative Size: %{y} <extra></extra>",
            visible = True ) )
  fig.update_layout(
      height = 350,
      margin = dict( l = 40, r = 40, t = 40, b = 40 ),
      template = "plotly_white",
      xaxis_title = "Months",
      yaxis_title = "Cumulative Data Size",
      legend_title = "Bucket" )
  fig.update_yaxes(
      range = [ min_val, max_val ],
      showgrid = True,
      gridcolor = "#CCCCCC",
      gridwidth = 1,
      tickvals = tickvals,
      ticktext = ticktext )
  output = widgets.Output()
  with output:
    fig.show()
  return fig, output, buckets


# ===========================================================
#
# ===========================================================
def make_tab( title: str, content ):
  """
    Build a tab page with a title and content widget.
    Content may be HTML, VBox, HBox, FigureWidget, etc.
    """
  if isinstance( content, str ):
    content = widgets.HTML( content )

  container = widgets.VBox(
      [ widgets.HTML( f"<h3>{title}</h3>" ), content ],
      layout = widgets.Layout( padding = "20px" ) )
  return container


def attach__bucket_slider_callback( fig, slider,
                                    monthly_bucket, output,
                                    plot_func ):

  def on_value_change( change ):
    with output:
      output.clear_output( wait = True )
      fig, _, _ = plot_func( monthly_bucket, slider )
      fig.show()

  slider.observe( on_value_change, names = "value" )


# ===========================================================
# MAIN DASHBOARD FUNCTION
# ===========================================================
def build_dashboard( df: pl.DataFrame ):
  """Build and display the complete dashboard."""
  cards_row = create_cards_row( df )
  summary = build_bucket_summary( df )

  head = widgets.HBox(
    [
      cards_row,
      widgets.HTML( "<div style='width:20px;'></div>" ),
      summary
    ],
    layout=widgets.Layout(width="100%")
  )

  slider_year = create_year_slider( df )
  slider_box = widgets.HBox( [ slider_year ],
                             layout = widgets.Layout(
                                 justify_content = "center",
                                 padding = "20px 0" ) )

  years, monthly = compute_monthly( df )

  fig, plot_output = build_figure( years, monthly,
                                   slider_year, df )
  attach_slider_callback( fig, slider_year, years,
                          plot_output )

  # ----- SECOND PLOT: BUCKET AGGREGATION -----
  monthly_bucket = compute_monthly_by_bucket( df )

  bucket_fig, bucket_output, _ = build_bucket_figure(
      monthly_bucket, slider_year )
  attach_bucket_slider_callback( bucket_fig, slider_year,
                                 monthly_bucket,
                                 bucket_output )

  monthly_bucket_cum = (
      df.with_columns( [
          pl.col( "files_oldest" ).dt.year().alias(
              "year" ),
          pl.col( "files_oldest" ).dt.month().alias(
              "month" )
      ] ).group_by( [ "bucket", "year", "month" ] ).agg( [
          pl.col( "files_size" ).sum().alias(
              "total_size" ),
          pl.col( "files_count" ).sum().alias(
              "total_files" )
      ] ).sort( [
          "bucket", "year", "month"
      ] ).with_columns( [
          pl.col( "total_size" ).cum_sum().over(
              "bucket" ).alias( "total_size_cum" ),
          pl.col( "total_files" ).cum_sum().over( "bucket" )
      ] ) )
  growth_fig, growth_output, _ = build_bucket_cumulative_figure(
      monthly_bucket_cum, slider_year )
  attach__bucket_slider_callback(
      growth_fig, slider_year, monthly_bucket_cum,
      growth_output, build_bucket_cumulative_figure )
  # Insert below the first plot
  overview = widgets.VBox( [
      # cards_row,
      # summary,
      head,
      slider_box,
      plot_output,  # first plot
      bucket_output,  # second plot
      growth_output
  ] )

  # overview = widgets.VBox([cards_row, slider_box, plot_output])

  tab_bucket = make_tab("Charts", "<p>More content here.</p>")
  tab_class = build_service_class_tab( df )

  tab_sankey = build_sankey_tab( df )

  tabs = widgets.Tab(
    children = [
      overview,
      tab_bucket,
      tab_class,
      tab_sankey
  ] )

  tabs.set_title( 0, "Overview" )
  tabs.set_title( 1, "Bucket" )
  tabs.set_title( 2, "Class" )
  tabs.set_title( 3, "Sankey" )

  display( tabs )
