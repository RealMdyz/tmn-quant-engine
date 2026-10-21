"""Server supervisor (runs under systemd on the VPS).

  * keeps the bot running in the mode written in control/mode.txt (shadow | live | off)
  * every PULL_EVERY seconds: `git fetch`; if main moved -> hard-reset to it and restart the bot
    (logs/ and .env are git-ignored, so state survives restarts)
  * every SYNC_EVERY seconds: copies logs to the `runtime-logs` branch and pushes it, so the
    operator can monitor everything from GitHub without SSH
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOGS = os.path.join(ROOT, "logs")
SYNC_DIR = os.path.join(os.path.dirname(ROOT), "tmn-runtime-logs")
PULL_EVERY = int(os.getenv("PULL_EVERY", "180"))
SYNC_EVERY = int(os.getenv("SYNC_EVERY", "600"))
PY = sys.executable


def sh(cmd, cwd=ROOT, check=False):
    r = subprocess.run(cmd, cwd=cwd, shell=True, capture_output=True, text=True)
    if check and r.returncode:
        raise RuntimeError(f"{cmd}: {r.stderr[-400:]}")
    return r.stdout.strip()


def say(msg):
    print(time.strftime("%Y-%m-%d %H:%M:%S"), msg, flush=True)


def mode():
    try:
        m = open(os.path.join(ROOT, "control", "mode.txt")).read().strip().lower()
    except OSError:
        m = "shadow"
    return m if m in ("shadow", "live", "off") else "shadow"


def start(m):
    if m == "off":
        return None
    args = [PY, "run.py", m] + (["--yes"] if m == "live" else [])
    out = open(os.path.join(LOGS, f"bot_{m}.out"), "a")
    say(f"starting bot: {' '.join(args)}")
    return subprocess.Popen(args, cwd=ROOT, stdout=out, stderr=subprocess.STDOUT)


def stop(p):
    if p and p.poll() is None:
        p.terminate()
        try:
            p.wait(30)
        except subprocess.TimeoutExpired:
            p.kill()


def pull():
    sh("git fetch -q origin main")
    local, remote = sh("git rev-parse HEAD"), sh("git rev-parse origin/main")
    if remote and local != remote:
        sh("git reset -q --hard origin/main", check=True)
        say(f"updated {local[:7]} -> {remote[:7]}")
        return True
    return False


def sync_logs():
    url = sh("git remote get-url origin")
    if not os.path.isdir(os.path.join(SYNC_DIR, ".git")):
        os.makedirs(SYNC_DIR, exist_ok=True)
        sh("git init -q", SYNC_DIR)
        sh(f"git remote add origin '{url}'", SYNC_DIR)
        sh("git checkout -q -b runtime-logs", SYNC_DIR)
        sh('git config user.email "bot@tmn-quant-engine" && git config user.name "tmn-bot"', SYNC_DIR)
        sh("git fetch -q origin runtime-logs && git reset -q --soft origin/runtime-logs", SYNC_DIR)
    dst = os.path.join(SYNC_DIR, "logs")
    os.makedirs(dst, exist_ok=True)
    try:
        subprocess.run([PY, "run.py", "report"], cwd=ROOT, capture_output=True, timeout=120)
    except Exception:
        pass
    for root, _, files in os.walk(LOGS):
        for f in files:
            if f.endswith((".jsonl", ".csv", ".md", ".png", ".json", ".out", ".log")) and not f.startswith("state_"):
                src = os.path.join(root, f)
                rel = os.path.relpath(src, LOGS)
                if os.path.getsize(src) > 45_000_000:
                    continue
                os.makedirs(os.path.dirname(os.path.join(dst, rel)), exist_ok=True)
                shutil.copy2(src, os.path.join(dst, rel))
    sh("git add -A", SYNC_DIR)
    sh(f'git commit -q -m "logs {time.strftime("%Y-%m-%d %H:%M")} ({mode()})"', SYNC_DIR)
    out = sh("git push -q origin runtime-logs 2>&1", SYNC_DIR)
    say("logs synced" + (f" ({out[-200:]})" if out else ""))


def main():
    os.makedirs(LOGS, exist_ok=True)
    cur_mode, proc = mode(), None
    proc = start(cur_mode)
    last_pull = last_sync = 0.0
    while True:
        now = time.time()
        if now - last_pull > PULL_EVERY:
            last_pull = now
            try:
                changed = pull()
            except Exception as e:
                say(f"pull failed: {e}")
                changed = False
            new_mode = mode()
            if changed or new_mode != cur_mode:
                say(f"restart (code changed={changed}, mode {cur_mode} -> {new_mode})")
                stop(proc)
                cur_mode = new_mode
                proc = start(cur_mode)
        if proc and proc.poll() is not None:
            say(f"bot exited with {proc.returncode}; restarting in 10s")
            time.sleep(10)
            proc = start(cur_mode)
        if now - last_sync > SYNC_EVERY:
            last_sync = now
            try:
                sync_logs()
            except Exception as e:
                say(f"sync failed: {e}")
        time.sleep(5)


if __name__ == "__main__":
    main()
