#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: set tabstop=2 shiftwidth=2 softtabstop=2 expandtab:


import os

import boto3
from botocore.config import Config

import json

import uuid, time
from PIL import Image
import imagehash
import exifread

import pandas as pd
from concurrent.futures import ProcessPoolExecutor
from tqdm import tqdm

import cv2
import numpy as np

import faiss

import logging
import warnings

from rich.console import Console
from rich.progress import Progress


# ================= CONFIG =================

S3_BUCKET = 'analise-dados'
S3_PREFIX = ''  # '' = whole bucket

AWS_ACCESS_KEY_ID     = 'AKIA5GCWF4XZPDFOUZI3'
AWS_SECRET_ACCESS_KEY = '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'
AWS_SESSION_TOKEN     = None
AWS_REGION            = 'us-east-1'

WORK_DIR = './work'
TMP_DIR  = f'{WORK_DIR}/tmp'
OUT_DIR  = f'{WORK_DIR}/output'

CHECKPOINT_DIR = f'{WORK_DIR}/checkpoints'

MAX_CPU_WORKERS = max( 1, os.cpu_count( ) - 1 )
CPU_RETRIES = 3

GPU_BATCH_SIZE = 32
BLUR_THRESHOLD = 1200
PHASH_SIM_THRESHOLD = 8

# =========================================

KEYS_FILE      = f'{CHECKPOINT_DIR}/s3_keys.json'

CPU_PENDING     = f'{CHECKPOINT_DIR}/cpu_pending.txt'
CPU_INPROGRESS  = f'{CHECKPOINT_DIR}/cpu_inprogress.txt'
CPU_DONE        = f'{CHECKPOINT_DIR}/cpu_done.txt'

BLUR_PENDING    = f'{CHECKPOINT_DIR}/blur_pending.txt'
BLUR_INPROGRESS = f'{CHECKPOINT_DIR}/blur_inprogress.txt'
BLUR_DONE       = f'{CHECKPOINT_DIR}/blur_done.txt'

FAISS_DONE      = f'{CHECKPOINT_DIR}/faiss.done'

PROCESS_LOG = f'{WORK_DIR}/processing.log'
WARNING_LOG = f'{WORK_DIR}/warning.log'

CHECKPOINT_S3_PREFIX = 'checkpoints/'

console = Console( )


def setup_logging( ) :

  logging.basicConfig(
    filename = PROCESS_LOG,
    level = logging.INFO,
    format = '%(asctime)s %(levelname)s %(message)s'
  )

  warning_logger = logging.getLogger( 'warnings' )
  warning_handler = logging.FileHandler( WARNING_LOG )
  warning_handler.setFormatter(
    logging.Formatter( '%(asctime)s %(message)s' )
  )
  warning_logger.addHandler( warning_handler )
  warning_logger.setLevel( logging.WARNING )

  def warning_hook( message, category, filename, lineno, file = None, line = None ) :
    warning_logger.warning(
      f'{category.__name__}: {message}'
    )

  warnings.showwarning = warning_hook


def ensure_dirs( ) :

  for d in [ WORK_DIR, TMP_DIR, OUT_DIR, CHECKPOINT_DIR ] :
    os.makedirs( d, exist_ok = True )


def create_s3_client( ) :

  return boto3.client(
    's3',
    region_name = AWS_REGION,
    aws_access_key_id = AWS_ACCESS_KEY_ID,
    aws_secret_access_key = AWS_SECRET_ACCESS_KEY,
    aws_session_token = AWS_SESSION_TOKEN,
    config = Config(
      max_pool_connections = 50,
      retries = {'max_attempts': 5}
    )
  )


def append_line( path, line ) :

  with open( path, 'a' ) as f :
    f.write( line + '\n' )


def load_set( path ) :

  return (
    set( open( path ).read( ).splitlines( ) )
      if os.path.exists( path ) else set( )
  )


def s3_upload_checkpoint( local_path ) :

  if not os.path.exists( local_path ) :
    logging.warning(
      f'checkpoint not found locally, skip s3 upload: {local_path}'
    )
    return

  try :

    s3 = create_s3_client( )

    key = CHECKPOINT_S3_PREFIX + os.path.basename( local_path )

    s3.upload_file(
      local_path,
      S3_BUCKET,
      key
    )

    logging.info(
      f'checkpoint uploaded to s3: {key}'
    )

  except Exception as e :

    logging.warning(
      f'checkpoint s3 upload failed, local kept: {local_path} error={e}'
    )

    return


