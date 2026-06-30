#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: set tabstop=2 shiftwidth=2 softtabstop=2 expandtab:


'''
S3 storage backend for Subsea.

Public API:
- S3Client
- S3ObjectStore
- S3ParallelLister
'''

from .client import S3Client
from .lister import S3ParallelLister as parallel_lister
from .store_facade import S3ObjectStoreFacade

client = S3Client
store = S3ObjectStoreFacade( S3Client )

__all__ = [
  'client',
  'store',
  'parallel_lister',
]
