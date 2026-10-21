#!/usr/bin/env bash
# One-time server setup (Ubuntu/Debian). Run as root:
#   curl -fsSL -H "Authorization: token <GITHUB_TOKEN>" \
#     https://raw.githubusercontent.com/RealMdyz/tmn-quant-engine/main/deploy/bootstrap.sh -o bootstrap.sh
#   bash bootstrap.sh
# It asks for the secrets interactively and stores them ONLY in /opt/tmn-quant-engine/.env (chmod 600).
set -euo pipefail
APP=/opt/tmn-quant-engine
REPO=RealMdyz/tmn-quant-engine

echo "== installing system packages"
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq && apt-get install -y -qq git python3 python3-venv python3-pip ca-certificates >/dev/null

read -rsp "GitHub fine-grained token (repo contents read/write): " GHTOKEN; echo
read -rsp "Wallex API key (challenge account): " WALLEX; echo
read -rsp "BoxAPI key (LLM): " LLMKEY; echo
read -rsp "AvalAI key (optional backup LLM, Enter to skip): " LLM2KEY; echo

echo "== cloning"
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

echo "== python env"
python3 -m venv .venv
if ! .venv/bin/pip install -q -r requirements.txt; then
  echo "PyPI unreachable, trying Iranian mirror"
  .venv/bin/pip install -q -r requirements.txt -i https://mirror-pypi.runflare.com/simple || \
  .venv/bin/pip install -q -r requirements.txt -i https://package-mirror.liara.ir/repository/pypi/simple
fi

echo "== connectivity check"
.venv/bin/python run.py check || true

echo "== systemd service"
cat > /etc/systemd/system/tmn-bot.service <<EOF
[Unit]
Description=TMN Quant Engine supervisor
After=network-online.target
Wants=network-online.target

[Service]
WorkingDirectory=${APP}
ExecStart=${APP}/.venv/bin/python ${APP}/deploy/supervisor.py
Restart=always
RestartSec=10
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
EOF
timedatectl set-timezone Asia/Tehran || true
systemctl daemon-reload
systemctl enable --now tmn-bot
sleep 3
systemctl --no-pager status tmn-bot | head -12
echo
echo "DONE. The bot runs in the mode written in control/mode.txt (default: shadow)."
echo "Live logs: journalctl -u tmn-bot -f   |   bot output: tail -f ${APP}/logs/bot_shadow.out"