def recover_stage( pending, inprogress, done ) :

  p = load_set( pending )
  ip = load_set( inprogress )
  d = load_set( done )

  for k in ip :
    if k not in d :
      append_line( pending, k )

  open( inprogress, 'w' ).close( )


def commit_batch_csv( path, rows ) :

  tmp = path + '.tmp'

  if os.path.exists( path ) :
    df = pd.read_csv( path )
    df = pd.concat( [ df, pd.DataFrame( rows ) ], ignore_index = True )
  else :
    df = pd.DataFrame( rows )

  df.to_csv( tmp, index = False )

  with open( tmp, 'a' ) as f :
    f.flush( )
    os.fsync( f.fileno( ) )

  os.replace( tmp, path )


def list_s3_images( ) :

  if os.path.exists( KEYS_FILE ) :
    logging.info( 'loading s3 keys from checkpoint' )
    return json.load( open( KEYS_FILE ) )

  logging.info( 'listing s3 bucket' )

  s3 = create_s3_client( )
  paginator = s3.get_paginator( 'list_objects_v2' )

  keys = [ ]

  for page in paginator.paginate( Bucket = S3_BUCKET, Prefix = S3_PREFIX ) :
    for obj in page.get( 'Contents', [ ] ) :
      k = obj[ 'Key' ]
      if k.lower( ).endswith( ('.jpg', '.jpeg', '.png', '.webp', '.tif', '.tiff' ) ) :
        keys.append( k )

  json.dump( keys, open( KEYS_FILE, 'w' ) )
  return keys


def cpu_worker( s3_key ) :

  logging.info( f'cpu processing {s3_key}' )

  s3 = create_s3_client( )
  tmp = f'{TMP_DIR}/{uuid.uuid4( ).hex}.img'

  for attempt in range( CPU_RETRIES ) :
    try :

      s3.download_file( S3_BUCKET, s3_key, tmp )

      try :
        pil = Image.open( tmp )
      except Exception as e :
        logging.getLogger( 'warnings' ).warning(
          f'{s3_key} pil open failed: {e}'
        )
        raise

      phash = str( imagehash.phash( pil ) )

      try :
        with open( tmp, 'rb' ) as f :
          exif = exifread.process_file( f, details = False )
      except Exception as e :
        logging.getLogger( 'warnings' ).warning(
          f'{s3_key} exif read failed: {e}'
        )
        exif = { }

      return {
        's3_key': s3_key,
        'width': pil.width,
        'height': pil.height,
        'megapixels': pil.width * pil.height / 1e6,
        'format': pil.format,
        'phash': phash,
        'has_exif': bool( exif ),
      }

    except Exception as e :
      err = str( e )
      time.sleep( 1 )

    finally :
      if os.path.exists( tmp ) :
        os.remove( tmp )

  logging.error( f'cpu failed {s3_key}: {err}' )
  return {'s3_key': s3_key, 'error': err}


def gpu_blur_score( gray ) :

  g = cv2.cuda_GpuMat( )
  g.upload( gray )
  gx = cv2.cuda.Sobel( g, cv2.CV_32F, 1, 0 )
  gy = cv2.cuda.Sobel( g, cv2.CV_32F, 0, 1 )
  mag = cv2.cuda.magnitude( gx, gy )
  return cv2.cuda.sum( mag )[ 0 ] / gray.size


def phash_to_vec( h ) :

  return np.array( [int( c, 16 ) for c in h], dtype = np.float32 )


