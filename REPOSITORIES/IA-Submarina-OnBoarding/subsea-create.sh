#!/usr/bin/env bash
set -e

ROOT='Subsea'

echo 'Resetting Subsea project...'
rm -rf "${ROOT}"

echo 'Creating directory structure...'
mkdir -p \
  "${ROOT}/data" \
  "${ROOT}/media" \
  "${ROOT}/cv" \
  "${ROOT}/pipelines" \
  "${ROOT}/plotting" \
  "${ROOT}/adapters" \
  "${ROOT}/tests"


python_header( ) {
  printf '%s\n' \
'#!/usr/bin/env python3' \
'# -*- coding: utf-8 -*-' \
'# vim: set tabstop=2 shiftwidth=2 softtabstop=2 expandtab:' \
'' \
'' \
''
}


write_py( ) {

  local file="$1"
  shift

  python_header > "${file}"

  printf '%s\n' "$*" >> "${file}"

}


write_txt( ) {

  local file="$1"
  shift

  printf '%s\n' "$*" > "${file}"

}


echo 'Creating core modules...'
write_py "${ROOT}/__init__.py" '

'

write_py "${ROOT}/config.py" '

from pathlib import Path


class SubseaConfig :

  ROOT = Path( "." )

  DATA_DIR = ROOT / "data"

  LOG_FILE = ROOT / "subsea.log"

'

write_py "${ROOT}/logging.py" '

import logging

from rich.logging import RichHandler

from Subsea.config import SubseaConfig


def setup_logging( ) :

  logging.basicConfig(
    level = logging.INFO,
    handlers = [
      RichHandler( ),
      logging.FileHandler(
        SubseaConfig.LOG_FILE
      )
    ]
  )

'

write_py "${ROOT}/observability.py" '

import time
import logging

from rich.console import Console
from rich.status import Status


class SubseaComponent :

  console = Console( )

  def __init__( self ) :

    self.log = logging.getLogger(
      "Subsea.%s" % self.__class__.__name__
    )

  def step( self, message ) :

    self.log.info( message )
    self.console.log(
      "[bold cyan]%s" % message
    )


def trace( name = None ) :

  def decorator( fn ) :

    label = name or fn.__name__

    def wrapper( self, *args, **kwargs ) :

      full = "%s.%s" % (
        self.__class__.__name__,
        label
      )

      start = time.time( )

      self.log.info(
        "start %s" % full
      )

      with Status(
        "Running %s..." % full,
        console = self.console
      ) :

        try :

          result = fn(
            self,
            *args,
            **kwargs
          )

          elapsed = time.time( ) - start

          self.log.info(
            "end %s elapsed=%.2fs" % (
              full,
              elapsed
            )
          )

          self.console.log(
            "[green]Completed %s" % full
          )

          return result

        except Exception as e :

          self.log.exception(
            "failed %s" % full
          )

          self.console.log(
            "[red]Failed %s: %s" % (
              full,
              e
            )
          )

          raise

    return wrapper

  return decorator

'

write_py "${ROOT}/runtime.py" '

import os

from concurrent.futures import ProcessPoolExecutor

from Subsea.observability import SubseaComponent, trace


class Runtime( SubseaComponent ) :

  def __init__( self, workers = None ) :

    super( ).__init__()

    self.workers = (
      workers or max(
        1,
        os.cpu_count( ) - 1
      )
    )

  @trace( )
  def map( self, fn, items ) :

    self.step(
      "Executing with %d workers" %
      self.workers
    )

    with ProcessPoolExecutor(
      self.workers
    ) as exe :

      return list(
        exe.map( fn, items )
      )

'


echo 'Creating data interfaces...'
write_py "${ROOT}/data/__init__.py" '

'

write_py "${ROOT}/data/parquet.py" '

import polars as pl

from Subsea.observability import SubseaComponent, trace


class ParquetStore( SubseaComponent ) :

  @trace( )
  def write( self, df, path ) :

    self.step(
      "Writing parquet %s" % path
    )

    df.write_parquet(
      path
    )

  @trace( )
  def read( self, path ) :

    self.step(
      "Reading parquet %s" % path
    )

    return pl.read_parquet(
      path
    )

'


echo 'Creating media interfaces...'
write_py "${ROOT}/media/__init__.py" '

'

write_py "${ROOT}/media/image.py" '

import cv2
from pathlib import Path

from Subsea.observability import SubseaComponent, trace


class ImageSource( SubseaComponent ) :

  def __init__( self, paths ) :

    super( ).__init__()

    self.paths = [
      Path( p )
      for p in paths
    ]

  @trace( )
  def __iter__( self ) :

    for p in self.paths :

      self.step(
        "Loading image %s" % p
      )

      yield p, cv2.imread(
        str( p )
      )

