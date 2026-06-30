#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: set tabstop=2 shiftwidth=2 softtabstop=2 expandtab:


from typing import Type, Optional

from .base import SubseaBase


class PipelineMeta( type ) :
  '''
  Metaclass that registers the concrete Pipeline subclass.
  '''
  _active_pipeline : Optional[ Type[ 'Pipeline' ] ] = None

  def __init__( cls, name, bases, namespace ) :
    super( ).__init__( name, bases, namespace )

    # Ignore the base Pipeline class itself
    if cls.__name__ == 'Pipeline' :
      return

    # Register concrete pipeline
    PipelineMeta._active_pipeline = cls


class Pipeline( SubseaBase, metaclass = PipelineMeta ) :
  '''
  Base class for all Subsea pipelines.
  '''

  _active_instance = None

  def __init__(self, *args, **kwargs):
        Pipeline._active_instance = self
        super( ).__init__(
          *args,
          **kwargs
        )

  def run( self ) :
    raise NotImplementedError( 'Pipeline must implement run( )' )


def get_active_pipeline( ) -> Type[ 'Pipeline' ] :
  if PipelineMeta._active_pipeline is None :
    raise RuntimeError( 'No Subsea Pipeline defined' )

  return PipelineMeta._active_pipeline


