#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: set tabstop=2 shiftwidth=2 softtabstop=2 expandtab:

from __future__ import annotations
from types import FrameType


# ---------------- DB ----------------

def detect_db(frame: FrameType) -> str | None:
    name = frame.f_code.co_name.lower()
    module = frame.f_globals.get("__name__", "").lower()

    if name in {"execute", "executemany"}:
        return "sql-execute"

    if "psycopg" in module or "sqlalchemy" in module:
        return "sql-driver"

    return None


# ---------------- FILE ----------------

def detect_file(frame: FrameType) -> str | None:
  name = frame.f_code.co_name
  module = frame.f_globals.get("__name__", "")

  if module.startswith("petrobras.core.ui"):
    return None

  if name in {"open", "read", "write"}:
    return "file-io"

  return None


# ---------------- AWS S3 ----------------

def detect_s3_download(frame: FrameType) -> dict | None:
    name = frame.f_code.co_name
    module = frame.f_globals.get("__name__", "")
    locals_ = frame.f_locals

    if "boto3" not in module:
        return None

    if name == "download_file":
        return {
            "provider": "aws-s3",
            "bucket": locals_.get("Bucket") or locals_.get("bucket"),
            "key": locals_.get("Key") or locals_.get("key"),
            "target": locals_.get("Filename") or locals_.get("filename"),
        }

    if name == "get_object":
        return {
            "provider": "aws-s3",
            "bucket": locals_.get("Bucket"),
            "key": locals_.get("Key"),
        }

    return None


# ---------------- GCS ----------------

def detect_gcs_download(frame: FrameType) -> dict | None:
    module = frame.f_globals.get("__name__", "")
    name = frame.f_code.co_name

    if "google.cloud.storage" not in module:
        return None

    blob = frame.f_locals.get("self")

    if name.startswith("download") and hasattr(blob, "name"):
        return {
            "provider": "gcs",
            "bucket": getattr(blob.bucket, "name", None),
            "object": blob.name,
        }

    return None
