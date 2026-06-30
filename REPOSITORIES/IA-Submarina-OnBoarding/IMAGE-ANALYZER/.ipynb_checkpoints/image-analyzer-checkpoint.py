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



# ================= CONFIG =================
 
S3_BUCKET = 'analise-dados'
S3_PREFIX = ''  # '' = whole bucket
 
AWS_ACCESS_KEY_ID = 'AKIA5GCWF4XZPDFOUZI3'
AWS_SECRET_ACCESS_KEY = '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'
AWS_SESSION_TOKEN = ''   # can be None
AWS_REGION = 'us-east-1'
 
WORK_DIR = './work'
TMP_DIR = f'{WORK_DIR}/tmp'
OUT_DIR = f'{WORK_DIR}/output'
CHECKPOINT_DIR = f'{WORK_DIR}/checkpoints'
 
MAX_CPU_WORKERS = max( 1, os.cpu_count( ) - 1 )
CPU_RETRIES = 3
 
GPU_BATCH_SIZE = 32
BLUR_THRESHOLD = 1200
PHASH_SIM_THRESHOLD = 8
 
# =========================================

#import os
for d in [ WORK_DIR, TMP_DIR, OUT_DIR, CHECKPOINT_DIR ] :
  os.makedirs( d, exist_ok = True )

#import boto3
#from botocore.config import Config
 
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

#import json
 
KEYS_FILE = f'{CHECKPOINT_DIR}/s3_keys.json'
 
def list_s3_images( ) :
  if os.path.exists( KEYS_FILE ) :
    return json.load( open( KEYS_FILE ) )
 
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

PROCESSED_FILE = f'{CHECKPOINT_DIR}/processed_keys.txt'
FAILED_FILE = f'{CHECKPOINT_DIR}/failed_keys.txt'
 
def load_set( path ) :
  return (
    set( open( path ).read( ).splitlines( ) )
      if os.path.exists( path ) else set( )
  )
 
def append_line( path, line ) :
  with open( path, 'a' ) as f :
    f.write( line + '\n' )

#import uuid, time
#from PIL import Image
#import imagehash
#import exifread
 
def cpu_worker( s3_key ) :
  s3 = create_s3_client( )
  tmp = f'{TMP_DIR}/{uuid.uuid4( ).hex}.img'
 
  for attempt in range( CPU_RETRIES ) :
    try :
      s3.download_file( S3_BUCKET, s3_key, tmp )
 
      pil = Image.open( tmp )
      phash = str( imagehash.phash( pil ) )
 
      with open( tmp, 'rb' ) as f :
        exif = exifread.process_file( f, details = False )
 
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
 
  return {'s3_key': s3_key, 'error': err}

#import pandas as pd
#from concurrent.futures import ProcessPoolExecutor
#from tqdm import tqdm
 
keys = list_s3_images( )
processed = load_set( PROCESSED_FILE )
failed = load_set( FAILED_FILE )
 
pending = [ k for k in keys if k not in processed ]
 
rows = [ ]
 
with ProcessPoolExecutor( MAX_CPU_WORKERS ) as exe :
  for r in tqdm( exe.map( cpu_worker, pending ), total = len( pending ) ) :
    if 'error' in r :
      append_line( FAILED_FILE, r[ 's3_key' ] )
    else :
      rows.append( r )
      append_line( PROCESSED_FILE, r[ 's3_key' ] )
 
df_cpu = pd.DataFrame( rows )
df_cpu.to_csv( f'{OUT_DIR}/metadata_hashes.csv', index = False )

#import cv2
#import numpy as np
 
def gpu_blur_score( gray ) :
  g = cv2.cuda_GpuMat( )
  g.upload( gray )
  gx = cv2.cuda.Sobel( g, cv2.CV_32F, 1, 0 )
  gy = cv2.cuda.Sobel( g, cv2.CV_32F, 0, 1 )
  mag = cv2.cuda.magnitude( gx, gy )
  return cv2.cuda.sum( mag )[ 0 ] / gray.size
 
BLUR_FILE = f'{CHECKPOINT_DIR}/blur_done.txt'
blur_done = load_set( BLUR_FILE )
 
blur_rows = [ ]
 
for i in tqdm( range( 0, len( df_cpu ), GPU_BATCH_SIZE ) ) :
  batch = df_cpu.iloc[ i:i+GPU_BATCH_SIZE ]
 
  for _, row in batch.iterrows( ) :
    if row[ 's3_key' ] in blur_done :
      continue
 
    s3 = create_s3_client( )
    tmp = f'{TMP_DIR}/{uuid.uuid4( ).hex}.img'
 
    try :
      s3.download_file( S3_BUCKET, row[ 's3_key' ], tmp )
      gray = cv2.imread( tmp, cv2.IMREAD_GRAYSCALE )
      score = gpu_blur_score( gray )
 
      blur_rows.append( {
        's3_key': row[ 's3_key' ],
        'blur_score': score,
        'blurry': score < BLUR_THRESHOLD
      } )
 
      append_line( BLUR_FILE, row[ 's3_key' ] )
 
    finally :
      if os.path.exists( tmp ) :
        os.remove( tmp )
 
df_blur = pd.DataFrame( blur_rows )
df = df_cpu.merge( df_blur, on = 's3_key', how = 'left' )
df.to_csv( f'{OUT_DIR}/image_metrics.csv', index = False )

#import faiss
 
def phash_to_vec( h ) :
  return np.array( [int( c, 16 ) for c in h ], dtype = np.float32 )
 
vecs = np.stack( df[ 'phash' ].apply( phash_to_vec ).values )
 
res = faiss.StandardGpuResources( )
index = faiss.IndexFlatL2( vecs.shape[ 1 ] )
gpu_index = faiss.index_cpu_to_gpu( res, 0, index )
 
gpu_index.add( vecs )
D, I = gpu_index.search( vecs, k = 5 )
 
df[ 'nearest_duplicate' ] = I[ : , 1 ]
df[ 'similarity_distance' ] = D[ : , 1 ]
df[ 'near_duplicate' ] = df[ 'similarity_distance' ] < PHASH_SIM_THRESHOLD
 
df.to_csv( f'{OUT_DIR}/image_metrics_with_similarity.csv', index = False )
