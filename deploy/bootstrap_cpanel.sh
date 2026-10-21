#!/usr/bin/env bash
# Setup on cPanel shared hosting (no root, no systemd). Run inside cPanel -> Terminal:
#   bash bootstrap_cpanel.sh
# Secrets are typed interactively and stored only in ~/tmn-quant-engine/.env (chmod 600).
# A cron job (every minute, guarded by flock) keeps the supervisor alive if the host kills it.
set -euo pipefail
APP="$HOME/tmn-quant-engine"
REPO=RealMdyz/tmn-quant-engine

read -rsp "GitHub fine-grained token (repo contents read/write): " GHTOKEN; echo
read -rsp "Wallex API key (challenge account): " WALLEX; echo
read -rsp "BoxAPI key (LLM): " LLMKEY; echo
read -rsp "AvalAI key (optional, Enter to skip): " LLM2KEY; echo

if [ ! -d "$APP/.git" ]; then
  git clone -q "https://x-access-token:${GHTOKEN}@github.com/${REPO}.git" "$APP"
fi
cd "$APP"
git config user.email "bot@tmn-quant-engine"; git config user.name "tmn-bot"
cat > .env <<EOF
WALLEX_API_KEY=${WALLEX}
LLM_BASE_URL=https://ai.boxapi.ir/ai/v1
LLM_API_KEY=${LLMKEY}
LLM2_BASE_URL=https://api.avalai.ir/v1
LLM2_API_KEY=${LLM2KEY}
EOF
chmod 600 .env

PY=$(command -v python3.11 || command -v python3.10 || command -v python3.9 || command -v python3)
echo "using $PY ($($PY --version))"
$PY -m venv .venv || { echo "venv not available: create one in cPanel -> Setup Python App, then re-run"; exit 1; }
.venv/bin/pip install -q --upgrade pip || true
.venv/bin/pip install -q -r requirements.txt || \
  .venv/bin/pip install -q -r requirements.txt -i https://mirror-pypi.runflare.com/simple || \
  .venv/bin/pip install -q -r requirements.txt -i https://package-mirror.liara.ir/repository/pypi/simple
mkdir -p logs
.venv/bin/python run.py check || true

# keep-alive cron (every minute; flock prevents duplicates)
LINE="* * * * * cd $APP && /usr/bin/flock -n $APP/logs/.sup.lock $APP/.venv/bin/python deploy/supervisor.py >> $APP/logs/supervisor.out 2>&1"
( crontab -l 2>/dev/null | grep -v "tmn-quant-engine" ; echo "$LINE" ) | crontab -
nohup /usr/bin/flock -n "$APP/logs/.sup.lock" "$APP/.venv/bin/python" deploy/supervisor.py >> "$APP/logs/supervisor.out" 2>&1 &
sleep 5
tail -5 logs/supervisor.out || true
echo "DONE. Mode = $(cat control/mode.txt). Logs: tail -f $APP/logs/bot_shadow.out"
