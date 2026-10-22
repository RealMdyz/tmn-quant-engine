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
    if os.getenv("DISABLE_PULL"):          # container deploys (Liara) are updated by CI, not by git pull
        return False
    sh("git fetch -q origin main")
    local, remote = sh("git rev-parse HEAD"), sh("git rev-parse origin/main")
    if remote and local != remote:
        sh("git reset -q --hard origin/main", check=True)
        say(f"updated {local[:7]} -> {remote[:7]}")
        return True
    return False


def remote_url():
    tok, repo = os.getenv("GITHUB_TOKEN"), os.getenv("GITHUB_REPO", "RealMdyz/tmn-quant-engine")
    if tok:
        return f"https://x-access-token:{tok}@github.com/{repo}.git"
    return sh("git remote get-url origin")


def sync_logs():
    url = remote_url()
    if not url:
        return
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


def status_server():
    """Tiny read-only status page (Liara needs an HTTP port; also handy for the demo video)."""
    import http.server
    import threading

    class H(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            body = ""
            try:
                m = mode()
                if self.path.startswith("/report"):
                    subprocess.run([PY, "run.py", "report"], cwd=ROOT, capture_output=True, timeout=120)
                    body = open(os.path.join(LOGS, "report.md"), encoding="utf-8").read()
                elif self.path.startswith("/decisions"):
                    n = 60
                    lines = open(os.path.join(LOGS, f"decisions_{m}.jsonl"), encoding="utf-8").read().splitlines()
                    skip = ("quote",) if "all" not in self.path else ()
                    keep = [l for l in lines if not any(f'"event": "{e}"' in l for e in skip)]
                    body = "\n\n".join(keep[-n:])
                elif self.path.startswith("/bot"):
                    body = "\n".join(open(os.path.join(LOGS, f"bot_{m}.out"), encoding="utf-8").read().splitlines()[-80:])
                elif self.path.startswith("/deviations"):
                    body = "\n".join(open(os.path.join(LOGS, f"deviations_{m}.csv"), encoding="utf-8").read().splitlines()[-40:])
                else:
                    eq = os.path.join(LOGS, f"equity_{m}.csv")
                    tail = open(eq, encoding="utf-8").read().splitlines()[-15:] if os.path.exists(eq) else []
                    body = f"mode: {m}\n\n" + "\n".join(tail) + "\n\n/report  /decisions  /decisions?all  /bot  /deviations"
            except Exception as e:
                body = f"no data yet ({e})"
            data = body.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def log_message(self, *a):
            pass

    port = int(os.getenv("PORT", "0") or 0)
    if port:
        srv = http.server.ThreadingHTTPServer(("0.0.0.0", port), H)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        say(f"status page on :{port}")


def main():
    os.makedirs(LOGS, exist_ok=True)
    status_server()
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
