#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: set tabstop=2 shiftwidth=2 softtabstop=2 expandtab:





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