'

write_py "${ROOT}/media/video.py" '

import cv2

from Subsea.observability import SubseaComponent, trace


class VideoSource( SubseaComponent ) :

  def __init__( self, path ) :

    super( ).__init__()

    self.cap = cv2.VideoCapture(
      path
    )

  @trace( )
  def frames( self ) :

    while True :

      ret, frame = self.cap.read( )

      if not ret :

        break

      yield frame

'


echo 'Creating CV layer...'
write_py "${ROOT}/cv/__init__.py" '

'

write_py "${ROOT}/cv/blur.py" '

import cv2

from Subsea.observability import SubseaComponent, trace


class BlurDetector( SubseaComponent ) :

  @trace( )
  def score( self, gray ) :

    self.step(
      "Computing blur score"
    )

    if cv2.cuda.getCudaEnabledDeviceCount( ) > 0 :

      g = cv2.cuda_GpuMat( )
      g.upload(
        gray
      )

      lap = cv2.cuda.Laplacian(
        g,
        cv2.CV_32F
      )

      return cv2.cuda.sum(
        lap
      )[ 0 ]

    return cv2.Laplacian(
      gray,
      cv2.CV_32F
    ).var( )

'


echo 'Creating adapters...'
write_py "${ROOT}/adapters/s3.py" '

import boto3

from Subsea.observability import SubseaComponent, trace


class S3Adapter( SubseaComponent ) :

  def __init__( self, bucket ) :

    super( ).__init__()

    self.s3 = boto3.client(
      "s3"
    )

    self.bucket = bucket

  @trace( )
  def download( self, key, path ) :

    self.step(
      "Downloading %s" % key
    )

    self.s3.download_file(
      self.bucket,
      key,
      path
    )

'

write_py "${ROOT}/adapters/duckdb.py" '

import duckdb

from Subsea.observability import SubseaComponent, trace


class DuckDBAdapter( SubseaComponent ) :

  @trace( )
  def query( self, sql ) :

    return duckdb.query(
      sql
    ).df( )

'

write_py "${ROOT}/adapters/spark.py" '

from pyspark.sql import SparkSession

from Subsea.observability import SubseaComponent, trace


class SparkAdapter( SubseaComponent ) :

  def __init__( self ) :

    super( ).__init__()

    self.spark = SparkSession.builder.getOrCreate( )

  @trace( )
  def read_parquet( self, path ) :

    return self.spark.read.parquet(
      path
    )

'


echo 'Creating plotting interface...'
write_py "${ROOT}/plotting/__init__.py" '

'

write_py "${ROOT}/plotting/charts.py" '

import matplotlib.pyplot as plt

from Subsea.observability import SubseaComponent, trace


class ChartPlotter( SubseaComponent ) :

  @trace( )
  def histogram( self, values, title ) :

    self.step(
      "Plotting histogram"
    )

    plt.hist(
      values
    )

    plt.title(
      title
    )

    plt.show( )

'


echo 'Creating pipeline...'
write_py "${ROOT}/pipelines/__init__.py" '

'

write_py "${ROOT}/pipelines/image_pipeline.py" '

import cv2
import polars as pl

from Subsea.observability import SubseaComponent, trace
from Subsea.media.image import ImageSource
from Subsea.cv.blur import BlurDetector


class ImagePipeline( SubseaComponent ) :

  def __init__( self ) :

    super( ).__init__()

    self.blur = BlurDetector( )

  @trace( )
  def run( self, paths ) :

    rows = [ ]

    for path, img in ImageSource(
      paths
    ) :

      if img is None :

        self.log.warning(
          "Unreadable image %s" %
          path
        )

        continue

      gray = cv2.cvtColor(
        img,
        cv2.COLOR_BGR2GRAY
      )

      score = self.blur.score(
        gray
      )

      rows.append( {
        "path": str( path ),
        "blur_score": score
      } )

    return pl.DataFrame(
      rows
    )

'


echo 'Creating tests and enforcement...'
write_py "${ROOT}/tests/test_structure.py" '

import Subsea


def test_import( ) :

  assert Subsea is not None

'


echo 'Creating entrypoint...'
write_py "${ROOT}/__main__.py" '

from Subsea.logging import setup_logging
from Subsea.pipelines.image_pipeline import ImagePipeline


def main( ) :

  setup_logging( )

  pipeline = ImagePipeline( )

  pipeline.run( [ ] )


if __name__ == "__main__" :

  main( )

'

echo 'Subsea environment initialized with adapters, interfaces, and enforcement.'
