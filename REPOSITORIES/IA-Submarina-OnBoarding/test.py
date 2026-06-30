#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: set tabstop=2 shiftwidth=2 softtabstop=2 expandtab:


from typing import Optional

import Subsea


class Corals( Subsea.Pipeline ) :

  def __init__(
    self,
    *,
    bucket : Optional[ str ] = None,
    prefix : Optional[ str ] = None,
  ) :

    super( ).__init__(
      bucket = bucket,
      prefix = prefix
        if prefix and prefix.startswith( '/' )
          else f'{self.prefix}/{prefix}'
            if prefix else None
    )



  def run( self ) :
    #print( self.prefix )
    #self.models( )
    print( self.images( render = True, show_files = True ) )

corals = Corals( prefix = 'Datasets/coral_images_lote_comOverlayRevisado' )
#corals = Corals( prefix = '/Datasets/coral_images_lote_comOverlayRevisado' )
#corals = Corals( )
#corals.models( )
#corals.images( render = True, show_files = False )
#corals.objects(
#  #path = 'test',
#  show_files = False,
#  render = True
#)

corals.test( 'test', 5 )

#Subsea.run( )
