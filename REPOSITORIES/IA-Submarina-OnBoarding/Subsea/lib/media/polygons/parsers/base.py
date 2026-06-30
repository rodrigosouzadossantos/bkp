#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: set tabstop=2 shiftwidth=2 softtabstop=2 expandtab:


from abc import ABC , abstractmethod
from typing import Iterable , Tuple


class AnnotationParser( ABC ) :

    '''
    Interface for annotation parsers.

    Parsers only extract raw data.
    No normalization, no geometry logic.
    '''

    @abstractmethod
    def parse(
        self ,
        raw : str ,
    ) -> Iterable[ Tuple[ int , list[ Tuple[ float , float ] ] ] ] :

        '''
        Returns:
          iterable of ( label , [ ( x , y ) , ... ] )
        '''

        pass

