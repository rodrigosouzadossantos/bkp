#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: set tabstop=2 shiftwidth=2 softtabstop=2 expandtab:


from dataclasses import dataclass

import numpy as np


@dataclass( frozen = True )
class RawPolygon :

    '''
    Polygon annotation as loaded from file.

    - points may be normalized ( 0 – 1 )
    - or pixel based
    '''

    label : int
    points : np.ndarray # shape ( N , 2 ) , float
    normalized : bool

