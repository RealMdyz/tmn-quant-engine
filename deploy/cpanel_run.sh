#!/usr/bin/env bash
# Called every minute by cron on cPanel shared hosting (guarded by flock, so only one copy runs).
# First run: probes the host, builds the Python env, writes .env from ~/tmn.env. Then it runs the
# supervisor in the foreground; if the host kills it, the next cron tick starts it again.
APP="$HOME/tmn-quant-engine"
cd "$APP" || exit 1
mkdir -p logs
echo "=== $(date '+%F %T') cpanel_run start"

pick_python() {
  for p in /opt/alt/python312/bin/python3 /opt/alt/python311/bin/python3 /opt/alt/python310/bin/python3 \
           /opt/alt/python39/bin/python3 python3.12 python3.11 python3.10 python3.9 python3; do
    if command -v "$p" >/dev/null 2>&1 && "$p" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)' 2>/dev/null; then
      echo "$p"; return 0
    fi
  done
  return 1
}

if [ ! -f logs/.probe_done ]; then
  echo "--- host probe"
  uname -a; id; ulimit -a | head -5
  which git curl flock || true
  for p in /opt/alt/python3*/bin/python3 python3; do echo "$p: $($p --version 2>&1)"; done
  curl -s -m 10 -o /dev/null -w "wallex %{http_code}\n" https://api.wallex.ir/v1/markets
  curl -s -m 10 -o /dev/null -w "github %{http_code}\n" https://github.com
  curl -s -m 10 -o /dev/null -w "boxapi %{http_code}\n" https://ai.boxapi.ir/ai/v1/models
  curl -s -m 10 -o /dev/null -w "pypi %{http_code}\n" https://pypi.org/simple/
  touch logs/.probe_done
fi

# secrets: ~/tmn.env (created by the account owner) -> .env used by the bot
if [ -f "$HOME/tmn.env" ] && [ ! -f .env ]; then
  grep -v '^GITHUB_TOKEN' "$HOME/tmn.env" > .env
  chmod 600 .env
fi

if [ ! -f .venv/.ready ]; then
  PY=$(pick_python) || { echo "no python >= 3.9 found"; exit 1; }
  echo "--- building venv with $PY"
  "$PY" -m venv .venv || { echo "venv failed"; exit 1; }
  .venv/bin/pip install -q --upgrade pip
  .venv/bin/pip install -q -r requirements.txt \
    || .venv/bin/pip install -q -r requirements.txt -i https://mirror-pypi.runflare.com/simple \
    || .venv/bin/pip install -q -r requirements.txt -i https://package-mirror.liara.ir/repository/pypi/simple \
    || { echo "pip install failed"; exit 1; }
  touch .venv/.ready
  echo "--- check"
  .venv/bin/python run.py check 2>&1 | tail -40
fi

echo "--- starting supervisor (mode: $(cat control/mode.txt))"
exec .venv/bin/python deploy/supervisor.py
