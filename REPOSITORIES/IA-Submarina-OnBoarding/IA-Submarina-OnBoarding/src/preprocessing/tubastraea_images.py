#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: set tabstop=2 shiftwidth=2 softtabstop=2 expandtab:


# ------------------------------------------------------------
# 1. Imports & Environment Configuration
# ------------------------------------------------------------
# This module loads all required dependencies used throughout the
# image‑analysis pipeline. It ensures that numerical processing,
# deep learning inference, clustering, and visualization tools
# are available when other modules run.
#
# Inputs:
#   - None
#
# Outputs:
#   - Global imports available to all modules
#
# This module supports:
#   - All downstream functionality
#
# Integration point in pipeline:
#   Place this module at the beginning of the pipeline.
#   It precedes every other module.
# ------------------------------------------------------------

import os
import sys
from pathlib import Path
import multiprocessing as mp
import json
import csv

import numpy as np
from PIL import Image, ExifTags

import torch
from torchvision import models, transforms

from sklearn.decomposition import PCA
from sklearn.cluster import KMeans
from sklearn.ensemble import IsolationForest
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.metrics import (
  silhouette_score,
  calinski_harabasz_score,
  davies_bouldin_score
)

import hdbscan

import matplotlib.pyplot as plt

from rich import print
from rich import pretty
from rich.console import Console
from rich.progress import (
  Progress,
  SpinnerColumn,
  BarColumn,
  TextColumn,
  TimeElapsedColumn
)
from rich.panel import Panel
from rich.table import Table



# ------------------------------------------------------------
# 0. Rich Console Auto-Configuration (Terminal × Jupyter)
# ------------------------------------------------------------
# This module automatically detects whether the code is running
# inside a true terminal (TTY) or inside a Jupyter environment
# (JupyterLab / Jupyter Notebook). Based on the environment,
# it configures the Rich console with the optimal settings.
#
# Behaviors:
#   - Terminal: default Rich console
#   - Jupyter: force_terminal=True + force_jupyter=True
#   - Non-interactive (piped/redirected): minimal mode
#
# Outputs:
#   - console : Rich Console() instance auto-configured
#
# Integration point:
#   Place this module before any logging, printing or progress
#   visualization that relies on Rich.
# ------------------------------------------------------------
pretty.install( )

def in_jupyter( ) :
    try:
        from IPython import get_ipython
        shell = get_ipython().__class__.__name__
        return shell in ( 'ZMQInteractiveShell', 'Shell' )
    except Exception:
        return False

def in_terminal():
    return sys.stdout.isatty( )

def create_auto_console( ) :
    if in_jupyter( ) :
        return Console(
            #force_terminal = True,
            force_jupyter = True,
            color_system = 'truecolor'
        )
    elif in_terminal( ) :
        return Console(
            force_terminal = True
        )
    else:
        return Console( force_terminal = False )

console = create_auto_console( )



# ------------------------------------------------------------
# 2. Compute Device Selection ( CPU/GPU )
# ------------------------------------------------------------
# This module determines whether CUDA GPU acceleration is available
# and configures a device object to be used by the embedding model.
#
# Inputs:
#   - Local hardware configuration
#
# Outputs:
#   - device : torch.device instance ( 'cuda' or 'cpu' )
#
# This module supports:
#   - Embedding extraction
#   - Performance optimization
#
# Integration point in pipeline:
#   Place this module after:
#     1. Imports & Environment Configuration
#   And before:
#     3. Image Metadata Extraction
# ------------------------------------------------------------

device = torch.device( 'cuda' if torch.cuda.is_available( ) else 'cpu' )
if device.type == "cuda":
    console.print( "[bold green]Using device: CUDA (GPU available)[/]" )
else:
    console.print( "[bold red]Using device: CPU — no GPU detected[/]" )



# ------------------------------------------------------------
# 3. Image Metadata Extraction
# ------------------------------------------------------------
# This module extracts key image metadata including geometry,
# pixel statistics, and EXIF tags when available.
#
# Inputs:
#   - path : filesystem path to an image
#
# Outputs:
#   - metadata dict containing structural + statistical properties
#
# This module supports:
#   - Reporting
#   - Image quality analysis
#   - Outlier and cluster interpretation
#
# Integration point in pipeline:
#   Place this module after:
#     2. Compute Device Selection
#   And before:
#     4. CNN Embedding Model
# ------------------------------------------------------------

def extract_metadata( path ) :
    img = Image.open( path )
    arr = np.array( img )
  
    data = {
        'filename': str( path ),
        'format': img.format,
        'mode': img.mode,
        'width': img.size[ 0 ],
        'height': img.size[ 1 ],
        'mean': float( arr.mean( ) ),
        'std': float( arr.std( ) ),
        'min': int( arr.min( ) ),
        'max': int( arr.max( ) )
    }
  
    exif_data = {}
    try:
        if hasattr( img, '_getexif' ) and img._getexif( ) :
            for t, v in img._getexif( ).items( ) :
                exif_data[ExifTags.TAGS.get( t, t )] = v
    except Exception:
        pass
  
    data[ 'exif' ] = exif_data
    return data



# ------------------------------------------------------------
# 4. CNN Embedding Model ( ResNet50 )
# ------------------------------------------------------------
# This module loads a pretrained ResNet50 model and prepares a
# function to extract numerical embeddings for each image.
# Embeddings are used as the feature representation for clustering,
# outlier detection, similarity search, and deduplication.
#
# Inputs:
#   - path : filesystem path to image
#
# Outputs:
#   - embedding : numpy array vector representing the image
#
# This module supports:
#   - Clustering
#   - Outlier detection
#   - Similarity search
#   - Dataset characterization
#
# Integration point in pipeline:
#   Place this module after:
#     3. Image Metadata Extraction
#   And before:
#     5. Image Discovery
# ------------------------------------------------------------

prep = transforms.Compose( [
    transforms.Resize( ( 224, 224 )),
    transforms.ToTensor( )
] )

model = models.resnet50( weights = 'IMAGENET1K_V2' )
model.to( device )
model.eval( )

def get_embedding( path ) :
    img = Image.open( path ).convert( 'RGB' )
    t = prep( img ).unsqueeze( 0 ).to( device )
    with torch.no_grad( ) :
        e = model( t ).cpu( ).numpy( ).flatten( )
    return e



# ------------------------------------------------------------
# 5. Image Discovery
# ------------------------------------------------------------
# This module scans a directory recursively and identifies all
# supported image files. Its output is the ordered list of files
# that undergo subsequent processing.
#
# Inputs:
#   - folder : root directory to search
#
# Outputs:
#   - paths : list of image paths found
#
# This module supports:
#   - Bulk processing
#   - Dataset ingestion
#
# Integration point in pipeline:
#   Place this module after:
#     4. CNN Embedding Model
#   And before:
#     6. PCA Dimensionality Reduction
# ------------------------------------------------------------

