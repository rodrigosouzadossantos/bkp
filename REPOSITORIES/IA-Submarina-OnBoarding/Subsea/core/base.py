#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: set tabstop=2 shiftwidth=2 softtabstop=2 expandtab:


import logging

from typing import (
  Dict,
  List,
  Iterator,
  Iterable,
  Optional,
)

from Subsea import (
  Error,
  CONFIG,
  STORAGE,
  CONSOLE,
)

from ..lib.media.image import Image
from ..lib.media.image_loader import ImageLoader

from .viewer import Viewer

from Subsea.observability.tracing import TracingPolicy


class SubseaBase :
  '''
  Base class providing shared Subsea services.
  '''

  IMAGE_EXTENSIONS = (
    '.jpg',
    '.jpeg',
    '.png',
    '.webp',
    '.tif',
    '.tiff',
  )

  def __init__(
    self,
    *,
    bucket : Optional[ str ] = None,
    prefix : Optional[ str ] = None,
    logger : Optional[ logging.Logger ] = None,
  ) :

    self.log = logger or logging.getLogger(
      self.__class__.__name__
    )

    self.tracing = TracingPolicy(
      name = self.__class__.__name__,
      logger = self.log,
    )

    if bucket is not None:
      self.bucket = bucket

    if prefix is not None:
      self.prefix = prefix

    self._base_initialized = True

    self._images : Optional[ dict ] = None
    self._objects : Optional[ List[ str ] ] = None

    self._models : Optional[ List[ str ] ] = None

    self._load_objects( )


  @property
  def bucket( self ) -> str:
    return (
      getattr( self, 'runtime_bucket', None ) or
      CONFIG.pipelines[ self.__class__.__name__ ].bucket
    )

  @bucket.setter
  def bucket(self, value: str):
    self.runtime_bucket = value

  @property
  def prefix( self ) -> str:
    return (
      getattr( self, 'runtime_prefix', None ) or
      CONFIG.pipelines[ self.__class__.__name__ ].prefix
    )

  @prefix.setter
  def prefix( self, value: str ) :
    self.runtime_prefix = value[ 1 : ] if value.startswith( '/' ) else value

  def s3_structure(
    self,
    uris : list[ str ],
  ) -> dict :

    tree : dict = { }

    for uri in uris:

      if not uri.startswith( 's3://' ):
        continue

      # remove scheme
      path = uri[ 5: ]

      # split parts
      parts = path.split( '/' )

      # prepend scheme as root
      parts = [ 's3' ] + parts

      node = tree

      for i, part in enumerate( parts ):

        is_last = i == len( parts ) - 1

        if is_last:
          # file
          node.setdefault( part, None )
        else:
          node = node.setdefault( part, { } )

    return tree


  def s3_keys(
    self,
    tree : dict,
  ) -> List[ str ] :

    '''
    Convert a nested S3 tree into storage keys.

    Returns:
      list of S3 object keys (WITHOUT bucket)
    '''

    keys : List[ str ] = [ ]

    if 's3' not in tree:
      raise ValueError( 'Tree root must contain "s3"' )

    for bucket, bucket_node in tree[ 's3' ].items( ) :

      def walk(
        node : dict,
        parts : list,
      ):

        for name, value in node.items( ) :

          if value is None:
            # file
            keys.append(
              '/'.join( parts + [ name ] )
            )

          elif isinstance( value, dict ):
            walk(
              value,
              parts + [ name ],
            )

      walk(
        bucket_node,
        [ ],
      )

    return keys


  def filter_tree(
    self,
    node : dict,
    extensions : tuple[ str, ... ] = None,
    *,
    invert : bool = False,
  ) -> dict :

    result = { }

    for key, value in node.items( ) :

      # -------------------------------
      # File
      # -------------------------------

      if not isinstance( value, dict ):

        matches = key.lower( ).endswith( extensions ) if extensions else True

        if matches ^ invert :
          result[ key ] = value


      # -------------------------------
      # Directory
      # -------------------------------

      elif isinstance( value, dict ):

        filtered = self.filter_tree(
          value,
          extensions,
          invert = invert,
        )

        if filtered:
          result[ key ] = filtered

    return result

  def _load_objects( self ) -> None :

    if self._objects is not None:
      return

    with self.tracing.operation(
      'Loading Objects',
      prefix = self.prefix,
    ) :

        self.log.info(
          f'Listing objects | bucket = { self.bucket } | prefix = { self.prefix }'
        )

        try :
          store = STORAGE.store(
            bucket = self.bucket
          )
        except Exception as e :
          raise Error( str( e ) ) from None;

        lister = STORAGE.parallel_lister(
          store = store,
          max_workers = 32,
        )

        keys = lister.list_objects(
          prefix = self.prefix,
        )

        self._objects = self.s3_structure( [
          f's3://{ self.bucket }/{ k }'
          for k in keys
        ] )

        self._images = self.filter_tree(
          self._objects,
          self.IMAGE_EXTENSIONS,
        )

        self._models = self.filter_tree(
          self._objects,
          ( '.pt', 'keras' ),
        )

        loader = ImageLoader( STORAGE )

        keys = self.s3_keys( self._images )
        images_list = loader.load_many( keys )

        image_map = {
          key: img
          for key, img in zip(
            keys,
            images_list,
          )
        }

        self.attach_images_to_tree(
          self._images,
          image_map,
        )


  def attach_images_to_tree(
    self,
    tree : Dict,
    images : Dict[ str, Image ],
  ) -> None :

    '''
    Mutates the tree in-place.

    Replaces:
      filename: None
    with:
      filename: Image

    Parameters
    ----------
    tree : dict
      Nested S3 tree.

    images : dict[str, Image]
      Mapping key -> Image,
      where key is the storage key
      (relative path, without bucket).
    '''

    if 's3' not in tree:
      raise ValueError(
        'Tree root must contain "s3"'
      )

    for bucket, bucket_node in tree[ 's3' ].items( ) :

      def walk(
        node : dict,
        parts : list,
      ):

        for name, value in list( node.items( ) ) :

          if value is None:

            key = '/'.join( parts + [ name ] )

            if key not in images:
              raise KeyError(
                f'Image not loaded for key: { key }'
              )

            node[ name ] = images[ key ]

          elif isinstance( value, dict ):

            walk(
              value,
              parts + [ name ],
            )

      walk(
        bucket_node,
        [ ],
      )

  
  @property
  def objects( self ) :
    return Viewer(
      f's3://{ self.bucket }/{ self.prefix }',
      self._objects,
      self.filter_tree
    )
  
  @property
  def models( self ) :
    return Viewer(
      f's3://{ self.bucket }/{ self.prefix }',
      self._models, self.filter_tree )
  
  @property
  def images( self ) :
    return Viewer(
      f's3://{ self.bucket }/{ self.prefix }',
      self._images, self.filter_tree )

  def test( self, path = 'test', count = 5 ) :
    def image_to_label_name( image_name : str ) -> str :
        return image_name.rsplit( '.' , 1 )[ 0 ] + '.txt'

    from ..lib.media.polygons.parsers.txt_polygon import TxtPolygonParser
    from ..lib.media.polygons.loader import PolygonLoader
    from ..lib.media.polygons.normalizer import PolygonNormalizer
    from ..lib.media.polygons.annotated_image import AnnotatedImage

    from io import BytesIO
    import cv2
    import numpy as np

    def load_image_from_storage(
        storage,
        bucket: str,
        key: str,
    ) -> np.ndarray:

        buf = BytesIO()

        storage.client(bucket).client.download_fileobj(
            bucket,
            key,
            buf,
        )

        data = np.frombuffer(
            buf.getvalue(),
            dtype=np.uint8,
        )

        img = cv2.imdecode(
            data,
            cv2.IMREAD_COLOR,
        )

        return img

    def load_text_from_storage(
        storage,
        bucket: str,
        key: str,
        encoding: str = 'utf-8',
    ) -> str:

        buf = BytesIO()

        storage.client(bucket).client.download_fileobj(
            bucket,
            key,
            buf,
        )

        return buf.getvalue().decode( encoding )


    from pathlib import PurePosixPath

    def image_path_to_s3_key(
        image_path : str | PurePosixPath ,
    ) -> str :

        p = str( image_path )

        prefix = '/projetos/ghva/'

        if p.startswith( prefix ):
            return p[ len( prefix ) : ]

        return p


    # --------------------------------------------------
    # Setup loader
    # --------------------------------------------------

    parser = TxtPolygonParser( )
    loader = PolygonLoader( parser, STORAGE, )

    # --------------------------------------------------
    # Test loop
    # --------------------------------------------------

    tested = 0
    errors = [ ]

    images = self.images( path = f'images/{path}' )
    labels = self.objects( path = f'labels/{path}' )

    for image_name , image in images.items( ) :

            label_name = image_to_label_name( image_name )

            if label_name not in labels :
                # No annotation for this image
                continue

        #try :

            # Load raw polygons
            raw_polygons = loader.load(
                f'{self.prefix}/labels/{path}/{label_name}'
            )

            # Normalize polygons using image shape
            H , W = image.numpy.shape[ : 2 ]

            polygons = PolygonNormalizer.normalize_many(
                raw_polygons ,
                image_height = H ,
                image_width  = W ,
            )

            ## Bind image + polygons
            #annotated = AnnotatedImage(
            #    image    = image ,
            #    polygons = polygons ,
            #)

            ## Render overlay (single test)
            #result = annotated.overlay(
            #    alpha = 0.3 ,
            #)

            # Optional: show first N only
            if tested < count :
              #display( result )
              #print( raw_polygons )
              #print( image.numpy.shape )
              #print( polygons )
              #print( '=============================' )

              bucket = 'analise-dados'
              image_key = image_path_to_s3_key( image.path )
              label_key = (
                  image_key
                  .replace( '/images/' , '/labels/' )
                  .rsplit( '.' , 1 )[ 0 ]
                  + '.txt'
              )
              print( 'IMAGE KEY:' , image_key )
              print( 'LABEL KEY:' , label_key )
              # --------------------------------------------------
              # Load raw data
              # --------------------------------------------------
              img = load_image_from_storage(
                  STORAGE,
                  bucket,
                  image_key,
              )
              label_text = load_text_from_storage(
                  STORAGE,
                  bucket,
                  label_key,
              )
              h, w = img.shape[:2]
              # --------------------------------------------------
              # Draw polygons exactly like the manual code
              # --------------------------------------------------
              for lineno, line in enumerate( label_text.splitlines(), start = 1 ):

                  line = line.strip()

                  if not line:
                      continue

                  parts = line.split()

                  if len( parts ) < 3:
                      continue

                  coords = list( map( float, parts[ 1: ] ) )

                  points = []

                  for i in range( 0, len( coords ), 2 ):
                      x = int( round( coords[ i ] * w ) )
                      y = int( round( coords[ i + 1 ] * h ) )
                      points.append( [ x, y ] )

                  pts = np.array( points, dtype = np.int32 )

                  cv2.polylines(
                      img,
                      [ pts ],
                      isClosed = True,
                      color = ( 0 , 0 , 255 ),
                      thickness = 2,
                  )

              #cv2.imshow( 'debug', img )
              #cv2.waitKey( 0 )

              display( Image(
                  array = img[ : , : , :: -1 ],  # BGR → RGB
                  path  = image.path,
              ) )

            else :
                break

            tested += 1

        #except Exception as e :

        #    errors.append(
        #        ( image_name , str( e ) )
        #    )

    # --------------------------------------------------
    # Summary
    # --------------------------------------------------

    print( f'Tested images: { tested }' )
    print( f'Errors: { len( errors ) }' )

    for name , err in errors[ : 5 ] :
        print( name , '->' , err )
