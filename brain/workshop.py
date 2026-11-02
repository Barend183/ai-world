"""The AI's workshop: it writes and runs its own Python programs.

Programs an AI writes after reading the internet must not run on your own PC, so the workshop only
opens online, on GitHub's throwaway servers (or locally if you set "allow_code_locally": true).
Online, each program runs as a separate, unprivileged user with an empty environment, so it can't
read the API keys or the GitHub token, and the checkout keeps no credentials it could push with.
"""
import os
import re
import shutil
import subprocess
import sys

from .world import WORLD

FOLDER = os.path.join(WORLD, "workshop")
MAX_FILES_BYTES = 5_000_000
SANDBOX_USER = "sprout"


def enabled(config):
    return os.environ.get("GITHUB_ACTIONS") == "true" or bool(config.get("allow_code_locally"))


def _size():
    return sum(os.path.getsize(os.path.join(d, f)) for d, _, files in os.walk(FOLDER) for f in files)


def run(code, save_as=None, timeout=60):
    if not code.strip():
        raise ValueError("there's no code to run")
    os.makedirs(FOLDER, exist_ok=True)
    if save_as:
        name = re.sub(r"[^A-Za-z0-9_.-]", "_", str(save_as))[:60]
        name = name if name.endswith(".py") else name + ".py"
        with open(os.path.join(FOLDER, name), "w", encoding="utf-8") as f:
            f.write(code)
    script = os.path.join(FOLDER, ".last_run.py")
    with open(script, "w", encoding="utf-8") as f:
        f.write(code)

    env = {"PATH": os.environ.get("PATH", ""), "HOME": FOLDER, "PYTHONIOENCODING": "utf-8", "LANG": "C.UTF-8"}
    cmd = [sys.executable, "-I", script]
    if os.environ.get("GITHUB_ACTIONS") == "true":
        # A different user can't read this process's environment (and its keys) through /proc.
        if not shutil.which("sudo"):
            raise ValueError("the workshop's safety lock isn't available here, so it stays closed")
        cmd = ["sudo", "-n", "-u", SANDBOX_USER, "env", "-i", *[f"{k}={v}" for k, v in env.items()], *cmd]
    try:
        done = subprocess.run(cmd, cwd=FOLDER, env=env, capture_output=True, timeout=timeout)
        out = (done.stdout + done.stderr).decode("utf-8", errors="replace")
        status = "" if done.returncode == 0 else f"\n(exited with code {done.returncode})"
    except subprocess.TimeoutExpired as e:
        out = ((e.stdout or b"") + (e.stderr or b"")).decode("utf-8", errors="replace")
        status = f"\n(stopped after {timeout} seconds)"
    if _size() > MAX_FILES_BYTES:
        status += "\n(your workshop folder is over 5 MB; delete things you don't need)"
    out = out.strip() or "(the program printed nothing)"
    if len(out) > 5000:
        out = out[:2500] + "\n[...]\n" + out[-2400:]
    files = sorted(f for f in os.listdir(FOLDER) if not f.startswith("."))
    return out + status + (f"\nFiles in your workshop: {', '.join(files[:40])}" if files else "")