def list_images( folder ) :
    exts = ( '*.jpg', '*.jpeg', '*.png', '*.bmp', '*.tiff' )
    paths = []
    for ext in exts:
        paths.extend( Path( folder ).rglob( ext ))
    return [p for p in paths]



# ------------------------------------------------------------
# 6. PCA Dimensionality Reduction
# ------------------------------------------------------------
# This module reduces embedding dimensionality to a lower‑dimensional
# space, making clustering more stable and enabling visualization.
#
# Inputs:
#   - embeddings : numpy array ( N × D )
#
# Outputs:
#   - reduced : numpy array ( N × K )
#   - pca     : fitted PCA transformer
#
# This module supports:
#   - Clustering
#   - Visualization ( scatter plot )
#
# Integration point in pipeline:
#   Place this module after:
#     5. Image Discovery
#   And before:
#     7. Image Clustering
# ------------------------------------------------------------

def reduce_embeddings( embeddings, dims = 50 ) :
    pca = PCA( n_components = dims )
    return pca.fit_transform( embeddings ), pca



# ------------------------------------------------------------
# 7. Image Clustering ( KMeans )
# ------------------------------------------------------------
# This module assigns each image to a cluster based on its
# PCA‑reduced embedding. Clustering facilitates dataset grouping,
# pattern discovery, and exploration of visual structure.
#
# Inputs:
#   - reduced_embeddings : array ( N × K )
#   - n_clusters         : number of clusters
#
# Outputs:
#   - labels : array assigning cluster ID to each image
#   - model  : fitted KMeans instance
#
# This module supports:
#   - Dataset organization
#   - Visual inspection
#   - Content grouping
#
# Integration point in pipeline:
#   Place this module after:
#     6. PCA Dimensionality Reduction
#   And before:
#     8. Outlier Detection
# ------------------------------------------------------------

def cluster_images( reduced_embeddings, n_clusters = 5 ) :
    kmeans = KMeans( n_clusters = n_clusters )
    labels = kmeans.fit_predict( reduced_embeddings )
    return labels, kmeans



# ------------------------------------------------------------
# 7b. Image Clustering with HDBSCAN
# ------------------------------------------------------------
# This module performs density‑based clustering using HDBSCAN.
# Unlike KMeans, HDBSCAN does not require choosing the number
# of clusters beforehand. It automatically discovers dense
# regions in the embedding space and labels sparse points
# as noise ( -1 ).
#
# Inputs:
#   - reduced_embeddings : numpy array ( N × K )
#   - min_cluster_size   : minimum size required for a cluster
#
# Outputs:
#   - labels : array assigning cluster ID ( or -1 for noise )
#   - model  : fitted HDBSCAN instance
#
# This module supports:
#   - Automatic cluster count detection
#   - Detection of noise/outlier regions
#   - Non‑spherical cluster shapes
#
# Integration point in pipeline:
#   Place this module after:
#     7. Image Clustering ( KMeans )
#   And before:
#     8. Outlier Detection
# ------------------------------------------------------------

def cluster_images_hdbscan( reduced_embeddings, min_cluster_size = 10 ) :
    model = hdbscan.HDBSCAN(
        min_cluster_size = min_cluster_size,
        min_samples = None,
        metric = 'euclidean',
        cluster_selection_method = 'eom'
    )
    labels = model.fit_predict( reduced_embeddings )
    return labels, model



# ------------------------------------------------------------
# 8. Outlier Detection ( IsolationForest )
# ------------------------------------------------------------
# This module identifies images that diverge significantly from
# the dataset distribution. Such images are often indicators of
# rare events, anomalies, or potential failure cases for ML models.
#
# Inputs:
#   - embeddings : numpy array of image embeddings
#   - contamination : expected fraction of anomalies
#
# Outputs:
#   - preds : array of flags ( 1 = normal, -1 = outlier )
#   - model : fitted IsolationForest instance
#
# This module supports:
#   - Model QA
#   - Anomaly analysis
#   - Data cleaning
#
# Integration point in pipeline:
#   Place this module after:
#     7. Image Clustering
#   And before:
#     9. Similarity Search & Duplicate Detection
# ------------------------------------------------------------

def detect_outliers( embeddings, contamination = 0.05 ) :
    iso = IsolationForest( contamination = contamination )
    preds = iso.fit_predict( embeddings )
    return preds, iso



# ------------------------------------------------------------
# 9. Similarity Search & Duplicate Detection
# ------------------------------------------------------------
# This module provides functionality for detecting visually
# similar or near‑duplicate images based on cosine similarity
# computed from image embeddings.
#
# It is intended to be integrated into the full image‑analysis
# pipeline, after embeddings are generated. The functions below
# compute both near‑duplicate similarity and strong duplicates.
#
# Inputs:
#   - embeddings : numpy array ( N × D )
#   - paths      : list of image paths
#   - threshold  : similarity cutoff ( 0.90 typical )
#
# Outputs:
#   - list of tuples:
#       ( image_path_1, image_path_2, similarity_score )
#
# This module supports:
#   - Duplicate detection
#   - Similar‑image clustering
#   - Reverse‑image search
#   - Dataset cleanliness verification ( model QA )
#
# Integration point in pipeline:
#   Place this module after:
#     8. Outlier Detection
#   And before:
#     10. Visualization
# ------------------------------------------------------------

def find_similar_images( embeddings, paths, threshold = 0.90 ) :
    sim = cosine_similarity( embeddings )
    n = len( paths )
    pairs = []
  
    for i in range( n ) :
        for j in range( i + 1, n ) :
            if sim[i, j] >= threshold:
                pairs.append( ( str( paths[ i ] ), str( paths[ j ] ), float( sim[i, j] )) )
  
    return pairs

def find_duplicates( similar_pairs, strong_threshold = 0.98 ) :
    return [p for p in similar_pairs if p[ 2 ] >= strong_threshold]



# ------------------------------------------------------------
# 10. Visualization ( Cluster Plot )
# ------------------------------------------------------------
# This module generates a 2‑D scatter plot using the first two
# PCA components, coloring each point by its cluster assignment.
#
# Inputs:
#   - reduced : PCA‑reduced embeddings
#   - labels  : cluster IDs
#
# Outputs:
#   - clusters.png : saved visualization
#
# This module supports:
#   - Human validation of clustering
#   - Exploratory data analysis
#
# Integration point in pipeline:
#   Place this module after:
#     9. Similarity Search & Duplicate Detection
#   And before:
#     11. Report Saving
# ------------------------------------------------------------

def plot_clusters( reduced, labels ) :
    plt.scatter( reduced[:, 0], reduced[:, 1], c = labels, cmap = 'tab20' )
    plt.title( 'Image Clusters' )
    plt.xlabel( 'PCA 1' )
    plt.ylabel( 'PCA 2' )
    plt.savefig( 'clusters.png', dpi = 200 )
    plt.close( )



