#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: set tabstop=2 shiftwidth=2 softtabstop=2 noexpandtab:

import polars as pl

import plotly.express as px
import plotly.graph_objects as go
import ipywidgets as widgets

import numpy as np
from sklearn.cluster import AgglomerativeClustering
from polars import DataFrame

from Levenshtein import distance as lev_distance


def build_sankey_tab( df : pl.DataFrame ) :

  req = [
    "class_norm","company_norm","un_norm",
    "bucket_norm","files_size","cluster_label_kb"
  ]

  for c in req :
    if c not in df.columns :
      raise ValueError( f"'{c}' missing" )

  dfc = df.filter(
      pl.col( 'class_norm' ).is_not_null( ) &
      pl.col( 'company_norm' ).is_not_null( ) &
      pl.col( 'un_norm' ).is_not_null( ) &
      pl.col( 'bucket_norm' ).is_not_null( ) &
      pl.col( 'cluster_label_kb' ).is_not_null( ) &
      pl.col( 'files_size' ).is_not_null( )
  )

  def apply_topn( df, col, n ) -> pl.DataFrame :
    keep = set(
      df.group_by( col )
        .agg( pl.col( 'files_size' )
        .sum( ).alias( 'sz' ) )
        .sort( 'sz', descending = True )
        .head( n )[ col ]
        .to_list( )
    )
    return df.with_columns(
      pl.when( pl.col( col ).is_in( keep ) )
        .then( pl.col( col ) )
        .otherwise( pl.lit( 'OTHER_' + col.upper( ) ) )
        .alias( col )
    )

  dfc = apply_topn( dfc, "class_norm",          15 )
  dfc = apply_topn( dfc, "cluster_label_kb",    15 )
  dfc = apply_topn( dfc, "company_norm",        20 )
  dfc = apply_topn( dfc, "un_norm",             20 )
  dfc = apply_topn( dfc, "bucket_norm",         20 )

  def sankey_nodes( df, cols ) :
    out = [ ]
    for c in cols :
      out += df[ c ].unique( ).to_list( )
    return out, { n : i for i, n in enumerate( out ) }

  def sankey_links( df, scol, tcol, idx ) :
      g = df.group_by( [ scol, tcol ] ).agg(
        pl.col( 'files_size' ).sum( ).alias( 'v' )
      )
      src = [ idx[ r[ scol ] ] for r in g.iter_rows( named = True ) ]
      tgt = [ idx[ r[ tcol ] ] for r in g.iter_rows( named = True ) ]
      val = [ r[ 'v' ] for r in g.iter_rows( named = True ) ]
      return src, tgt, val

    def cluster_colors( clusters ) :
      import colorsys
      out = { }
      L = sorted( clusters )
      n = len( L )
      for i, c in enumerate( L ) :
          h = i / max( 1, n - 1 )
          r, g, b = colorsys.hsv_to_rgb( h, 0.55, 0.95 )
          out[ c ] = f"rgba({int(r*255)},{int(g*255)},{int(b*255)},0.85)"
      return out

    def build( fig_nodes, idx, flows, title, node_colors = None ) :
      src=sum( [ f[ 0 ] for f in flows ], [ ] )
      tgt=sum( [ f[ 1 ] for f in flows ], [ ] )
      val=sum( [ f[ 2 ] for f in flows ], [ ] )
      vmax = max( val );
      vmin = min( val )
  
      def cs( v ) :
        x = ( v - vmin ) / ( vmax - vmin + 1e-9 )
        r = int( 255 * x );
        g = int( 210 * ( 1 - x ) );
        b = int( 50 * ( 1 - x ) )
        return f"rgba({r},{g},{b},0.55)"

      lcols = [ cs( v ) for v in val ]
      inc = { n : 0.0 for n in fig_nodes }
      outv = { n : 0.0 for n in fig_nodes }
      sn = fig_nodes

      for s, t, v in zip( src, tgt, val ) :
        outv[ sn[ s ] ] += v
        inc[ sn[ t ] ] += v

      fmt = lambda x:f"{x/1024:.2f} TB"
      cd = [ [ fmt( inc[ n ] ), fmt( outv[ n ] ) ] for n in fig_nodes ]

      labels = [
        f"<span style='color:#0d6efd;font-weight:bold;"
        f"font-style:italic;'>{n}</span>"
        for n in fig_nodes
      ]
          
      if node_colors is None :
        ncol = "rgba(40,40,40,0.9)"
        node_colors = [ ncol ] * len( fig_nodes )
      
      node = dict(
        label = labels, pad = 20, thickness = 20,
        color = node_colors, customdata = cd,
        hovertemplate =
        "<b>%{label}</b><br>In: %{customdata[0]}<br>"
        "Out: %{customdata[1]}<extra></extra>"
      )

      link = dict(
        source = src, target = tgt, value = val,
        color = lcols,
        hovertemplate = "Flow: %{value}<extra></extra>"
      )

      f = go.Figure( data = [ go.Sankey( node = node, link = link ) ] )
      f.update_traces( arrangement = "snap" )
      f.update_layout( title = title, font_size = 12, height = 900 )
      return f

  def concat_flows( * flows ) :
    src = [ v for f in flows for v in f[ 0 ] ]
    tgt = [ v for f in flows for v in f[ 1 ] ]
    val = [ v for f in flows for v in f[ 2 ] ]
    return src, tgt, val

  def build_chain_sankey( dfc, title, color_map = None ) :
    def arrow_title_to_list( title ) :
      import re
      import unicodedata
      def norm( t ) :
        t = unicodedata.normalize( 'NFD', t )
        t = "".join( c for c in t if unicodedata.category( c ) != 'Mn' )
        t = t.lower( )
        t = re.sub( r'[^a-z0-9]+', '_', t ).strip( '_' )
        return t + "_norm"
      return [ norm( p.strip( ) ) for p in title.split( '→' ) ]

    cols = arrow_title_to_list( title )
    nodes, idx = sankey_nodes( dfc, cols )
    flows = [
      sankey_links( dfc, cols[ i ], cols[ i + 1 ], idx )
      for i in range( len( cols ) - 1 )
    ]

    idx = { n : i for i, n in enumerate( nodes ) }

    if color_map is None :
      node_colors = [ "rgba(40,40,40,0.9)" ] * len(nodes)
    else :
      node_colors = [
        color_map.get( n, "rgba(40,40,40,0.9)" )
        for n in nodes
      ]

    fig = build(
      nodes, idx,
      flows,
      title,
      node_colors
    )

    return fig

  # sankey 1
  fig1 = build_chain_sankey(
    dfc,
    "Class → Company → UN → Bucket"
  )

  # sankey 2
  fig2 = build_chain_sankey(
    dfc,
    "Cluster → Company → UN → Bucket",
    cluster_colors(
      dfc[ 'cluster_label_kb' ].unique( ).to_list( )
    )
  )

  o1 = widgets.Output( )
  o2 = widgets.Output( )

  with o1: fig1.show( )
  with o2: fig2.show( )

  return widgets.VBox(
    [ o1, o2 ],
    layout=widgets.Layout(padding="20px")
  )

