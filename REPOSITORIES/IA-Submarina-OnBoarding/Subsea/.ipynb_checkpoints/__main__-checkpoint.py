#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: set tabstop=2 shiftwidth=2 softtabstop=2 expandtab:


import logging

from Subsea.config import CONFIG 
from Subsea.logging import setup_logging
from Subsea.pipelines.image_pipeline import ImagePipeline

from Subsea.storage.adapters.s3_client import S3Client
from Subsea.storage.local_store import LocalObjectStore
from Subsea.storage.s3_store import S3ObjectStore
from Subsea.storage.s3_lister import S3ParallelLister


def main( ) :

  setup_logging( )

  s3_client = S3Client(
    bucket = 'analise-dados',
    region = 'us-east-1',
  )

  store = S3ObjectStore(
    client = s3_client,
  )

  lister = S3ParallelLister(
    store = store,
    max_workers = 32,
  )

  store = LocalObjectStore(
    root = CONFIG.DATA_DIR
  )

  pipeline = ImagePipeline(
    store = store,
    lister = lister,
    bucket_name = 'analise-dados',
  )

  table = pipeline.run( )

if __name__ == '__main__' :

  main( )