# ------------------------------------------------------------
# 10b. Overlay Visualization ( KMeans × HDBSCAN )
# ------------------------------------------------------------
# This module generates three scatter plots to visually compare
# the clustering behavior of KMeans and HDBSCAN. All plots use
# the first two PCA components for 2‑D visualization.
#
# Outputs generated:
#   - clusters_kmeans.png  : KMeans clustering visualization
#   - clusters_hdbscan.png : HDBSCAN clustering visualization
#   - clusters_overlay.png : combined overlay ( KMeans + HDBSCAN )
#
# Inputs:
#   - reduced_embeddings : PCA-reduced embeddings ( N × 2+ )
#   - kmeans_labels      : array with KMeans cluster IDs
#   - hdbscan_labels     : array with HDBSCAN cluster IDs
#
# Outputs:
#   - Three PNG plots saved to disk
#
# This module supports:
#   - Cluster comparison
#   - Visual debugging
#   - Outlier inspection ( via noise points )
#
# Integration point in pipeline:
#   Place this module after:
#     10. Visualization ( KMeans-only )
#   And before:
#     11. Report Saving
# ------------------------------------------------------------

def plot_cluster_comparison( reduced, kmeans_labels, hdbscan_labels ) :
    # ----- KMEANS -----
    plt.figure( figsize = ( 8, 6 ))
    plt.scatter(
        reduced[:, 0],
        reduced[:, 1],
        c = kmeans_labels,
        cmap = 'tab20',
        alpha = 0.8
    )
    plt.title( 'KMeans Clustering' )
    plt.xlabel( 'PCA 1' )
    plt.ylabel( 'PCA 2' )
    plt.savefig( 'clusters_kmeans.png', dpi = 200 )
    plt.close( )
    
    # ----- HDBSCAN -----
    plt.figure( figsize = ( 8, 6 ))
    cmap = plt.get_cmap( 'tab20' )
  
    # Noise ( -1 ) in black
    noise_mask = ( hdbscan_labels == -1 )
    cluster_mask = ~noise_mask
  
    plt.scatter(
        reduced[cluster_mask, 0],
        reduced[cluster_mask, 1],
        c = hdbscan_labels[ cluster_mask ],
        cmap = 'tab20',
        alpha = 0.8,
        label = 'HDBSCAN Clusters'
    )
  
    plt.scatter(
        reduced[noise_mask, 0],
        reduced[noise_mask, 1],
        c = 'black',
        s = 20,
        alpha = 0.6,
        label = 'Noise (-1)'
    )
  
    plt.title( 'HDBSCAN Clustering' )
    plt.xlabel( 'PCA 1' )
    plt.ylabel( 'PCA 2' )
    plt.legend( )
    plt.savefig( 'clusters_hdbscan.png', dpi = 200 )
    plt.close( )
  
    # ----- OVERLAY -----
    plt.figure( figsize = ( 8, 6 ))
  
    # KMeans ( circles )
    plt.scatter(
        reduced[:, 0],
        reduced[:, 1],
        c = kmeans_labels,
        cmap = 'tab20',
        alpha = 0.35,
        marker = 'o',
        label = 'KMeans'
    )
  
    # HDBSCAN ( crosses )
    plt.scatter(
        reduced[cluster_mask, 0],
        reduced[cluster_mask, 1],
        c = hdbscan_labels[ cluster_mask ],
        cmap = 'tab20',
        alpha = 0.8,
        marker = 'x',
        s = 50,
        label = 'HDBSCAN'
    )
  
    # Noise
    plt.scatter(
        reduced[noise_mask, 0],
        reduced[noise_mask, 1],
        c = 'black',
        s = 40,
        marker = 'D',
        label = 'Noise (-1)'
    )
  
    plt.title( 'Overlay Comparison — KMeans × HDBSCAN' )
    plt.xlabel( 'PCA 1' )
    plt.ylabel( 'PCA 2' )
    plt.legend( )
    plt.savefig( 'clusters_overlay.png', dpi = 200 )
    plt.close( )



# ------------------------------------------------------------
# 10c. Cluster Quality Metrics Panel ( KMeans × HDBSCAN )
# ------------------------------------------------------------
# This module computes quality metrics for both KMeans and
# HDBSCAN cluster assignments and displays them using a Rich
# Panel. Metrics include:
#
#   - Silhouette Score
#   - Davies–Bouldin Index
#   - Calinski–Harabasz Score
#
# HDBSCAN produces a noise cluster (-1), so metrics are computed
# only on non-noise points.
#
# Inputs:
#   - reduced : PCA-reduced embeddings
#   - kmeans_labels : array of cluster assignments ( KMeans )
#   - hdb_labels    : array of cluster assignments ( HDBSCAN )
#
# Outputs:
#   - Rich panel printed to console
#
# This module supports:
#   - Cluster comparison
#   - Pipeline performance evaluation
#
# Integration point in pipeline:
#   Place this module after:
#     10b. Overlay Visualization
#   And before:
#     11. Report Saving
# ------------------------------------------------------------

def show_cluster_metrics_panel( reduced, kmeans_labels, hdb_labels ) :
  
    # ---- KMEANS Metrics ----
    k_sil = silhouette_score( reduced, kmeans_labels )
    k_cal = calinski_harabasz_score( reduced, kmeans_labels )
    k_dav = davies_bouldin_score( reduced, kmeans_labels )
  
    # ---- HDBSCAN Metrics (remove noise) ----
    mask = hdb_labels != -1
    if mask.sum( ) > 1:
        h_sil = silhouette_score( reduced[ mask ], hdb_labels[ mask ] )
        h_cal = calinski_harabasz_score( reduced[ mask ], hdb_labels[ mask ] )
        h_dav = davies_bouldin_score( reduced[ mask ], hdb_labels[ mask ] )
    else:
        h_sil = h_cal = h_dav = float( 'nan' )
    
    panel = Panel.fit(
        f'[bold cyan]Cluster Quality Metrics[/]\n\n'
        f'[white]KMeans Silhouette:[/] [bold]{k_sil:.4f}[/]\n'
        f'[white]KMeans Calinski-Harabasz:[/] [bold]{k_cal:.2f}[/]\n'
        f'[white]KMeans Davies-Bouldin:[/] [bold]{k_dav:.4f}[/]\n\n'
        f'[white]HDBSCAN Silhouette:[/] [bold]{h_sil:.4f}[/]\n'
        f'[white]HDBSCAN Calinski-Harabasz:[/] [bold]{h_cal:.2f}[/]\n'
        f'[white]HDBSCAN Davies-Bouldin:[/] [bold]{h_dav:.4f}[/]\n',
        title = '[magenta]Cluster Quality Comparison[/]',
        border_style = 'cyan'
    )
  
    console.print(panel )



