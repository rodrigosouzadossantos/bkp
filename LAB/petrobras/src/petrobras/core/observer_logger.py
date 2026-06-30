#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: set tabstop=2 shiftwidth=2 softtabstop=2 expandtab:

from __future__ import annotations

import logging
from typing import Iterable


class ObserverLogger:
  """
  Consume Observer events and emit logs.

  Responsibilities:
    - translate structured events into log lines
    - decide log level per event type

  Support:
    - seq (global event counter)
    - call_id (UUID per invocation)
  """

  def __init__(self, logger: logging.Logger | None = None) -> None:
    self.logger = logger or logging.getLogger("observer")

  # -------------------------------------------------
  # Public API
  # -------------------------------------------------

  def log_events(self, events: Iterable[dict]) -> None:
    for event in events:
      self._log_event(event)

  def handle_event(self, event: dict) -> None:
    self._log_event(event)

  # -------------------------------------------------
  # Internal
  # -------------------------------------------------

  def _log_event(self, event: dict) -> None:
    etype = event.get("type")
    seq = event.get("seq")
    call_id = event.get("call_id")

    prefix = f"[seq={seq} id={call_id}]"

    if etype == "call":
      self._log_call(prefix, event)

    elif etype == "return":
      self._log_return(prefix, event)

    elif etype == "exception":
      self._log_exception(prefix, event)

    else:
      self.logger.debug("%s Unknown event: %r", prefix, event)

  def _log_call(self, prefix: str, event: dict) -> None:
    func = event.get("function")
    args = event.get("args", {})
    self.logger.debug(
      "%s CALL %s args=%s",
      prefix,
      func,
      args,
    )

  def _log_return(self, prefix: str, event: dict) -> None:
    func = event.get("function")
    value = event.get("return")
    duration = event.get("duration")

    if duration is not None:
      self.logger.info(
        "%s RETURN %s -> %r (%.6fs)",
        prefix,
        func,
        value,
        duration,
      )
    else:
      self.logger.info(
        "%s RETURN %s -> %r",
        prefix,
        func,
        value,
      )

  def _log_exception(self, prefix: str, event: dict) -> None:
    func = event.get("function")
    exc_type, exc_value = event.get("exception", (None, None))
    duration = event.get("duration")

    if duration is not None:
      self.logger.error(
        "%s EXCEPTION %s %s: %r (%.6fs)",
        prefix,
        func,
        getattr(exc_type, "__name__", exc_type),
        exc_value,
        duration,
      )
    else:
      self.logger.error(
        "%s EXCEPTION %s %s: %r",
        prefix,
        func,
        getattr(exc_type, "__name__", exc_type),
        exc_value,
      )
