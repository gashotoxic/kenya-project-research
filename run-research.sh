#!/usr/bin/env bash
# Kenya project researcher — THE one command.
# Runs the full pipeline: validate -> score -> gate -> dedup -> backlog (-> notify).
# Usage: ./run-research.sh [--fetch] [--notify] [--check] [see --help]
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"

if [[ "${1:-}" == "--check" ]]; then
  shift
  exec python3 -m researcher.cli check "$@"
fi
exec python3 -m researcher.cli run "$@"
