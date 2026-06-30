#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: set tabstop=2 shiftwidth=2 softtabstop=2 expandtab:


import os
import time
import logging

from typing import Optional, Iterable

import boto3
from botocore.config import Config
from botocore.exceptions import (
  ClientError,
  EndpointConnectionError,
  ConnectionClosedError,
)

from Subsea.observability.tracing import TracingPolicy



class S3Client :

  '''
  Robust S3 client abstraction.

  Responsibilities:
  - provide safe, retriable access to S3
  - support large file transfers (multipart)
  - expose explicit, predictable semantics

  This class is intentionally low-level.
  No business logic belongs here.
  '''

  def __init__(
    self,
    bucket : str,
    region : Optional[ str ] = None,
    access_key : Optional[ str ] = None,
    secret_key : Optional[ str ] = None,
    session_token : Optional[ str ] = None,
    endpoint_url : Optional[ str ] = None,
    max_connections : int = 32,
    max_attempts : int = 10,
    connect_timeout : int = 10,
    read_timeout : int = 120,
    logger : Optional[ logging.Logger ] = None,
  ) :

    self.bucket = bucket

    self.log = logger or logging.getLogger(
      f'S3Client[{bucket}]'
    )

    self.tracing = TracingPolicy(
      name = 'S3Client',
      logger = self.log,
    )

    self.config = Config(
      region_name = region,
      max_pool_connections = max_connections,
      retries = {
        'max_attempts': max_attempts,
        'mode': 'adaptive',
      },
      connect_timeout = connect_timeout,
      read_timeout = read_timeout,
    )

    self.session = boto3.session.Session(
      aws_access_key_id = access_key,
      aws_secret_access_key = secret_key,
      aws_session_token = session_token,
      region_name = region,
    )

    self.client = self.session.client(
      's3',
      config = self.config,
      endpoint_url = endpoint_url,
    )

    self.log.debug(
      'Initialized S3Client for bucket=%s region=%s',
      bucket,
      region,
    )


  def paginate_objects(
    self,
    prefix : str,
  ) :

    """
    Yield paginated S3 list_objects_v2 responses.

    This is the ONLY place that knows boto3 pagination.
    """

    paginator = self.client.get_paginator(
      'list_objects_v2'
    )

    for page in paginator.paginate(
      Bucket = self.bucket,
      Prefix = prefix,
    ) :

      yield page


  def exists( self, key : str ) -> bool :

    '''
    Check if an object exists without downloading it.
    '''

    try :

      self.client.head_object(
        Bucket = self.bucket,
        Key = key,
      )

      return True

    except ClientError as e :

      code = e.response.get(
        'Error',
        { }
      ).get(
        'Code'
      )

      if code in ( '404', 'NoSuchKey' ) :
        return False

      raise


  def download(
    self,
    key : str,
    dest_path : str,
    overwrite : bool = False,
  ) -> None :

    '''
    Download an object to a local file.

    Uses boto3 high-level transfer manager,
    which automatically handles multipart downloads.
    '''

    with self.tracing.operation(
      'download',
      key = key,
      dest = dest_path,
    ) :
      if os.path.exists( dest_path ) and not overwrite :

        self.log.debug(
          'Skipping download, file exists: %s',
          dest_path,
        )

        return

      os.makedirs(
        os.path.dirname( dest_path ) or '.',
        exist_ok = True,
      )

      self.log.info(
        'Downloading s3://%s/%s -> %s',
        self.bucket,
        key,
        dest_path,
      )

      try :

        self.client.download_file(
          self.bucket,
          key,
          dest_path,
        )

      except (
        EndpointConnectionError,
        ConnectionClosedError,
      ) as e :

        self.log.error(
          'Network error downloading %s: %s',
          key,
          e,
        )

        raise


  def upload(
    self,
    src_path : str,
    key : str,
    content_type : Optional[ str ] = None,
    extra_args : Optional[ dict ] = None,
  ) -> None :

    '''
    Upload a local file to S3.

    Automatically uses multipart uploads for large files.
    '''

    with self.tracing.operation(
      'upload',
      src = src_path,
      key = key,
      content_type = content_type,
    ) :
      if not os.path.exists( src_path ) :
        raise FileNotFoundError( src_path )

      args = extra_args.copy( ) if extra_args else {}

      if content_type :
        args[ 'ContentType' ] = content_type

      self.log.info(
        'Uploading %s -> s3://%s/%s',
        src_path,
        self.bucket,
        key,
      )

      try :

        self.client.upload_file(
          src_path,
          self.bucket,
          key,
          ExtraArgs = args or None,
        )

      except ClientError as e :

        self.log.error(
          'Upload failed %s -> %s: %s',
          src_path,
          key,
          e,
        )

        raise


  def stream(
    self,
    key : str,
    chunk_size : int = 8 * 1024 * 1024,
  ) -> Iterable[ bytes ] :

    '''
    Stream an object in chunks.

    Useful for very large files or
    when piping data into another process.
    '''

    def generator( ) :

      with self.tracing.operation(
        'stream',
        key = key,
        chunk_size = chunk_size,
      ) :

        self.log.info(
          'Streaming s3://%s/%s',
          self.bucket,
          key,
        )

        try :

          response = self.client.get_object(
            Bucket = self.bucket,
            Key = key,
          )

          body = response[ 'Body' ]

          while True :

            chunk = body.read( chunk_size )

            if not chunk :
              break

            yield chunk

        except ClientError as e :

          self.log.error(
            'Failed streaming %s: %s',
            key,
            e,
          )

          raise

    return generator( )


  def list(
    self,
    prefix : str = '',
    suffix : Optional[ str ] = None,
  ) -> Iterable[ str ] :

    '''
    Iterate over object keys in the bucket.
    '''
  def generator( ) :

    with self.tracing.operation(
      'list',
      prefix = prefix,
      suffix = suffix,
    ) :

      paginator = self.client.get_paginator(
        'list_objects_v2'
      )

      for page in paginator.paginate(
        Bucket = self.bucket,
        Prefix = prefix,
      ) :

        for obj in page.get( 'Contents', [ ] ) :

          key = obj[ 'Key' ]

          if suffix and not key.endswith( suffix ) :
            continue

          yield key

    return generator( )


  def delete(
    self,
    key : str,
    version_id : str | None = None,
  ) -> None :

    with self.tracing.operation(
      'delete',
      key = key,
      version_id = version_id,
    ) :

      self.log.info(
        'Deleting s3://%s/%s%s',
        self.bucket,
        key,
        f' version={version_id}' if version_id else ' (latest)',
      )

      params = {
        'Bucket': self.bucket,
        'Key': key,
      }

      if version_id :
        params[ 'VersionId' ] = version_id

      try :

        self.client.delete_object(
          **params
        )

      except ClientError as e :

        if (
          e.response
            .get( 'Error', {} )
            .get( 'Code' )
          == 'NoSuchKey'
        ) :

          self.log.warning(
            'Object already deleted: %s version=%s',
            key,
            version_id,
          )

          return

        raise


  def wait_until_exists(
    self,
    key : str,
    timeout : int = 60,
    poll_interval : float = 1.0,
  ) -> bool :

    '''
    Wait until an object appears in S3.

    Useful for synchronization between producers/consumers.
    '''

    deadline = time.time( ) + timeout

    while time.time( ) < deadline :

      if self.exists( key ) :
        return True

      time.sleep( poll_interval )

    return False

