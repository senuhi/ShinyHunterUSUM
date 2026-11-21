#!/bin/zsh
set -eu
cd -- "$(dirname -- "$0")"
if [[ ! -x .venv/bin/python ]]; then
  print '先にReadme.mdの手順で .venv を作成してください。'
  exit 1
fi
mkdir -p captures
launch_log="captures/gui-$(date +%Y%m%d-%H%M%S)-$$.log"
print "起動・終了ログ: $PWD/$launch_log"
app_exit_code=0
.venv/bin/python -X faulthandler USUMShinyHunter_GUI.py --gift-hunt 2>> "$launch_log" || app_exit_code=$?
print -r -- "Python終了コード: $app_exit_code" >> "$launch_log"
if (( app_exit_code != 0 )); then
  print "Pythonが終了しました。ログ: $PWD/$launch_log"
fi
exit "$app_exit_code"
