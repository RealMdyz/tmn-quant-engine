"""Server supervisor (runs under systemd on the VPS).

  * keeps the bot running in the mode written in control/mode.txt (shadow | live | off)
  * every PULL_EVERY seconds: `git fetch`; if main moved -> hard-reset to it and restart the bot
    (logs/ and .env are git-ignored, so state survives restarts)
  * container deploys (Liara): when GITHUB_TOKEN is set, the bot runs from a git clone of main in
    CODE_DIR that is pulled the same way, so a code change reaches the server in ~2 minutes without
    a Docker rebuild (only requirements.txt / supervisor changes need a redeploy)
  * every SYNC_EVERY seconds: copies logs to the `runtime-logs` branch and pushes it, so the
    operator can monitor everything from GitHub without SSH
"""
from __future__ import annotations

import os
import shutil
import signal
import subprocess
import sys
import threading
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOGS = os.path.join(ROOT, "logs")
SYNC_DIR = os.path.join(os.path.dirname(ROOT), "tmn-runtime-logs")
PULL_EVERY = int(os.getenv("PULL_EVERY", "120"))
GIT_CODE = os.getenv("CODE_FROM_GIT", "1" if os.getenv("GITHUB_TOKEN") else "0") == "1"
CODE_DIR = os.getenv("CODE_DIR", os.path.join(os.path.dirname(ROOT), "tmn-code"))
APP = ROOT            # directory the bot runs from; becomes CODE_DIR once the git clone is ready
SYNC_EVERY = int(os.getenv("SYNC_EVERY", "600"))
SYNC_MAX_BYTES = int(os.getenv("SYNC_MAX_BYTES", "8000000"))
PY = sys.executable


def sh(cmd, cwd=ROOT, check=False, timeout=120):
    # own process group: on a timeout the whole group (git and its helpers) is killed, not only /bin/sh.
    # Killing only the shell left git children behind; as PID 1 this process inherited them and they
    # piled up until the container could not start any process ("/bin/sh: Cannot fork", live 2026-10-23).
    try:
        p = subprocess.Popen(cmd, cwd=cwd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                             text=True, start_new_session=True)
    except OSError as e:
        say(f"cannot start '{cmd.split(' origin')[0][:60]}': {e}")
        return ""
    try:
        out, err = p.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(p.pid, signal.SIGKILL)
        except OSError:
            pass
        p.communicate()
        if check:
            raise RuntimeError(f"{cmd}: timed out after {timeout}s")
        say(f"timeout after {timeout}s: {cmd.split(' origin')[0][:60]}")
        return ""
    if check and p.returncode:
        raise RuntimeError(f"{cmd}: {err[-400:]}")
    return out.strip()


def reap_orphans(keep=()):
    """As the container's PID 1 this process adopts every orphaned process; reap the finished ones
    (git helpers and the like) so they never fill the process table. Our own children are left alone."""
    me = os.getpid()
    try:
        pids = [int(d) for d in os.listdir("/proc") if d.isdigit()]
    except OSError:
        return
    reaped = 0
    for pid in pids:
        if pid in keep:
            continue
        try:
            stat = open(f"/proc/{pid}/stat").read()
        except OSError:
            continue
        name, rest = stat[stat.find("(") + 1:stat.rfind(")")], stat[stat.rfind(")") + 2:].split()
        if rest[0] == "Z" and int(rest[1]) == me and name not in ("sh", "python", "python3"):
            try:
                os.waitpid(pid, os.WNOHANG)
                reaped += 1
            except ChildProcessError:
                pass
    if reaped:
        say(f"reaped {reaped} finished orphan process(es)")


def say(msg):
    print(time.strftime("%Y-%m-%d %H:%M:%S"), msg, flush=True)


def mode():
    try:
        m = open(os.path.join(APP, "control", "mode.txt")).read().strip().lower()
    except OSError:
        m = "shadow"
    return m if m in ("shadow", "live", "off") else "shadow"


def start(m):
    if m == "off":
        return None
    sys.path.insert(0, APP)
    from bot.instance import held_elsewhere
    other = held_elsewhere(os.path.join(LOGS, f"instance_{m}.lock"))
    if other:
        say(f"bot of another container ({other}) is running on the shared volume: not starting ours yet")
        return None
    args = [PY, "run.py", m] + (["--yes"] if m == "live" else [])
    out = open(os.path.join(LOGS, f"bot_{m}.out"), "a")
    say(f"starting bot: {' '.join(args)}")
    return subprocess.Popen(args, cwd=APP, stdout=out, stderr=subprocess.STDOUT)


