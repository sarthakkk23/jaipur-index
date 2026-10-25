#!/usr/bin/env bash
# Build the main site and run the gate. Usage: ./build.sh [path/to/café/insights.json]
# With no path, the café figures are read from the live café site (what CI does).
set -euo pipefail
cd "$(dirname "$0")"
PY=.venv/bin/python
[ -x "$PY" ] || { python3 -m venv .venv && .venv/bin/pip -q install -r requirements.txt; }
ARGS=()
[ $# -gt 0 ] && ARGS=(--data "cafes=$1")
"$PY" pipeline/build.py ${ARGS[@]+"${ARGS[@]}"}
"$PY" pipeline/check.py
