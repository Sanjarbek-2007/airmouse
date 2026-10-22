#!/usr/bin/env bash
# AirCursor launcher.  ./run.sh            open the app
#                      ./run.sh ctl toggle   pause/resume the running app (bind to a shortcut)
#                      ./run.sh ctl quit     quit it
set -e
DIR="$(cd "$(dirname "$0")" && pwd)"
if [ ! -x "$DIR/.venv/bin/python" ]; then
  echo "First run: setting up (a few minutes)..." >&2
  "$DIR/scripts/setup-linux.sh"
fi
export PYTHONPATH="$DIR${PYTHONPATH:+:$PYTHONPATH}"
exec "$DIR/.venv/bin/python" -m aircursor "$@"
