#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: set tabstop=2 shiftwidth=2 softtabstop=2 noexpandtab:

import ipywidgets as widgets
from IPython.display import display
import plotly.graph_objects as go
from plotly.subplots import make_subplots


import numpy as np
from sklearn.cluster import AgglomerativeClustering
import polars as pl
from polars import DataFrame

from Levenshtein import distance as lev_distance


def get_classes( df ) :
    suits = df.select("class_norm").filter( pl.col( 'class_norm').is_not_null() ).unique( ).to_series( ).to_list( )
    suits = [s for s in suits if s is not None]
    dist_matrix = np.array([[lev_distance(a, b) for b in suits] for a in suits])
    
    # Clustering: defina n_clusters conforme desejado
    n_clusters = 80  # exemplo, ajuste conforme necessário
    clustering = AgglomerativeClustering(n_clusters=n_clusters, metric='precomputed', linkage='average')
    labels = clustering.fit_predict(dist_matrix)
    
    # Crie um dicionário suit_norm -> cluster
    suit_to_cluster = dict(zip(suits, labels))
    
    return (
        df.filter( pl.col( 'class_norm').is_not_null() )
            .with_columns(
              pl.col("class_norm").map_elements(
                    lambda x: suit_to_cluster.get(x, -1),
                    return_dtype=pl.Int32
                ).alias("class_cluster")
            ).select( [ 'class_norm', "class_cluster" ] )
            .group_by("class_norm")
            .agg( pl.len() ).sort( 'len', descending = True )
            .filter(
                pl.col( 'len' ) > 160
            ).select( 'class_norm' )
    )


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
    df = df.filter( pl.col( 'class_norm' ).cast(pl.String).is_in(
        get_classes( df )
            .to_series()
            .cast(pl.String)
            .implode()
    ) )
                                        
    df_agg = (
        df
        .group_by("class")
        .agg([
            pl.col("files_size").sum().alias("total_size"),
            pl.col("files_count").sum().alias("total_files"),
            pl.col("files_size").mean().alias("avg_size"),
            pl.col("os").n_unique().alias("os_count"),
            pl.len().alias("job_count")
        ])
        .sort("total_size", descending = True)
    )
    # ---- 3. Convert to Python lists for plotting ----------------------------
    classes = df_agg["class"].to_list()
    total_gb = [round(x, 2) for x in df_agg["total_size"].to_list()]          # Or convert to GB
    total_files = df_agg["total_files"].to_list()
    avg_size = df_agg["avg_size"].to_list()
    # ---- 4. Create a bar chart ---------------------------------------------
    fig = go.Figure()
    fig.add_bar(
        x=classes,
        y=total_gb,
        marker_color="#42a5f5",
        name="Total Size (GB)",
        hovertemplate="<b>%{x}</b><br>Total Size: %{y} GB<extra></extra>"
    )
    fig.update_layout(
        title="Data Volume by Service Class",
        xaxis_title="Service Class",
        yaxis_title="Size (GB)",
        height=350,
        template="plotly_white",
        margin=dict(l=40, r=40, t=40, b=40)
    )
    output = widgets.Output()
    with output:
        fig.show()
    
    # ---- 5. Create summary table -------------------------------------------
    totals = pl.DataFrame({
        "total_size": [df_agg["total_size"].sum()],
        "job_count": [df_agg["job_count"].sum()],
        "os_count": [df_agg["os_count"].sum()]
    }).with_columns(
        human_bytes(pl.col('total_size')),
    )

    table_html = "<table style='border-collapse: collapse; width: 100%;'>"
    table_html += (
        "<tr !style='background:#f0f0f0;'>"
        "<th style='padding:8px;border:1px solid #ccc;'>Class</th>"
        f"<th style='padding:8px;border:1px solid #ccc;'>Total Size ({totals['total_size'].item()})</th>"
        "<th style='padding:8px;border:1px solid #ccc;'>Avg Size</th>"
        f"<th style='padding:8px;border:1px solid #ccc;'>Jobs ({totals['job_count'].item()})</th>"
        f"<th style='padding:8px;border:1px solid #ccc;'>OS ({totals['os_count'].item()})</th>"
        "</tr>"
    )

    df_agg = df_agg.with_columns( 
        human_bytes( pl.col( 'total_size' ) ),
        human_bytes( pl.col( 'avg_size' ) )
    )

    for row in df_agg.iter_rows(named=True):
        table_html += (
            "<tr>"
            f"<td style='padding:6px;border:1px solid #ccc;'>{row['class']}</td>"
            f"<td style='padding:6px;border:1px solid #ccc;'>{row['total_size']}</td>"
            f"<td style='padding:6px;border:1px solid #ccc;'>{row['avg_size']}</td>"
            f"<td style='padding:6px;border:1px solid #ccc;'>{row['job_count']}</td>"
            f"<td style='padding:6px;border:1px solid #ccc;'>{row['os_count']}</td>"
            "</tr>"
        )
    table_html += "</table>"
    table_widget = widgets.HTML(table_html)
    # ---- 6. Wrap into a VBox with title ------------------------------------
    tab_content = widgets.VBox(
        [
            widgets.HTML("<h3>Service Class Analysis</h3>"),
            output,
            widgets.HTML("<h4>Summary</h4>"),
            table_widget
        ],
        layout=widgets.Layout(padding="20px")
    )
    return tab_content
