#!/usr/bin/env bash
# Sourceable dependency checker.
# Usage: source scripts/require.sh && require vault "https://developer.hashicorp.com/vault/install"

install_hint() {
  local bin="$1" doc_url="$2"
  if command -v brew >/dev/null 2>&1; then
    echo "brew install $bin"
  elif command -v apt-get >/dev/null 2>&1; then
    echo "sudo apt-get install $bin"
  elif command -v dnf >/dev/null 2>&1; then
    echo "sudo dnf install $bin"
  elif command -v pacman >/dev/null 2>&1; then
    echo "sudo pacman -S $bin"
  else
    echo "see $doc_url"
  fi
}

require() {
  local bin="$1" doc_url="$2"
  command -v "$bin" >/dev/null 2>&1 && return 0
  echo "ERROR: '$bin' is required but not installed." >&2
  echo "  install: $(install_hint "$bin" "$doc_url")" >&2
  echo "  docs:    $doc_url" >&2
  exit 1
}