def main( ) :

  ensure_dirs( )
  setup_logging( )

  console.rule( '[bold blue]Image Pipeline Started' )
  logging.info( 'pipeline started' )

  keys = list_s3_images( )

  recover_stage( CPU_PENDING, CPU_INPROGRESS, CPU_DONE )

  done = load_set( CPU_DONE )

  for k in keys :
    if k not in done :
      append_line( CPU_PENDING, k )

  pending = load_set( CPU_PENDING )

  rows = [ ]

  with Progress( ) as progress :

    task = progress.add_task( 'CPU stage', total = len( pending ) )

    with ProcessPoolExecutor( MAX_CPU_WORKERS ) as exe :

      for r in exe.map( cpu_worker, pending ) :

        progress.advance( task )

        append_line( CPU_INPROGRESS, r[ 's3_key' ] )

        if 'error' in r :
          append_line( FAILED_FILE, r[ 's3_key' ] )
        else :
          rows.append( r )

          if len( rows ) >= 100 :

            commit_batch_csv(
              f'{OUT_DIR}/metadata_hashes.csv',
              rows
            )

            for x in rows :
              append_line( CPU_DONE, x[ 's3_key' ] )

            rows = [ ]
            s3_upload_checkpoint( CPU_DONE )

  if rows :

    commit_batch_csv(
      f'{OUT_DIR}/metadata_hashes.csv',
      rows
    )

    for x in rows :
      append_line( CPU_DONE, x[ 's3_key' ] )

    s3_upload_checkpoint( CPU_DONE )

  recover_stage( BLUR_PENDING, BLUR_INPROGRESS, BLUR_DONE )

  blur_done = load_set( BLUR_DONE )

  for k in load_set( CPU_DONE ) :
    if k not in blur_done :
      append_line( BLUR_PENDING, k )

  blur_pending = load_set( BLUR_PENDING )

  blur_rows = [ ]

  for k in tqdm( blur_pending ) :

    append_line( BLUR_INPROGRESS, k )

    s3 = create_s3_client( )
    tmp = f'{TMP_DIR}/{uuid.uuid4( ).hex}.img'

    try :

      s3.download_file( S3_BUCKET, k, tmp )
      gray = cv2.imread( tmp, cv2.IMREAD_GRAYSCALE )

      if gray is None :
        logging.getLogger( 'warnings' ).warning(
          f'{k} cv2 read failed'
        )
        continue

      score = gpu_blur_score( gray )

      blur_rows.append( {
        's3_key': k,
        'blur_score': score,
        'blurry': score < BLUR_THRESHOLD
      } )

      if len( blur_rows ) >= 100 :

        commit_batch_csv(
          f'{OUT_DIR}/blur_metrics.csv',
          blur_rows
        )

        for x in blur_rows :
          append_line( BLUR_DONE, x[ 's3_key' ] )

        blur_rows = [ ]
        s3_upload_checkpoint( BLUR_DONE )

    finally :
      if os.path.exists( tmp ) :
        os.remove( tmp )

  if blur_rows :

    commit_batch_csv(
      f'{OUT_DIR}/blur_metrics.csv',
      blur_rows
    )

    for x in blur_rows :
      append_line( BLUR_DONE, x[ 's3_key' ] )

    s3_upload_checkpoint( BLUR_DONE )

  if not os.path.exists( FAISS_DONE ) :

    logging.info( 'faiss stage started' )

    df_cpu = pd.read_csv( f'{OUT_DIR}/metadata_hashes.csv' )
    df_blur = pd.read_csv( f'{OUT_DIR}/blur_metrics.csv' )

    df = df_cpu.merge( df_blur, on = 's3_key', how = 'left' )

    vecs = np.stack( df[ 'phash' ].apply( phash_to_vec ).values )

    res = faiss.StandardGpuResources( )
    index = faiss.IndexFlatL2( vecs.shape[ 1 ] )
    gpu_index = faiss.index_cpu_to_gpu( res, 0, index )

    gpu_index.add( vecs )
    D, I = gpu_index.search( vecs, k = 5 )

    df[ 'nearest_duplicate' ] = I[ : , 1 ]
    df[ 'similarity_distance' ] = D[ : , 1 ]
    df[ 'near_duplicate' ] = df[ 'similarity_distance' ] < PHASH_SIM_THRESHOLD

    tmp_out = f'{OUT_DIR}/image_metrics_with_similarity.csv.tmp'

    df.to_csv( tmp_out, index = False )

    os.replace(
      tmp_out,
      f'{OUT_DIR}/image_metrics_with_similarity.csv'
    )

    open( FAISS_DONE + '.tmp', 'w' ).write( 'done' )
    os.replace( FAISS_DONE + '.tmp', FAISS_DONE )

    s3_upload_checkpoint( FAISS_DONE )

  logging.info( 'pipeline completed' )
  console.rule( '[bold green]Completed' )


if __name__ == '__main__' :

  main( )
