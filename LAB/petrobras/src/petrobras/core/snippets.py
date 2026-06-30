#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: set tabstop=2 shiftwidth=2 softtabstop=2 expandtab:

from __future__ import annotations
import linecache
from types import FrameType


def get_snippet(frame: FrameType, context: int = 2) -> str:
    filename = frame.f_code.co_filename
    lineno = frame.f_lineno

    start = max(1, lineno - context)
    end = lineno + context

    lines: list[str] = []
    for i in range(start, end + 1):
        line = linecache.getline(filename, i)
        if not line:
            continue
        prefix = "➜" if i == lineno else " "
        lines.append(f"{prefix} {i:4d} | {line.rstrip()}")

    return "\n".join(lines)


