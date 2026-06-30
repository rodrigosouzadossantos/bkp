#!/usr/bin/env bash

set -e

HEADER='#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: set tabstop=2 shiftwidth=2 softtabstop=2 expandtab:


'

echo 'Prepending Python header where missing...'

find . -type f -name "*.py" | while read -r file ; do

  # Skip virtual environments and caches
  case "$file" in
    */.venv/*|*/venv/*|*/__pycache__/*)
      continue
      ;;
  esac

  # Check if file already has the shebang
  if head -n 1 "$file" | grep -q '^#!/usr/bin/env python3' ; then
    echo "Skipping (header exists): $file"
    continue
  fi

  echo "Updating: $file"

  tmp="$(mktemp)"

  {
    printf "%s\n" "$HEADER"
    cat "$file"
  } > "$tmp"

  mv "$tmp" "$file"

done

echo 'Header prepended successfully.'