# ------------------------------------------------------------
# 10d. Cluster Association Heatmap ( KMeans × HDBSCAN )
# ------------------------------------------------------------
# This module generates a heatmap showing the cross-distribution
# between KMeans and HDBSCAN clusters. This helps identify how
# clusters from both algorithms align or disagree.
#
# - Rows: KMeans cluster IDs
# - Columns: HDBSCAN cluster IDs
# - Values: Number of images belonging to both clusters
#
# Inputs:
#   - kmeans_labels : array
#   - hdb_labels    : array
#
# Outputs:
#   - cluster_heatmap.png : saved heatmap
#
# This module supports:
#   - Cross-algorithm analysis
#   - Understanding cluster alignment
#
# Integration point in pipeline:
#   Place this module after:
#     10c. Cluster Quality Metrics Panel
#   And before:
#     11. Report Saving
# ------------------------------------------------------------

def plot_cluster_heatmap( kmeans_labels, hdb_labels ) :
  
    km_ids = sorted( set( kmeans_labels ))
    hdb_ids = sorted( set( hdb_labels ))
  
    matrix = np.zeros( (len( km_ids ), len( hdb_ids )), dtype = int )
  
    # fill matrix
    for km, hb in zip( kmeans_labels, hdb_labels ) :
        i = km_ids.index( km )
        j = hdb_ids.index( hb )
        matrix[i, j] += 1
  
    # plot heatmap
    plt.figure( figsize = ( 10, 7 ))
    plt.imshow( matrix, cmap = 'viridis' )
    plt.colorbar( label = 'Image Count' )
  
    plt.xticks( ticks = range( len( hdb_ids )), labels = hdb_ids )
    plt.yticks( ticks = range( len( km_ids )), labels = km_ids )
  
    plt.xlabel( 'HDBSCAN Clusters' )
    plt.ylabel( 'KMeans Clusters' )
    plt.title( 'Cluster Association Heatmap ( KMeans × HDBSCAN )' )
  
    plt.savefig( 'cluster_heatmap.png', dpi = 200 )
    plt.close( )



# ------------------------------------------------------------
# 10e. Automatic Clusterizer Evaluation ( KMeans × HDBSCAN )
# ------------------------------------------------------------
# This module automatically evaluates which clustering method
# (KMeans or HDBSCAN) performed better according to a series of
# quantitative and structural criteria:
#
#   - Silhouette Score (higher = better)
#   - Davies–Bouldin Index (lower = better)
#   - Calinski–Harabasz Score (higher = better)
#   - Number of clusters (penalizes KMeans if exaggerated)
#   - Noise points detected by HDBSCAN
#   - Cluster alignment between methods (heatmap diagonal strength)
#
# The goal is to identify which algorithm describes the dataset
# structure more accurately.
#
# Inputs:
#   - reduced embeddings (PCA)
#   - kmeans_labels
#   - hdb_labels
#
# Outputs:
#   - Rich panel identifying the best algorithm
#   - Dictionary with scores for external reporting
#
# This module supports:
#   - Algorithm selection
#   - Model QA
#   - Automated pipeline reporting
#
# Integration point in pipeline:
#   Place this module after:
#     10d. Cluster Association Heatmap
#   And before:
#     11. Report Saving
# ------------------------------------------------------------

from rich.panel import Panel
from rich import print

def evaluate_clusterizers( reduced, kmeans_labels, hdb_labels ) :
  
    # === Helper metrics (already calculated before) ===
    # KMeans metrics
    k_sil = silhouette_score( reduced, kmeans_labels )
    k_cal = calinski_harabasz_score( reduced, kmeans_labels )
    k_dav = davies_bouldin_score( reduced, kmeans_labels )
    
    # HDBSCAN metrics (excluding noise)
    mask = hdb_labels != -1
    if mask.sum( ) > 1:
        h_sil = silhouette_score( reduced[ mask ], hdb_labels[ mask ] )
        h_cal = calinski_harabasz_score( reduced[ mask ], hdb_labels[ mask ] )
        h_dav = davies_bouldin_score( reduced[ mask ], hdb_labels[ mask ] )
    else:
        h_sil = h_cal = h_dav = float( "nan" )
    
    # === Structural metrics ===
    k_clusters = len( set( kmeans_labels ))
    h_clusters = len( set( hdb_labels )) - ( 1 if -1 in set( hdb_labels ) else 0 )
    h_noise = sum( l == -1 for l in hdb_labels )
  
    # Heatmap diagonal strength
    km_ids = sorted( set( kmeans_labels ))
    hdb_ids = sorted( set( hdb_labels ))
  
    assoc = np.zeros( (len( km_ids ), len( hdb_ids )), dtype = int )
    for km, hb in zip( kmeans_labels, hdb_labels ) :
        assoc[km_ids.index( km ), hdb_ids.index( hb )] += 1
  
    diagonal_strength = sum(
        assoc[i, j]
        for i, km_id in enumerate( km_ids )
        for j, hb_id in enumerate( hdb_ids )
        if km_id == hb_id
    )
    diagonal_strength_ratio = diagonal_strength / len( kmeans_labels )
  
    # === Scoring ===
    k_score = 0
    h_score = 0
  
    # Silhouette
    if k_sil > h_sil: k_score += 1
    else: h_score += 1
  
    # Calinski–Harabasz
    if k_cal > h_cal: k_score += 1
    else: h_score += 1
  
    # Davies–Bouldin (lower is better )
    if k_dav < h_dav: k_score += 1
    else: h_score += 1
  
    # Noise (penaliza HDBSCAN se detectar noise demais )
    if h_noise > len( reduced ) * 0.2:
        k_score += 1
    else:
        h_score += 1
  
    # Heatmap diagonal (alinhamento)
    if diagonal_strength_ratio > 0.35:
        k_score += 1
    else:
        h_score += 1
  
    # === Final decision ===
    if k_score > h_score:
        winner = "KMeans"
    elif h_score > k_score:
        winner = "HDBSCAN"
    else:
        winner = "Tie"
  
    # Panel output
    panel = Panel.fit(
        f"[bold cyan]Cluster Algorithm Evaluation[/]\n\n"
        f"KMeans score: [bold]{k_score}[/]\n"
        f"HDBSCAN score: [bold]{h_score}[/]\n\n"
        f"[white]Winner:[/] [bold magenta]{winner}[/]\n",
        title = "[green]Best Clusterizer[/]",
        border_style = "bright_blue"
    )
    console.print( panel )
  
    return {
        "winner": winner,
        "kmeans_score": k_score,
        "hdbscan_score": h_score,
        "kmeans_clusters": k_clusters,
        "hdbscan_clusters": h_clusters,
        "hdbscan_noise": h_noise,
        "diagonal_strength_ratio": diagonal_strength_ratio,
    }



