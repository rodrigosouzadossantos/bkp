#!/usr/bin/env bash
set -euo pipefail

echo "🔍 Searching for virtualenv site-packages..."

find . -type d -path "*/.venv/lib/*/site-packages" | while read -r SITE; do
  TARGET="$SITE/sitecustomize.py"

  echo "➡️  Processing: $TARGET"

  # Backup if file already exists
  if [ -f "$TARGET" ]; then
    echo "   📌 Existing sitecustomize.py found, backing up"
    cp "$TARGET" "$TARGET.bak.$(date +%s)"
  fi

  cat > "$TARGET" << 'EOF'
# sitecustomize.py
# Injected by PECI-RT (Nautilus-RT)
# Loads import guard before any application code

import sys

try:
    from nautilus_rt.nemo import Nemo
    sys.meta_path.insert(0, Nemo("nautilus_rt"))
except Exception:
    # Never break Python startup
    pass
EOF

  echo "   ✅ Installed sitecustomize.py"
done

echo "🎉 Injection completed."
