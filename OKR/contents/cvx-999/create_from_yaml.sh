#!/usr/bin/env bash
set -euo pipefail

########################################
# File Content Generators by Type
########################################

create_py() {
  local file="$1"
  cat > "$file" <<EOF
# -*- coding: utf-8 -*-
\"\"\"
Auto-generated Python module: $(basename "$file")
\"\"\"

__all__ : list[str] = [
]
EOF
}

create_json() {
  local file="$1"
  cat > "$file" <<EOF
{
  "generated": true
}
EOF
}

create_yaml_file() {
  local file="$1"
  cat > "$file" <<EOF
# Auto-generated YAML
generated: true
EOF
}

create_md() {
  local file="$1"
  cat > "$file" <<EOF
# $(basename "$file" .md)

Auto-generated documentation.
EOF
}

create_txt() {
  local file="$1"
  echo "Auto-generated file: $(basename "$file")" > "$file"
}

########################################
# File Dispatcher (by extension)
########################################

create_file_by_type() {
  local file="$1"

  if [[ "$file" != *.* ]]; then
    touch "$file"
    return
  fi

  local ext="${file##*.}"
  ext="$(echo "$ext" | tr '[:upper:]' '[:lower:]')"
  local fn="create_${ext}"

  if declare -f "$fn" > /dev/null 2>&1; then
    "$fn" "$file"
  else
    touch "$file"
  fi
}

########################################
# YAML Parser + Creator
########################################

create_from_yaml() {
  local root="${1:-.}"

  mkdir -p "$root"

  local current_path=""
  local indent_stack=()

  while IFS= read -r line; do

    [[ -z "$line" || "$line" =~ ^# ]] && continue

    # Count indentation (2 spaces)
    local indent="${line%%[^ ]*}"
    local level=$(( ${#indent} / 2 ))
    local trimmed="${line#"${indent}"}"

    # Adjust path stack
    indent_stack=("${indent_stack[@]:0:$level}")

    if [[ "$trimmed" =~ ^- ]]; then
      # File
      local filename="${trimmed#- }"
      local dir_path="$root"
      for part in "${indent_stack[@]}"; do
        dir_path="$dir_path/$part"
      done

      mkdir -p "$dir_path"
      create_file_by_type "$dir_path/$filename"

    elif [[ "$trimmed" =~ :[[:space:]]*NULL$ ]]; then
      # Empty directory
      local dirname="${trimmed%%:*}"
      indent_stack[$level]="$dirname"

      local dir_path="$root"
      for part in "${indent_stack[@]}"; do
        dir_path="$dir_path/$part"
      done

      mkdir -p "$dir_path"

    elif [[ "$trimmed" =~ :$ ]]; then
      # Directory with children
      local dirname="${trimmed%%:*}"
      indent_stack[$level]="$dirname"

      local dir_path="$root"
      for part in "${indent_stack[@]}"; do
        dir_path="$dir_path/$part"
      done

      mkdir -p "$dir_path"
    fi

  done
}

########################################
# Usage
########################################

# Example:
# cat structure.yaml | create_from_yaml ./output_project
