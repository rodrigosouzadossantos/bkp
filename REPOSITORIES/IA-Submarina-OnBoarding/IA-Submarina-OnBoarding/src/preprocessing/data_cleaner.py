#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: set tabstop=2 shiftwidth=2 softtabstop=2 noexpandtab:

import polars as pl

import numpy as np

from sklearn.cluster import AgglomerativeClustering
from sklearn.feature_extraction.text import CountVectorizer

from Levenshtein import distance as lev_distance
from sentence_transformers import SentenceTransformer
from keybert import KeyBERT


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
data = (
  Path( __file__ )
    .parent
    .parent
    .parent
    .resolve( )
    / 'data/raw/dados-submarinos'
)

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

# -----------------------------
#
# -----------------------------

serv_class = (
  df.select( 'class_norm' )
  .filter(
    pl.col( 'class_norm')
    .is_not_null( )
  ).unique( )
  .to_series( )
  .to_list( )
)
serv_class = [
  s for s in serv_class if s is not None
]
dist_matrix = np.array( [
  [ lev_distance( a, b ) for b in serv_class ]
  for a in serv_class
] )

# Clustering
n_clusters = 80
clustering = AgglomerativeClustering(
  n_clusters = n_clusters,
  metric = 'precomputed',
  linkage = 'average'
)
labels = clustering.fit_predict(dist_matrix)
suit_to_cluster = dict( zip( serv_class, labels ) )

df = df.filter(
    pl.col( 'class_norm' ).is_not_null( )
  ).with_columns(
  pl.col( 'class_norm' ).map_elements(
        lambda x: suit_to_cluster.get(x, -1),
        return_dtype=pl.Int32
    ).alias( 'class_cluster' )
)

cols = df.columns
cols.remove( 'class_cluster' )
cols.insert(
  cols.index( 'class_norm' ) + 1, 'class_cluster'
)

df = df.select( cols )

# -----------------------------
#
# -----------------------------

st_model = SentenceTransformer( 'all-mpnet-base-v2' )

def centroid_label( texts, top_n = 3 ) :
	# 1. basic cleanup
	texts = [
		t for t in texts if t and isinstance( t, str )
	]

	if len( texts ) == 0 :
		return 'Desconhecido'

	# 2. embed cluster texts
	emb = st_model.encode( texts )
	cen = np.mean( emb, axis = 0 )

	# --------------------------------------
	# 3. extract candidate phrases robustly
	# --------------------------------------
	vec = CountVectorizer(
		ngram_range=( 1, 3 ),
		stop_words = None, # keep Portuguese
		min_df = 1,
		token_pattern = r"(?u)\b\w+\b" # capture codes, pidf-3 → pidf, 3
	)

	try:
		vec.fit( texts )
	except ValueError :
		return 'Desconhecido'

	cand = vec.get_feature_names_out( )
	if len( cand ) == 0 :
		return 'Desconhecido'

	# 4. embed candidates
	cemb = st_model.encode( cand )

	# 5. cosine similarity with centroid
	num = np.dot( cemb, cen )
	den = np.linalg.norm( cemb, axis = 1 ) * np.linalg.norm( cen )
	sim = num / den

	# 6. pick best N
	idx = sim.argsort( )[ ::-1 ][ :top_n ]

	ph = [ cand[ i ].capitalize( ) for i in idx ]
	if len( ph ) == 1 :
		return ph[ 0 ]

	return f"{ph[0]} ({' / '.join(ph[1:])})"


def label_with_centroid( df ) :
	labels = [ ]
	for cl in df[ 'class_cluster' ].unique( ) :
		sub = df.filter( pl.col( 'class_cluster' ) == cl )
		texts = sub[ 'class_norm' ].to_list( )
		label = centroid_label( texts )
		labels.append( {
			'class_cluster' : cl,
			'cluster_label_st' : label
		} )
	mapdf = pl.DataFrame( labels )
	return df.join(
		mapdf,
		on = 'class_cluster',
		how = 'left'
	)


# -----------------------------
#
# -----------------------------

kw_model = KeyBERT( model = 'all-mpnet-base-v2' )

def label_with_keybert( df ) :
	labs = [ ]
	clusters = df[ 'class_cluster' ].unique( )
	for cl in clusters :
		sub = df.filter( pl.col( 'class_cluster' ) == cl )
		txt = sub[ 'class_norm' ].to_list( )
		doc = ' '.join( txt )
		kws = kw_model.extract_keywords(
			doc,
			keyphrase_ngram_range = ( 1, 3 ),
			stop_words = None,
			use_mmr = True,
			diversity = 0.4,
			top_n = 3
		)
		ph = [ k for k, _ in kws ]
		ph = [ p.capitalize( ) for p in ph ]
		if len( ph ) == 0 :
			lab = 'Desconhecido'
		elif len( ph ) == 1 :
			lab = ph[ 0 ]
		else :
			lab = f"{ph[0]} ({' / '.join(ph[1:])})"
		labs.append({
			'class_cluster' : cl,
			'cluster_label_kb' : lab
		})
	mapdf = pl.DataFrame( labs )
	return df.join(
		mapdf,
		on = 'class_cluster',
		how = 'left'
	)


df = label_with_centroid( df )
df = label_with_keybert( df )

cols = df.columns

cols.remove( 'cluster_label_kb' )
cols.insert(
  cols.index( 'class_cluster' ) + 1, 'cluster_label_kb'
)

cols.remove( 'cluster_label_st' )
cols.insert(
  cols.index( 'class_cluster' ) + 1, 'cluster_label_st'
)

df = df.select( cols )

# ============================================
# Save as Parquet
# ============================================
df.write_parquet( f'{data}.parquet' )

print( df.sample( ) )