# ------------------------------------------------------------
# 11. Report Saving (CSV + JSON)
# ------------------------------------------------------------
# This module stores metadata, similarity results, and duplicates
# in human‑readable formats for later analysis and auditing.
#
# Inputs:
#   - metadata  : list of dicts
#   - similar   : list of similar image pairs
#   - duplicates: list of duplicate image pairs
#
# Outputs:
#   - image_summary.csv
#   - image_metadata.json
#   - similar_images.json
#   - duplicate_images.json
#
# This module supports:
#   - Documentation
#   - QA review
#   - Downstream processes
#
# Integration point in pipeline:
#   Place this module after:
#     10. Visualization
#   And before:
#     12. Main Pipeline
# ------------------------------------------------------------

def make_json_safe( obj ) :
  if isinstance( obj, np.generic ) :
    return obj.item( )
  return obj

def save_reports( metadata, similar, duplicates ) :
  keys = sorted( {k for m in metadata for k in m if k != 'exif'} )

  with open( 'image_summary.csv', 'w', newline = '' ) as f:
    writer = csv.writer( f )
    writer.writerow( keys )
    for m in metadata:
      writer.writerow( [make_json_safe( m.get( k, '' )) for k in keys] )

  with open( 'image_metadata.json', 'w' ) as f:
    safe_metadata = [
      {k: make_json_safe( v ) for k, v in m.items( )}
        for m in metadata
    ]
    json.dump( safe_metadata, f, indent = 2 )

  with open( 'similar_images.json', 'w' ) as f:
    json.dump( similar, f, indent = 2 )

  with open( 'duplicate_images.json', 'w' ) as f:
    json.dump( duplicates, f, indent = 2 )



# ------------------------------------------------------------
# 
# ------------------------------------------------------------

def process_single_image( path ) :
    meta = extract_metadata( path )
    emb = get_embedding( path )  # GPU-safe: executed serially if CUDA is used
    return meta, emb

def process_images_parallel( paths ) :
    if device.type == 'cuda':
        console.log( '[yellow]GPU detected → running serial embedding extraction (CUDA-safe).[/]' )
        metadata = []
        embeddings = []
        with Progress(
            SpinnerColumn( ),
            TextColumn( '[progress.description]{task.description}' ),
            BarColumn( ),
            TimeElapsedColumn( ),
            console = console
        ) as progress:
            task = progress.add_task( 'Processing images...', total = len( paths ))
            for p in paths:
                m, e = process_single_image( p )
                metadata.append( m )
                embeddings.append( e )
                progress.update( task, advance = 1 )
        return metadata, embeddings
  
    console.log( '[cyan]CPU detected → running parallel multiprocessing.[/]' )
    with Progress(
        SpinnerColumn( ),
        TextColumn( '[progress.description]{task.description}' ),
        BarColumn( ),
        TimeElapsedColumn( ),
        console = console
    ) as progress:
        task = progress.add_task( 'Processing images...', total = len( paths ))
      
        # Custom wrapper so progress advances per item
        def wrapper( path ) :
            meta, emb = process_single_image( path )
            progress.update( task, advance = 1 )
            return meta, emb
      
        with mp.Pool( mp.cpu_count( ) ) as pool:
            results = pool.map( wrapper, paths )
  
    metadata = [m for m, _ in results]
    embeddings = [e for _, e in results]
    return metadata, embeddings



# ------------------------------------------------------------
# 12. Main Pipeline Controller
# ------------------------------------------------------------
# This module orchestrates all steps of the processing pipeline.
# It loads images, computes metadata, extracts embeddings,
# reduces dimensionality, clusters, detects outliers, finds
# similar images, and finally generates reports and plots.
#
# Inputs:
#   - folder : root directory containing images
#
# Outputs:
#   - Full set of files written to disk:
#       summary CSV, metadata JSON, duplicate list, cluster plot
#
# This module supports:
#   - End‑to‑end automation
#
# Integration point in pipeline:
#   Place this module after:
#     11. Report Saving
#   And before:
#     13. Entry Point
# ------------------------------------------------------------

def analyze_images( folder, clusters = 5 ) :

    global GLOBAL_DATASET_ROOT
    GLOBAL_DATASET_ROOT = Path( folder )
  
    console.log( '[bold cyan]Scanning for images...[/]' )
    paths = list_images( folder )
    console.log( f'[green]Found {len(paths )} images.[/]' )
  
    console.log( '[bold cyan]Processing images (parallel or serial )...[/]' )
    metadata, embeddings = process_images_parallel( paths )
    embeddings = np.array( embeddings )
  
    console.log( '[bold cyan]Reducing dimensions with PCA...[/]' )
    reduced, pca = reduce_embeddings( embeddings )
  
    console.log( '[bold cyan]Clustering images...[/]' )
    labels, km = cluster_images( reduced, clusters )
    for m, l in zip( metadata, labels ) :
      m[ 'cluster' ] = int( l )

    console.log( '[bold cyan]Clustering with HDBSCAN...[/]' )
    hdb_labels, hdb_model = cluster_images_hdbscan( reduced )
    for m, lab in zip( metadata, hdb_labels ) :
      m[ 'cluster_hdbscan' ] = int( lab )
  
    console.log( '[bold cyan]Detecting outliers...[/]' )
    outliers, iso = detect_outliers( embeddings )
    for m, o in zip( metadata, outliers ) :
        m[ 'outlier' ] = bool( o == -1 )
  
    console.log( '[bold cyan]Computing image similarities...[/]' )
    similar = find_similar_images( embeddings, paths )
    duplicates = find_duplicates( similar )
  
    console.log( '[bold cyan]Saving reports...[/]' )
    save_reports( metadata, similar, duplicates )
  
    console.log( '[bold cyan]Generating visualization...[/]' )
    plot_clusters( reduced, labels )

    console.log( '[bold cyan]Generating overlay plots (KMeans × HDBSCAN)...[/]' )
    plot_cluster_comparison( reduced, labels, hdb_labels )

    console.log( "[bold cyan]Computing cluster quality metrics...[/]" )
    show_cluster_metrics_panel( reduced, labels, hdb_labels )

    console.log( "[bold cyan]Generating cluster association heatmap...[/]" )
    plot_cluster_heatmap( labels, hdb_labels )

    console.log( "[bold cyan]Evaluating clusterizers automatically...[/]" )
    cluster_eval = evaluate_clusterizers( reduced, labels, hdb_labels )

    console.log( "[bold cyan]Generating HTML report...[/]" )
    generate_html_report(
      metadata = metadata,
      similar = similar,
      duplicates = duplicates,
      eval_results = cluster_eval,
      kmeans_labels = labels,
      hdb_labels = hdb_labels
    )

    show_duplicate_pairs( duplicates, max_pairs = 10 )
    show_duplicates_grid( duplicates )
  
    console.log( '[bold green]DONE![/]' )

    show_final_panel(
      total_images = len( paths ),
      total_clusters = len( set( labels )),
      outlier_count = sum( m[ 'outlier' ] for m in metadata ),
      similar_count = len( similar ),
      duplicates_count = len( duplicates )
    )

    show_cluster_table( metadata )
    show_hdbscan_table( metadata )
    show_comparison_panel( labels, hdb_labels )



