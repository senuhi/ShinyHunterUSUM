#!/bin/zsh
set -eu
cd -- "$(dirname -- "$0")"
if [[ ! -x .venv/bin/python ]]; then
  print '先にReadme.mdの手順で .venv を作成してください。'
  exit 1
fi
exec .venv/bin/python USUMShinyHunter_GUI.py
