#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: set tabstop=2 shiftwidth=2 softtabstop=2 expandtab:



from Subsea.logging import SubseaLogger
from Subsea.pipelines.image_pipeline import ImagePipeline

def main( ) :

  SubseaLogger.setup( )

  pipeline = ImagePipeline( )

  df = pipeline.run( [ ] )

  print( df )

if __name__ == '__main__' :

  main( )