def stop(p):
    if p and p.poll() is None:
        p.terminate()
        try:
            p.wait(30)
        except subprocess.TimeoutExpired:
            p.kill()


def setup_code():
    """Clone main into CODE_DIR and run the bot from there (logs/ points to the persistent volume)."""
    global APP
    if not GIT_CODE:
        return
    if not os.path.isdir(os.path.join(CODE_DIR, ".git")):
        shutil.rmtree(CODE_DIR, ignore_errors=True)
        sh(f"git clone -q --depth 20 --branch main '{remote_url()}' '{CODE_DIR}'", cwd=os.path.dirname(CODE_DIR),
           timeout=300)
    if not os.path.isfile(os.path.join(CODE_DIR, "run.py")):
        say("git clone failed: running the image's code")
        return
    link = os.path.join(CODE_DIR, "logs")
    if not os.path.islink(link):
        if os.path.isdir(link) and os.path.realpath(link) != os.path.realpath(LOGS):
            shutil.rmtree(link)
        os.symlink(LOGS, link)
    APP = CODE_DIR
    say(f"running code from git clone @ {sh('git rev-parse --short HEAD', CODE_DIR)} (code changes need no rebuild)")


def pull():
    if APP == CODE_DIR and APP != ROOT:
        sh("git fetch -q --depth 20 origin main", CODE_DIR, timeout=120)
        local, remote = sh("git rev-parse HEAD", CODE_DIR), sh("git rev-parse origin/main", CODE_DIR)
        if remote and local and local != remote:
            sh("git reset -q --hard origin/main", CODE_DIR, check=True)
            say(f"code updated {local[:7]} -> {remote[:7]}")
            return True
        return False
    if os.getenv("DISABLE_PULL"):          # image-only container deploy: updated by a rebuild
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
        subprocess.run([PY, "run.py", "report"], cwd=APP, capture_output=True, timeout=120)
    except Exception:
        pass
    for root, _, files in os.walk(LOGS):
        for f in files:
            if f.endswith((".jsonl", ".csv", ".md", ".png", ".json", ".out", ".log")) and not f.startswith("state_"):
                src = os.path.join(root, f)
                rel = os.path.relpath(src, LOGS)
                if os.path.getsize(src) > SYNC_MAX_BYTES:     # GitHub from Iran is slow: keep pushes small
                    continue
                os.makedirs(os.path.dirname(os.path.join(dst, rel)), exist_ok=True)
                shutil.copy2(src, os.path.join(dst, rel))
    sh("git add -A", SYNC_DIR)
    sh(f'git commit -q -m "logs {time.strftime("%Y-%m-%d %H:%M")} ({mode()})"', SYNC_DIR)
    out = sh("git push -q origin runtime-logs 2>&1", SYNC_DIR, timeout=240)
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
                    subprocess.run([PY, "run.py", "report"], cwd=APP, capture_output=True, timeout=120)
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


def safe_sync():
    try:
        sync_logs()
    except Exception as e:
        say(f"sync failed: {e}")


def main():
    os.makedirs(LOGS, exist_ok=True)
    status_server()
    setup_code()
    cur_mode, proc = mode(), None
    proc = start(cur_mode)
    # read-only market probe on every deploy (research data; Wallex is only reachable from here)
    probe = subprocess.Popen([sys.executable, "run.py", "probe"], cwd=APP,
                             stdout=open(os.path.join(LOGS, "probe.out"), "a"), stderr=subprocess.STDOUT)
    last_pull = last_sync = 0.0
    syncer = None
    while True:
        now = time.time()
        if probe and probe.poll() is not None:
            say(f"probe finished ({probe.returncode}); syncing logs now")
            probe = None
            last_sync = 0.0
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
        reap_orphans(keep={proc.pid} if proc else ())
        if proc and proc.poll() is not None:
            say(f"bot exited with {proc.returncode}; restarting in 10s")
            time.sleep(10)
            proc = start(cur_mode)
        elif proc is None and cur_mode != "off" and now - getattr(main, "_retry", 0) > 15:
            main._retry = now               # waiting for the other container's bot to go away
            proc = start(cur_mode)
        if now - last_sync > SYNC_EVERY and not (syncer and syncer.is_alive()):
            last_sync = now
            syncer = threading.Thread(target=safe_sync, daemon=True)   # a slow push must never block supervision
            syncer.start()
        time.sleep(5)


if __name__ == "__main__":
    main()