def show_final_panel(
    total_images,
    total_clusters,
    outlier_count,
    similar_count,
    duplicates_count
) :
    panel = Panel.fit(
        f'[bold cyan]Final Pipeline Summary[/]\n\n'
        f'[white]Images processed:[/] [bold]{total_images}[/]\n'
        f'[white]Clusters:[/] [bold]{total_clusters}[/]\n'
        f'[white]Outliers detected:[/] [bold]{outlier_count}[/]\n'
        f'[white]Similar pairs:[/] [bold]{similar_count}[/]\n'
        f'[white]Duplicate pairs:[/] [bold]{duplicates_count}[/]\n',
        title = '[green]Pipeline Completed[/]',
        border_style = 'bright_blue'
    )
    console.print( panel )

def show_cluster_table( metadata ) :
    table = Table(
        title = 'Cluster Summary',
        show_lines = True,
        header_style = 'bold cyan'
    )
  
    table.add_column( 'Cluster ID', justify = 'center' )
    table.add_column( 'Count', justify = 'center' )
    table.add_column( 'Outliers', justify = 'center' )
    table.add_column( 'Outlier %', justify = 'center' )
  
    # aggregate info
    clusters = {}
    for m in metadata:
        cid = m[ 'cluster' ]
        clusters.setdefault( cid, {'count': 0, 'outliers': 0} )
        clusters[ cid]['count' ] += 1
        if m[ 'outlier' ]:
            clusters[ cid]['outliers' ] += 1
  
    # populate table
    for cid, stats in sorted( clusters.items( ) ) :
        count = stats[ 'count' ]
        outliers = stats[ 'outliers' ]
        pct = ( outliers / count ) * 100 if count > 0 else 0
        table.add_row(
            str( cid ),
            str( count ),
            str( outliers ),
            f'{pct:.1f}%'
        )
  
    console.print( table )


def show_hdbscan_table( metadata ) :
    table = Table(
        title = 'HDBSCAN Cluster Summary',
        show_lines = True,
        header_style = 'bold magenta'
    )
  
    table.add_column( 'Cluster ID', justify = 'center' )
    table.add_column( 'Count', justify = 'center' )
  
    clusters = {}
    for m in metadata:
        cid = m[ 'cluster_hdbscan' ]
        clusters.setdefault( cid, 0 )
        clusters[ cid ] += 1
  
    for cid, count in sorted( clusters.items( ) ) :
        table.add_row( str( cid ), str( count ))
  
    console.print( table )


def show_comparison_panel( kmeans_labels, hdb_labels ) :
    panel = Panel.fit(
        f'[bold cyan]Cluster Comparison[/]\n\n'
        f'[white]KMeans clusters:[/] [bold]{len(set(kmeans_labels))}[/]\n'
        f'[white]HDBSCAN clusters:[/] [bold]{len(set(hdb_labels))}[/]\n'
        f'[white]HDBSCAN noise points:[/] [bold]{sum(l == -1 for l in hdb_labels)}[/]\n',
        title = '[magenta]KMeans vs HDBSCAN[/]',
        border_style = 'magenta'
    )
    console.print( panel )



# ------------------------------------------------------------
# 12b. HTML Report Generator (Dataset & Clustering Analysis)
# ------------------------------------------------------------
# This module generates a complete HTML report summarizing:
#
#   - Basic dataset statistics
#   - Cluster results (KMeans & HDBSCAN)
#   - Outlier counts
#   - Similar and duplicate image statistics
#   - Cluster quality metrics
#   - Automatic clusterizer evaluation
#   - Heatmaps and cluster visualizations
#
# The report is exported as `report.html`.
#
# Inputs:
#   - metadata           : list of image metadata
#   - similar            : list of pairs (similar images)
#   - duplicates         : list of duplicate pairs
#   - eval_results       : dict returned from evaluate_clusterizers( )
#   - kmeans_labels      : KMeans cluster assignments
#   - hdb_labels         : HDBSCAN cluster assignments
#
# Outputs:
#   - report.html
#
# This module supports:
#   - Documentation
#   - Audit reports
#   - Sharing analysis results
#
# Integration point in pipeline:
#   Place this module after:
#     10e. Automatic Clusterizer Evaluation
#   And before:
#     (current) Report Saving
# ------------------------------------------------------------

def generate_html_report(
    metadata,
    similar,
    duplicates,
    eval_results,
    kmeans_labels,
    hdb_labels
) :
  
    total_images = len( metadata )
    k_clusters = len( set( kmeans_labels ))
    h_clusters = len( set( hdb_labels )) - ( 1 if -1 in set( hdb_labels ) else 0 )
    noise_points = sum( l == -1 for l in hdb_labels )
  
    # ---- CSS styling ----
    css = """
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 30px;
            background-color: #f7f7f7;
        }
        h1, h2, h3 {
            color: #003366;
        }
        .section {
            background: white;
            padding: 20px;
            margin-bottom: 25px;
            border-radius: 8px;
            border: 1px solid #ddd;
        }
        .stats-table, .cluster-table {
            border-collapse: collapse;
            width: 100%;
            margin-top: 10px;
        }
        .stats-table th, .stats-table td,
        .cluster-table th, .cluster-table td {
            border: 1px solid #ccc;
            padding: 8px 12px;
        }
        .stats-table th {
            background-color: #004080;
            color: white;
        }
        .cluster-table th {
            background-color: #660066;
            color: white;
        }
        img {
            border-radius: 8px;
            margin: 10px 0;
            border: 1px solid #ccc;
        }
    </style>
    """
    # ---- HTML structure ----
    html = f"""
    <html>
    <head>
        <title>Image Dataset Analysis Report</title>
        {css}
    </head>
    <body>
    <h1>Image Dataset Analysis Report</h1>
    <div class="section">
        <h2>1. Dataset Summary</h2>
        <table class="stats-table">
            <tr><th>Total Images</th><td>{total_images}</td></tr>
            <tr><th>Similar Pairs</th><td>{len(similar)}</td></tr>
            <tr><th>Duplicate Pairs</th><td>{len(duplicates)}</td></tr>
            <tr><th>KMeans Clusters</th><td>{k_clusters}</td></tr>
            <tr><th>HDBSCAN Clusters</th><td>{h_clusters}</td></tr>
            <tr><th>HDBSCAN Noise Points</th><td>{noise_points}</td></tr>
        </table>
    </div>
    <div class="section">
        <h2>2. Cluster Visualizations</h2>
        <h3>KMeans</h3>
        <img src="clusters_kmeans.png" width="500">
      <h3>HDBSCAN</h3>
        <img src="clusters_hdbscan.png" width="500">
      <h3>Overlay</h3>
        <img src="clusters_overlay.png" width="500">
      <h3>KMeans × HDBSCAN Heatmap</h3>
        <img src="cluster_heatmap.png" width="500">
    </div>
    <div class="section">
        <h2>3. Clusterizer Evaluation</h2>
        <table class="cluster-table">
            <tr><th>Metric</th><th>Value</th></tr>
            <tr><td>KMeans Score</td><td>{eval_results["kmeans_score"]}</td></tr>
            <tr><td>HDBSCAN Score</td><td>{eval_results["hdbscan_score"]}</td></tr>
            <tr><td>Winner</td><td>{eval_results["winner"]}</td></tr>
            <tr><td>Noise Ratio</td><td>{eval_results["hdbscan_noise"]}</td></tr>
            <tr><td>Alignment</td><td>{eval_results["diagonal_strength_ratio"]:.3f}</td></tr>
        </table>
    </div>
    <div class="section">
        <h2>4. Similarity & Deduplication Summary</h2>
        <p>Similar image pairs detected: <b>{len(similar)}</b></p>
        <p>Duplicate pairs detected: <b>{len(duplicates)}</b></p>
    </div>
    <div class="section">
        <h2>5. Notes</h2>
        <p>This analysis was automatically generated by the image
        preprocessing pipeline using PCA, ResNet embeddings,
        KMeans, HDBSCAN, cosine similarity, cluster evaluation
        metrics, and Rich visual reporting.</p>
    </div>
    </body>
    </html>
    """
  
    with open( "report.html", "w") as f:
        f.write( html)



