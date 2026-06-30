#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: set tabstop=2 shiftwidth=2 softtabstop=2 expandtab:

from __future__ import annotations

import sys
import os
from collections import deque
from typing import Optional

from rich.console import Console, Group
from rich.panel import Panel
from rich.live import Live


# =====================================================================
# OutputRouter
# =====================================================================

class OutputRouter:
  """
  Adaptive output router.

  Chooses the correct backend automatically depending on the runtime
  environment (script, CI, REPL, Jupyter, pipe).

  Public API:
    - emit(text): application output (stdout semantic)
    - observe(event): observer events
  """

  def __init__(self) -> None:
    mode = self._detect_environment()

    if mode == "live":
      self._backend = _LivePanelBackend()
    elif mode == "repl":
      self._backend = _SnapshotBackend()
    else:
      self._backend = _PlainStdoutBackend()

  # -------------------------------------------------------------------
  # Public API
  # -------------------------------------------------------------------

  def emit(self, text: str) -> None:
    self._backend.emit(text)

  def observe(self, event: dict) -> None:
    self._backend.observe(event)

  # -------------------------------------------------------------------
  # Environment detection (ENCAPSULATED)
  # -------------------------------------------------------------------

  @staticmethod
  def _detect_environment() -> str:
    """
    Detect execution environment.

    Returns:
      - "live"   : script / CI / TTY with cursor control
      - "repl"   : Python REPL, IPython, Jupyter
      - "stdout" : pipe / redirect / non-interactive
    """
    # --- Jupyter / IPython ---
    try:
      from IPython import get_ipython
      if get_ipython() is not None:
        return "repl"
    except Exception:
      pass

    # --- Python REPL ---
    if hasattr(sys, "ps1") or sys.flags.interactive:
      return "repl"

    # --- Non-interactive output ---
    if not sys.stdout.isatty():
      return "stdout"

    # --- CI (still allow Live) ---
    if os.environ.get("CI", "").lower() == "true":
      return "live"

    # --- Default: script / tty ---
    return "live"


# =====================================================================
# Backend base (internal)
# =====================================================================

class _BaseBackend:
  def emit(self, text: str) -> None:
    raise NotImplementedError

  def observe(self, event: dict) -> None:
    raise NotImplementedError

class StdoutRedirector:
  def __init__(self, backend):
    self.backend = backend
    self._buffer = ""

  def write(self, text):
    self._buffer += text
    while "\n" in self._buffer:
      line, self._buffer = self._buffer.split("\n", 1)
      self.backend.emit(line)

  def flush(self):
    if self._buffer:
      self.backend.emit(self._buffer)
      self._buffer = ""
# =====================================================================
# Live backend (script / CI)
# =====================================================================

class _LivePanelBackend:
  def __init__(self, observer_height=8, output_height=15, refresh_per_second=10):
    self.console = Console(force_terminal=True)
    self._observer_lines = deque(maxlen=observer_height)
    self._output_lines = deque(maxlen=output_height)

    self._live = Live(
      self._render(),
      console=self.console,
      refresh_per_second=refresh_per_second,
      transient=False
    )
    self._live.start()
    self._live.update(self._render(), refresh=True)

  # emit one line
  def emit(self, text: str):
    if text.strip():
      self._output_lines.append(text.rstrip())
      self._live.update(self._render())

  # observe events
  def observe(self, event: dict):
    func = event.get("function", "")
    if not func or func.startswith("_"):
      return
    seq = event.get("seq")
    duration = event.get("duration", 0.0)
    self._observer_lines.append(f"[{seq}] RETURN {func} ({duration:.6f}s)")
    self._live.update(self._render())

  # render panels
  def _render(self):
    observer_panel = Panel(
      "\n".join(self._observer_lines),
      title="Observer",
      border_style="cyan",
      height=self._observer_lines.maxlen + 2
    )
    output_panel = Panel(
      "\n".join(self._output_lines),
      title="Terminal Output",
      border_style="white",
      height=self._output_lines.maxlen + 2
    )
    return Group(observer_panel, output_panel)


# =====================================================================
# Snapshot backend (REPL / Jupyter)
# =====================================================================

class _SnapshotBackend(_BaseBackend):
  """
  REPL-safe backend.

  - stdout preserved
  - Rich panel printed only ONCE
  - No cursor control
  """

  def __init__(
    self,
    observer_height: int = 6,
    output_height: int = 10,
  ) -> None:
    self.console = Console(force_terminal=True)

    self._observer_lines: deque[str] = deque(maxlen=observer_height)
    self._output_lines: deque[str] = deque(maxlen=output_height)

    self._printed = False

  # -------------------------------------------------------------------

  def emit(self, text: str) -> None:
    if text.strip():
      self._output_lines.append(text.rstrip())
      # stdout semantics preserved
      print(text)

  def observe(self, event: dict) -> None:
    if event.get("type") != "return":
      return

    func = event.get("function", "")
    if func.split(".")[-1].startswith("_"):
      return

    seq = event.get("seq")
    duration = event.get("duration", 0.0)

    self._observer_lines.append(
      f"[{seq}] RETURN {func} ({duration:.6f}s)"
    )

    # Print snapshot only once
    if not self._printed:
      self.console.print(self._render())
      self._printed = True

  # -------------------------------------------------------------------

  def _render(self) -> Group:
    observer_panel = Panel(
      "\n".join(self._observer_lines),
      title="Observer",
      border_style="cyan",
    )

    output_panel = Panel(
      "\n".join(self._output_lines),
      title="Terminal Output",
      border_style="white",
    )

    return Group(observer_panel, output_panel)


# =====================================================================
# Plain stdout backend (pipes / redirect)
# =====================================================================

class _PlainStdoutBackend(_BaseBackend):
  """
  Fallback backend.

  - No Rich
  - Pure stdout
  """

  def emit(self, text: str) -> None:
    if text.strip():
      print(text)

  def observe(self, event: dict) -> None:
    # no observer output in plain stdout mode
    pass
