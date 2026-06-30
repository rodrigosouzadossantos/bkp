#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: set tabstop=2 shiftwidth=2 softtabstop=2 expandtab:


from __future__ import annotations

import sys
import atexit
from collections import deque

from rich.console import Console, Group
from rich.panel import Panel
from rich.live import Live


class ObserverUI:
  """
  Observer UI following the CI/build-tool pattern.

  - One Live
  - Explicit buffers
  - live.update() drives ALL output
  - No stdout / print / proxy
  """

  def __init__(
    self,
    observer_height: int = 8,
    output_height: int = 15,
    refresh_per_second: int = 10,
  ) -> None:
    self.console = Console(force_terminal=True)

    self._observer_lines: deque[str] = deque(maxlen=observer_height)
    self._output_lines: deque[str] = deque(maxlen=output_height)

    self._live = None
    self._refresh_per_second = refresh_per_second

    self._printed_once = False

    if not self._in_repl():
      self._live = Live(
        self._render(),
        console=self.console,
        refresh_per_second=refresh_per_second,
        transient=False,
      )
      self._live.start()

    atexit.register(self._shutdown)

  @staticmethod
  def _in_repl() -> bool:
    return hasattr(sys, "ps1") or sys.flags.interactive

  # -------------------------------------------------
  # Observer subscriber
  # -------------------------------------------------

  def handle_event(self, event: dict) -> None:
    if event.get("type") != "return":
      return

    line = self._format_event(event)
    self._observer_lines.append(line)

    if self._live:
      self._live.update(self._render())
    else:
      if not self._printed_once:
        self.console.print(self._render())
        self._printed_once = True

  # -------------------------------------------------
  # Application output API (REPL / run())
  # -------------------------------------------------

  def emit_output(self, text: str) -> None:
    if text.strip():
      self._output_lines.append(text.rstrip())

      if self._live:
        self._live.update(self._render())
      else:
        if not self._printed_once:
          self.console.print(self._render())
          self._printed_once = True

  # -------------------------------------------------
  # Rendering
  # -------------------------------------------------

  def _render(self) -> Group:
    observer_panel = Panel(
      "\n".join(self._observer_lines),
      title="Observer",
      border_style="cyan",
      height=self._observer_lines.maxlen,
    )

    output_panel = Panel(
      "\n".join(self._output_lines),
      title="Terminal Output",
      border_style="white",
      height=self._output_lines.maxlen,
    )

    return Group(observer_panel, output_panel)

  # -------------------------------------------------
  # Formatting
  # -------------------------------------------------

  def _format_event(self, event: dict) -> str:
    seq = event.get("seq")
    func = event.get("function")
    duration = event.get("duration", 0.0)
    return f"[{seq}] RETURN {func} ({duration:.6f}s)"

  # -------------------------------------------------
  # Shutdown
  # -------------------------------------------------

  def _shutdown(self) -> None:
    if self._live:
      self._live.stop()