# ------------------------------------------------------------
# X. Duplicate Image Polygon Viewer (Auto Root Path)
# ------------------------------------------------------------
# This module displays duplicate image pairs with YOLO polygon
# annotations drawn on top. It automatically uses the dataset
# path provided to analyze_images(), stored in the global
# variable GLOBAL_DATASET_ROOT.
#
# Expected dataset structure relative to GLOBAL_DATASET_ROOT:
#   images/train/*.jpg
#   images/test/*.jpg
#   labels/train/*.txt
#   labels/test/*.txt
#
# For each duplicate pair:
#   - Detect if image is in train/ or test/
#   - Load corresponding .txt file
#   - Draw all polygons on the image
#   - Display the two annotated images side-by-side
#
# Inputs:
#   - duplicate_pairs : list of tuples (path1, path2, similarity)
#   - max_pairs       : optional limit for visualization
#
# Outputs:
#   - Inline visualization of annotated duplicate image pairs
#
# Integration point:
#   Place this after duplicate detection, inside analyze_images()
# ------------------------------------------------------------

import cv2


# -------- Utility: short path for display --------

def shortname( path ) :
    p = Path( path )
    return f"{p.parent.name}/{p.name}"


# -------- Utility: draw a single polygon --------

def draw_polygon_on_image( img, line ) :
    console.log( f"[blue]No label found for: draw_polygon_on_image[/]" )
    parts = line.strip( ).split( )
    if len( parts ) < 3:
        return img
    
    coords = list( map( float, parts[ 1 : ] ) )
    h, w = img.shape[ : 2 ]
    points = [ ]
  
    for i in range( 0, len( coords ), 2 ) :
        x = int( coords[ i ] * w )
        y = int( coords[ i + 1 ] * h )
        points.append( [ x, y ] )
  
    pts = np.array( points, dtype = np.int32 )
    cv2.polylines( img, [ pts ], isClosed = True, color = ( 0,255,0 ), thickness = 2 )
    return img


# -------- Load image + draw its polygons based on GLOBAL_DATASET_ROOT --------

def annotate_image_with_polygons( image_path ) :
    """
    Given an image full path (original from duplicates list),
    find its YOLO label inside GLOBAL_DATASET_ROOT and draw polygons.
    """
  
    p = Path( image_path )
    img = cv2.imread( str( p ) )
    if img is None:
        return None
  
    # Determine if image is train/test under GLOBAL_DATASET_ROOT
    # Example: GLOBAL/images/train/<file.jpg>
    # Extract 'train' or 'test' from the image path
    # by checking whether its name exists under each split.
    img_name = p.name
  
    train_img = GLOBAL_DATASET_ROOT / "images" / "train" / img_name
    test_img  = GLOBAL_DATASET_ROOT / "images" / "test"  / img_name

    console.log( train_img )
    console.log( test_img )
  
    if train_img.exists( ) :
        split = "train"
    elif test_img.exists( ) :
        split = "test"
    else :
        console.log( f"[yellow]Image not found in train or test: {img_name}[/]" )
        return img
  
    # Label path
    label_path = GLOBAL_DATASET_ROOT / "labels" / split / (p.stem + ".txt" )
  
    if label_path.exists( ) :
        with open( label_path, 'r' ) as f :
            for line in f :
                img = draw_polygon_on_image( img, line )
    else:
        console.log( f"[yellow]No label found for: {img_name}[/]" )
  
    return img


# -------- Main function: display duplicate pairs with polygons --------

def show_duplicate_pairs( duplicate_pairs, max_pairs = None ) :
  
    shown = 0
  
    for p1, p2, sim in duplicate_pairs:
      
        if max_pairs and shown >= max_pairs:
            break
      
        imgA = annotate_image_with_polygons( p1 )
        imgB = annotate_image_with_polygons( p2 )
      
        if imgA is None or imgB is None:
            continue
      
        imgA = cv2.cvtColor( imgA, cv2.COLOR_BGR2RGB )
        imgB = cv2.cvtColor( imgB, cv2.COLOR_BGR2RGB )
      
        shown += 1
      
        fig, ax = plt.subplots( 1, 2, figsize=(12, 6 ) )
        fig.suptitle( f"Duplicate Pair {shown} — similarity={sim:.4f}", fontsize=14)
      
        # Left image
        ax[ 0 ].imshow( imgA )
        ax[ 0 ].set_title( f"A\n{shortname(p1)}" )
        ax[ 0 ].axis( 'off' )
      
        # Right image
        ax[ 1 ].imshow( imgB )
        ax[ 1 ].set_title( f"B\n{shortname(p2)}" )
        ax[ 1 ].axis( 'off' )
      
        plt.show( )
  
    console.log( f"[green]Displayed {shown} annotated duplicate pairs.[/]" )