def __build_sankey_tab(df: pl.DataFrame):
    TOP_N_CLASS=15
    TOP_N_COMPANY=20
    TOP_N_UN=20
    TOP_N_BUCKET=20
    required=["class_norm","company_norm","un_norm","bucket_norm","files_size"]

    for c in required:
        if c not in df.columns:
            raise ValueError(f"Column '{c}' missing.")

    suits = df.select("class_norm").filter( pl.col( 'class_norm').is_not_null() ).unique( ).to_series( ).to_list( )
    suits = [s for s in suits if s is not None]
    dist_matrix = np.array([[lev_distance(a, b) for b in suits] for a in suits])
    
    n_clusters = 80  # exemplo, ajuste conforme necessário
    clustering = AgglomerativeClustering(n_clusters=n_clusters, metric='precomputed', linkage='average')
    labels = clustering.fit_predict(dist_matrix)
    
    suit_to_cluster = dict(zip(suits, labels))

    
    dfc=df.filter(
        pl.col("class_norm").is_not_null()&
        pl.col("company_norm").is_not_null()&
        pl.col("un_norm").is_not_null()&
        pl.col("bucket_norm").is_not_null()&
        pl.col("files_size").is_not_null()
    )
    dfc=dfc.with_columns(
        pl.col("class_norm").map_elements(
            lambda x: suit_to_cluster.get(x,-1),
            return_dtype=pl.Int32
        ).alias("class_cluster")
    )
    valid=(
        dfc.group_by("class_cluster")
        .agg(pl.len().alias("count"))
        .filter(pl.col("count")>160)
        .select("class_cluster")
        .to_series()
        .to_list()
    )
    dfc=dfc.filter(pl.col("class_cluster").is_in(valid))
    def topn( col, n ) :
        top = dfc.group_by(col).agg(pl.col("files_size").sum().alias("size")).sort("size",descending=True).head(n)
        keep=set(top[col].to_list())
        return dfc.with_columns(
            pl.when(pl.col(col).is_in(keep))
            .then(pl.col(col))
            .otherwise(pl.lit(f"OTHER_{col.upper()}"))
            .alias(col)
        )
    dfc=topn("class_norm",TOP_N_CLASS)
    dfc=topn("company_norm",TOP_N_COMPANY)
    dfc=topn("un_norm",TOP_N_UN)
    dfc=topn("bucket_norm",TOP_N_BUCKET)
    class_list=dfc["class_norm"].unique().to_list()
    company_list=dfc["company_norm"].unique().to_list()
    un_list=dfc["un_norm"].unique().to_list()
    bucket_list=dfc["bucket_norm"].unique().to_list()
    nodes=class_list+company_list+un_list+bucket_list
    node_index={n:i for i,n in enumerate(nodes)}
    f1=(
        dfc.group_by(["class_norm","company_norm"])
        .agg(pl.col("files_size").sum().alias("value"))
    )
    src1=[node_index[r["class_norm"]] for r in f1.iter_rows(named=True)]
    tgt1=[node_index[r["company_norm"]] for r in f1.iter_rows(named=True)]
    val1=[r["value"] for r in f1.iter_rows(named=True)]
    f2=(
        dfc.group_by(["company_norm","un_norm"])
        .agg(pl.col("files_size").sum().alias("value"))
    )
    src2=[node_index[r["company_norm"]] for r in f2.iter_rows(named=True)]
    tgt2=[node_index[r["un_norm"]] for r in f2.iter_rows(named=True)]
    val2=[r["value"] for r in f2.iter_rows(named=True)]
    f3=(
        dfc.group_by(["un_norm","bucket_norm"])
        .agg(pl.col("files_size").sum().alias("value"))
    )
    src3=[node_index[r["un_norm"]] for r in f3.iter_rows(named=True)]
    tgt3=[node_index[r["bucket_norm"]] for r in f3.iter_rows(named=True)]
    val3=[r["value"] for r in f3.iter_rows(named=True)]
    incoming={n:0.0 for n in nodes}
    outgoing={n:0.0 for n in nodes}
    for s,t,v in zip(src1,tgt1,val1):
        outgoing[nodes[s]]+=v
        incoming[nodes[t]]+=v
    for s,t,v in zip(src2,tgt2,val2):
        outgoing[nodes[s]]+=v
        incoming[nodes[t]]+=v
    for s,t,v in zip(src3,tgt3,val3):
        outgoing[nodes[s]]+=v
        incoming[nodes[t]]+=v
    def fmt(x):return f"{x/1024:.2f} TB"
    custom=[[fmt(incoming[n]),fmt(outgoing[n])] for n in nodes]
    link_values=val1+val2+val3
    vmax=max(link_values)
    vmin=min(link_values)
    def color_scale(v):
        x=(v-vmin)/(vmax-vmin+1e-9)
        r=int(255*x)
        g=int(120*(1-x))
        b=int(40*(1-x))
        return f"rgba({r},{g},{b},0.55)"
    link_colors=[color_scale(v) for v in link_values]
    node=dict(
        label=[f"<span style='color:black'>{n}</span>" for n in nodes],
        pad=20,
        thickness=20,
        color="rgba(40,40,40,0.9)",
        customdata=custom,
        hovertemplate="<b>%{label}</b><br>Incoming: %{customdata[0]}<br>Outgoing: %{customdata[1]}<extra></extra>"
    )
    link=dict(
        source=src1+src2+src3,
        target=tgt1+tgt2+tgt3,
        value=link_values,
        color=link_colors,
        hovertemplate="Flow: %{value}<extra></extra>"
    )
    fig=go.Figure(data=[go.Sankey(node=node,link=link)])
    fig.update_layout(
        title="class → company → un → bucket",
        font_size=12,
        height=820
    )
    output = widgets.Output()
    with output:
        fig.show()
    tab_content = widgets.VBox(
        [
            output,
        ],
        layout=widgets.Layout(padding="20px")
    )
    return tab_content






