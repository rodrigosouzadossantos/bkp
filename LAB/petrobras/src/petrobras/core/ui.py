#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: set tabstop=2 shiftwidth=2 softtabstop=2 expandtab:

from __future__ import annotations

import sys
from collections import deque
from rich.console import Console, Group
from rich.panel import Panel
from rich.layout import Layout
from rich.live import Live
from rich.text import Text


# ---------------------------------------------------------------------
# CONFIG
# ---------------------------------------------------------------------

MAX_EVENTS = 120
MAX_OUTPUT = 200

_console = Console()

_events: deque[str] = deque(maxlen=MAX_EVENTS)
_output: deque[str] = deque(maxlen=MAX_OUTPUT)

_live: Live | None = None
_layout: Layout | None = None
_original_stdout = sys.stdout


# ---------------------------------------------------------------------
# STDOUT INTERCEPTOR
# ---------------------------------------------------------------------

class StdoutProxy:
  def write(self, text: str) -> None:
    if text.strip():
      _output.append(text.rstrip("\n"))
      _refresh()

  def flush(self) -> None:
    pass


# ---------------------------------------------------------------------
# LAYOUT
# ---------------------------------------------------------------------

def _make_layout() -> Layout:
  layout = Layout()

  layout.split_column(
    Layout(name="observer", ratio=3),
    Layout(name="execution", ratio=2),
  )

  return layout


def _render_observer() -> Panel:
  body = Group(*(Text(line) for line in _events))
  return Panel(
    body,
    title="Petrobras Observer",
    border_style="cyan",
  )


def _render_execution() -> Panel:
  body = Group(*(Text(line) for line in _output))
  return Panel(
    body,
    title="Execution",
    border_style="green",
  )


def _refresh() -> None:
  if _layout:
    _layout["observer"].update(_render_observer())
    _layout["execution"].update(_render_execution())


# ---------------------------------------------------------------------
# PUBLIC API
# ---------------------------------------------------------------------

def start_ui() -> None:
  global _live, _layout

  if _live:
    return

  _layout = _make_layout()
  _layout["observer"].update(_render_observer())
  _layout["execution"].update(_render_execution())

  # redirect stdout BEFORE Live starts
  sys.stdout = StdoutProxy()

  _live = Live(
    _layout,
    console=_console,
    refresh_per_second=10,
    transient=False,
  )
  _live.start()


def emit(message: str) -> None:
  _events.append(message)
  _refresh()


def shutdown_ui() -> None:
  global _live

  sys.stdout = _original_stdout

  if _live:
    _live.stop()
    _live = None
