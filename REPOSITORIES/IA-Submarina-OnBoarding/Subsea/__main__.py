#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: set tabstop=2 shiftwidth=2 softtabstop=2 expandtab:


import logging

#from Subsea.logging import setup_logging
from Subsea.storage import LocalObjectStore

from Subsea import CONFIG 
from Subsea import STORAGE

from Subsea.pipelines.image_pipeline import ImagePipeline

#import Subsea.pipelines.tubastraea as tuba 
from Subsea.pipelines.corals import Corals



def __main( ) :
  corals = Corals(
    bucket = 'analise-dados',
    prefix = 'projeto-ia-submarina/ia-frente-ambiental/',
  )

  corals.models( )


def main( ) :

  #setup_logging( )

  store = LocalObjectStore(
    root = CONFIG.paths.data_dir
  )

  pipeline = ImagePipeline(
    store = store,
    lister = STORAGE.parallel_lister(
      store = STORAGE.store(
        client = STORAGE.client(
          bucket = 'analise-dados',
          region = 'us-east-1',
        ),
      ),
      max_workers = 32,
    ),
    bucket_name = 'analise-dados',
  )

  table = pipeline.run( 'projeto-ia-submarina/ia-frente-ambiental/' )

#import multiprocessing as mp
if __name__ == '__main__' :

  #mp.set_start_method("spawn", force=True)
  main( )