def __show_duplicate_pairs(duplicate_pairs, max_pairs=None):
    shown = 0
    for i, (p1, p2, score) in enumerate(duplicate_pairs):
        name1 = Path(p1).name
        name2 = Path(p2).name
      
        # Skip duplicates with same filename
        if name1 == name2:
            continue
      
        shown += 1
        if max_pairs and shown > max_pairs:
            break
      
        fig, axes = plt.subplots(1, 2, figsize=(10, 5))
        fig.suptitle(
            f"Duplicate Pair {shown} — similarity={score:.4f}",
            fontsize=14
        )
      
        # Left image
        axes[0].imshow(Image.open(p1))
        axes[0].set_title(
            f"Image A\n{shortname(p1)}",
            fontsize=10
        )
        axes[0].axis("off")
      
        # Right image
        axes[1].imshow(Image.open(p2))
        axes[1].set_title(
            f"Image B\n{shortname(p2)}",
            fontsize = 10
        )
        axes[1].axis("off")
      
        plt.show()
  
    console.log(f"[green]Displayed {shown} unique-name duplicate pairs.[/]")



# ------------------------------------------------------------
# Xb. Duplicate Image Grid Viewer (Thumbnails)
# ------------------------------------------------------------
# This module provides a grid visualization of all duplicate
# images detected by the similarity engine. Each duplicate pair
# contributes two thumbnails to the grid.
#
# Inputs:
#   - duplicate_pairs : list of tuples
#       (image_path_1, image_path_2, similarity_score)
#   - thumb_size      : output size of thumbnails
#   - cols            : number of columns in the grid
#
# Outputs:
#   - Inline grid visualization of all duplicates
#
# This module supports:
#   - Rapid scanning of redundancy inside datasets
#   - Visual quality assessment
#   - Dataset curation and cleaning workflows
#
# Integration point in pipeline:
#   Place this module after:
#     X. Duplicate Image Pair Viewer
# ------------------------------------------------------------

def show_duplicates_grid( duplicate_pairs, thumb_size = ( 128,128 ), cols = 6 ) :
    images = [ ]
    for p1, p2, score in duplicate_pairs:
        images.append( (p1, score ) )
        images.append( (p2, score ) )
  
    rows = ( len( images ) + cols - 1 ) // cols
    fig = plt.figure( figsize = ( 3 * cols, 3 * rows ) )
  
    for i, ( path, score ) in enumerate( images ) :
        img = Image.open( path ).resize( thumb_size )
        ax = fig.add_subplot( rows, cols, i + 1 )
        ax.imshow( img )
        ax.set_title( f"{score:.2f}", fontsize = 8 )
        ax.axis( "off" )
  
    plt.tight_layout( )
    plt.show( )



# ------------------------------------------------------------
# X. YOLO Polygon Drawer for Full Dataset (Train/Test)
# ------------------------------------------------------------
# This module scans the dataset directory structure and draws
# all YOLO polygon annotations on their corresponding images.
#
# Expected structure:
#   <root>/images/train/*.jpg
#   <root>/images/test/*.jpg
#   <root>/labels/train/*.txt
#   <root>/labels/test/*.txt
#
# Annotation format inside each .txt file:
#   <class_id> x1 y1 x2 y2 ... xn yn
# Where:
#   - Coordinates are normalized (0–1)
#   - Each line represents one polygon
#
# The module:
#   1. Loads each image in /images/train and /images/test
#   2. Reads its corresponding label file in /labels/<split>
#   3. Draws all polygons using cv2.polylines()
#   4. Displays each annotated image inline (Jupyter)
#
# Inputs:
#   - root_dir : base path containing "images/" and "labels/"
#
# Outputs:
#   - Inline visualization of annotated images
#
# This module supports:
#   - Dataset inspection
#   - Annotation validation
#   - Polygon integrity checks
#
# Integration point in pipeline:
#   Can be used anywhere after:
#     - Dataset discovery
#     - Duplicate detection
#     - Outlier detection
#
# ------------------------------------------------------------

import cv2

def __draw_polygon_on_image(img, annotation_line):
    """
    Draw a single YOLO polygon on an image.
    """
    parts = annotation_line.strip().split()
    if len(parts) < 3:
        return img  # skip malformed lines
  
    class_id = int(parts[0])
    coords = list(map(float, parts[1:]))
  
    h, w = img.shape[:2]
    points = []
  
    # Convert normalized coords -> pixel coords
    for i in range(0, len(coords), 2):
        x_px = int(coords[i] * w)
        y_px = int(coords[i + 1] * h)
        points.append([x_px, y_px])
  
    points = np.array(points, dtype=np.int32)
  
    # Draw closed polygon
    cv2.polylines(img, [points], isClosed=True, color=(0,255,0), thickness=2)
  
    return img



def draw_polygons_for_dataset(root_dir):
    """
    Scan /images/{train,test} and /labels/{train,test},
    draw all polygons for each image, and display the result.
    """
  
    root = Path(root_dir)
    image_root = root / "images"
    label_root = root / "labels"
  
    if not image_root.exists() or not label_root.exists():
        console.log("[red]Invalid dataset structure.[/]")
        return
  
    splits = ["train", "test"]
  
    for split in splits:
        image_dir = image_root / split
        label_dir = label_root / split
      
        if not image_dir.exists():
            console.log(f"[yellow]Skipping missing split: {split}[/]")
            continue
      
        console.log(f"[cyan]Processing split: {split}[/]")
      
        image_paths = sorted(image_dir.rglob("*.jpg"))
      
        for img_path in image_paths:
            label_path = label_dir / (img_path.stem + ".txt")
          
            img = cv2.imread(str(img_path))
            if img is None:
                console.log(f"[red]Failed to read: {img_path}[/]")
                continue
          
            if not label_path.exists():
                console.log(f"[yellow]No label for image: {img_path.name}[/]")
                continue
          
            # Draw ALL polygons in the label file
            with open( label_path, 'r' ) as f :
                for line in f :
                    img = draw_polygon_on_image( img, line )
          
            # Convert BGR → RGB for notebook
            img_rgb = cv2.cvtColor( img, cv2.COLOR_BGR2RGB )
          
            # Display
            plt.figure(figsize=(8,8))
            plt.imshow(img_rgb)
            plt.title(f"{split}/{img_path.name}")
            plt.axis("off")
            plt.show()
  
    console.log("[green]All polygons drawn successfully.[/]")



# ------------------------------------------------------------
# 13. Entry Point
# ------------------------------------------------------------
# This module provides a command‑line interface for running the
# full image‑analysis pipeline. The user supplies a directory path,
# and the pipeline performs all processing steps automatically.
#
# Inputs:
#   - User input (folder path)
#
# Outputs:
#   - Triggers execution of entire pipeline
#
# This module supports:
#   - Manual activation
#   - Script usage
#
# Integration point in pipeline:
#   Place this module after:
#     12. Main Pipeline Controller
# ------------------------------------------------------------

if __name__ == '__main__':
    folder = input( 'Enter the directory path with images: ' ).strip( )
    analyze_images( folder )
