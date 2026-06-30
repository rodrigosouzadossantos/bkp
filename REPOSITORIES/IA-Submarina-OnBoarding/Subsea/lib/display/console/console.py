#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: set tabstop=2 shiftwidth=2 softtabstop=2 expandtab:


from rich.console import Console
from rich import pretty

# --------------------------------------------------
# Single global console instance
# --------------------------------------------------

console = Console( )

# --------------------------------------------------
# Enable rich pretty-print globally
# --------------------------------------------------

pretty.install( )

__all__ = [ 'console' ]

