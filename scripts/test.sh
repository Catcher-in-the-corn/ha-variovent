#!/usr/bin/env bash
# Run the test suite. One command for humans, CI and the review agents.
#
#   scripts/test.sh [pytest args...]
#
# On Windows (Git Bash / MSYS) the Home Assistant test framework needs a few
# shims (scripts/winshim). On Linux it runs plain pytest. A local virtualenv in
# .venv is used if present, otherwise whatever pytest is on PATH.
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

PY="python"
if [ -x ".venv/Scripts/python.exe" ]; then PY=".venv/Scripts/python.exe"      # Windows venv
elif [ -x ".venv/bin/python" ]; then PY=".venv/bin/python"; fi                 # POSIX venv

case "$(uname -s)" in
  MINGW* | MSYS* | CYGWIN*)
    PYTHONPATH="scripts/winshim${PYTHONPATH:+:$PYTHONPATH}" \
      "$PY" -m pytest -p winfix -p no:cacheprovider "$@"
    ;;
  *)
    "$PY" -m pytest -p no:cacheprovider "$@"
    ;;
esac
