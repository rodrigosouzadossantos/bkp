#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: set tabstop=2 shiftwidth=2 softtabstop=2 expandtab:

from __future__ import annotations

import sys
import time
import uuid
import threading
from collections import deque
from types import FrameType
from typing import Callable, Optional

from .singleton import Singleton


class Observer(metaclass=Singleton):
  """
  Execution observer with:
    - CALL / RETURN / EXCEPTION
    - internal event buffer
    - latency measurement
    - sequential event counter (seq)
    - UUID per invocation (call_id)
  """

  def __init__(self, namespace: str, max_events: int = 1000) -> None:
    # Singleton guard
    if hasattr(self, "_initialized"):
      return

    self.namespace = namespace
    self._installed = False

    self._events: deque[dict] = deque(maxlen=max_events)

    # active calls indexed by frame id
    self._active_calls: dict[int, float] = {}
    self._call_ids: dict[int, uuid.UUID] = {}

    # counters
    self._seq = 0

    self._lock = threading.Lock()
    self._initialized = True

    self._subscribers: list[callable] = []

  # -------------------------------------------------
  # Public API
  # -------------------------------------------------

  def install(self) -> None:
    if self._installed:
      return

    self._installed = True
    sys.settrace(self._trace)
    threading.settrace(self._trace)

  def uninstall(self) -> None:
    if not self._installed:
      return

    self._installed = False
    sys.settrace(None)
    threading.settrace(None)

  def clear(self) -> None:
    with self._lock:
      self._events.clear()
      self._active_calls.clear()
      self._call_ids.clear()
      self._seq = 0

  def get_events(self) -> list[dict]:
    with self._lock:
      return list(self._events)

  def subscribe(self, callback) -> None:
    with self._lock:
      self._subscribers.append(callback)

  def unsubscribe(self, callback) -> None:
    with self._lock:
      if callback in self._subscribers:
        self._subscribers.remove(callback)

  # -------------------------------------------------
  # Trace dispatcher
  # -------------------------------------------------

  def _trace(
    self,
    frame: FrameType,
    event: str,
    arg,
  ) -> Optional[Callable]:

    try:
      module = frame.f_globals.get("__name__")
      func_name = frame.f_code.co_name
      #if not isinstance(module, str):
      #  return self._trace

      if not (
        module == self.namespace
        or module.startswith(self.namespace + ".")
      ):
        return self._trace

      if module.startswith((
        "petrobras.singleton",
        "petrobras.core.observer",
        "petrobras.core.observer_logger",
        "petrobras.core.observer_ui",
        "petrobras.StdoutProxy",
        "logging",
        "rich",
      )):
        return self._trace

      if func_name in ("write", "flush"):
        return self._trace

      if func_name.startswith("_"):
        return self._trace

      if not (
        module == self.namespace
        or module.startswith(self.namespace + ".")
      ):
        return self._trace

    except Exception:
      return self._trace

    if event == "call":
      self._handle_call(frame)

    elif event == "return":
      self._handle_return(frame, arg)

    elif event == "exception":
      exc_type, exc_value, _ = arg
      self._handle_exception(frame, exc_type, exc_value)

    return self._trace

  # -------------------------------------------------
  # Internal handlers
  # -------------------------------------------------

  def _next_seq(self) -> int:
    with self._lock:
      self._seq += 1
      return self._seq

  def _emit(self, event: dict) -> None:
    with self._lock:
      self._events.append(event)
      subscribers = list(self._subscribers)

    # notify outside lock
    for callback in subscribers:
      try:
        callback(event)
      except Exception:
        pass

  def _handle_call(self, frame: FrameType) -> None:
    now = time.perf_counter()
    frame_id = id(frame)
    call_id = uuid.uuid4()
    seq = self._next_seq()

    event = {
      "seq": seq,
      "type": "call",
      "call_id": call_id,
      "function": self.get_function_name(frame),
      "args": self.get_arguments(frame),
      "timestamp": now,
    }

    with self._lock:
      self._active_calls[frame_id] = now
      self._call_ids[frame_id] = call_id
      self._events.append(event)

    self._emit(event)

  def _handle_return(self, frame: FrameType, value) -> None:
    now = time.perf_counter()
    frame_id = id(frame)
    seq = self._next_seq()

    with self._lock:
      start = self._active_calls.pop(frame_id, None)
      call_id = self._call_ids.pop(frame_id, None)

    duration = now - start if start is not None else None

    event = {
      "seq": seq,
      "type": "return",
      "call_id": call_id,
      "function": self.get_function_name(frame),
      "return": value,
      "timestamp": now,
      "duration": duration,
    }

    with self._lock:
      self._events.append(event)

    self._emit(event)

  def _handle_exception(
    self,
    frame: FrameType,
    exc_type: type[BaseException],
    exc_value: BaseException,
  ) -> None:
    now = time.perf_counter()
    frame_id = id(frame)
    seq = self._next_seq()

    with self._lock:
      start = self._active_calls.pop(frame_id, None)
      call_id = self._call_ids.pop(frame_id, None)

    duration = now - start if start is not None else None

    event = {
      "seq": seq,
      "type": "exception",
      "call_id": call_id,
      "function": self.get_function_name(frame),
      "exception": (exc_type, exc_value),
      "timestamp": now,
      "duration": duration,
    }

    self._emit(event)

    with self._lock:
      self._events.append(event)

  # -------------------------------------------------
  # Helpers
  # -------------------------------------------------

  def get_function_name(self, frame: FrameType) -> str:
    module = frame.f_globals.get("__name__", "<unknown>")
    name = frame.f_code.co_name
    return f"{module}.{name}"

  def get_arguments(self, frame: FrameType) -> dict[str, object]:
    return dict(frame.f_locals)