###########

def sankey( df ) :
	TOP_N_VESSELS = 4

	# 1. BASE
	df_sankey = (
			df.select([
				"un","os","field_location","company","vessel","files_size"
				])
			.with_columns([
				pl.concat_str([pl.lit("Unity: "), pl.col("un")]).alias("u"),
				#pl.concat_str([pl.lit("Solicitation: "), pl.col("os")]).alias("s"),
				pl.concat_str([pl.lit("Location: "), pl.col("field_location")]).alias("l"),
				pl.concat_str([pl.lit("Company: "), pl.col("company")]).alias("c"),
				pl.concat_str([pl.lit("Vessel: "), pl.col("vessel")]).alias("v"),
				])
			)
	# 2. TOP VESSELS
	top_vessels = (
			df_sankey.group_by("v")
					.agg(pl.sum("files_size").alias("total"))
					.sort("total", descending=True)
					.head(TOP_N_VESSELS)
	)
	df_sankey = df_sankey.with_columns(
			pl.when(pl.col("v").is_in(top_vessels["v"].implode()))
				.then(pl.col("v"))
				.otherwise(pl.lit("Vessel: Other"))
				.alias("v")
	)
	# 3. LINKS
	pairs = [("u","l"),("l","c"),("c","v")]
	links = pl.concat([
			df_sankey.group_by([s,t])
					.agg(pl.sum("files_size").alias("value"))
					.rename({s:"source", t:"target"})
			for s,t in pairs
	])
	# 4. NODES (only id + label)
	nodes = (
			pl.concat([
					links.select(pl.col("source").alias("label")),
					links.select(pl.col("target").alias("label")),
			])
			.unique()
			.sort("label")
			.with_row_index("id")
	)
	print("After initial nodes creation:", nodes.columns)
	# should be: ["id","label"]
	# 5. MAP LINKS → IDS
	links = (
			links
			.join(nodes, left_on="source", right_on="label", how="left")
			.rename({"id":"source_id"})
			.drop("label", strict=False)
			.join(nodes, left_on="target", right_on="label", how="left")
			.rename({"id":"target_id"})
			.drop("label", strict=False)
	)
	# 6. ADD LAYER COLUMN
	nodes = nodes.with_columns([
			pl.when(pl.col("label").str.starts_with("Unity:")).then(pl.lit(0))
	#      .when(pl.col("label").str.starts_with("Solicitation:")).then(pl.lit(1))
				.when(pl.col("label").str.starts_with("Location:")).then(pl.lit(1))
				.when(pl.col("label").str.starts_with("Company:")).then(pl.lit(2))
				.when(pl.col("label").str.starts_with("Vessel:")).then(pl.lit(3))
				.otherwise(pl.lit(-1))
				.alias("layer")
	])
	print("After adding layer:", nodes.columns)
	# should now include: "layer"
	# 7. ADD X POSITION + COLOR
	nodes = nodes.with_columns([
			pl.when(pl.col("layer") == 0).then(pl.lit(0.0))
				.when(pl.col("layer") == 1).then(pl.lit(0.25))
				.when(pl.col("layer") == 2).then(pl.lit(0.50))
				.when(pl.col("layer") == 3).then(pl.lit(0.75))
				.when(pl.col("layer") == 4).then(pl.lit(1.00))
				.otherwise(pl.lit(0.00))
				.alias("x"),
		pl.when(pl.col("layer") == 0).then(pl.lit("#4C78A8"))
				.when(pl.col("layer") == 1).then(pl.lit("#F58518"))
				.when(pl.col("layer") == 2).then(pl.lit("#54A24B"))
				.when(pl.col("layer") == 3).then(pl.lit("#E45756"))
				.when(pl.col("layer") == 4).then(pl.lit("#72B7B2"))
				.otherwise(pl.lit("#999999"))
				.alias("color")
	])
	print("Final nodes columns:", nodes.columns)
	# should be: ["id","label","layer","x","color"]
	# 8. ADD LINK COLOR
	links = links.with_columns(
			pl.lit("rgba(150,150,150,0.25)").alias("link_color")
	)
	# 9. PLOT
	fig = go.Figure(go.Sankey(
			arrangement="snap",
			node=dict(
					pad=15,
					thickness=14,
					label=nodes["label"].to_list(),
					color=nodes["color"].to_list(),
					x=nodes["x"].to_list(),
			),
			link=dict(
					source=links["source_id"].to_list(),
					target=links["target_id"].to_list(),
					value=links["value"].to_list(),
					color=links["link_color"].to_list(),
			)
	))

	fig.update_layout(
			title=f"Operational Data Volume Flow – Top {TOP_N_VESSELS} Vessels",
			font_size=11,
			margin=dict(l=10, r=10, t=45, b=10)
	)
	fig.write_html("sankey.html")
