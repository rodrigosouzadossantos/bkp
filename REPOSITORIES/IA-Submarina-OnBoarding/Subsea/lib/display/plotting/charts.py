#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: set tabstop=2 shiftwidth=2 softtabstop=2 expandtab:





import matplotlib.pyplot as plt

from Subsea.observability import SubseaComponent, trace


class ChartPlotter( SubseaComponent ) :

  @trace( )
  def histogram( self, values, title ) :

    self.step(
      "Plotting histogram"
    )

    plt.hist(
      values
    )

    plt.title(
      title
    )

    plt.show( )


