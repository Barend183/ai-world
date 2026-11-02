"""Wake the AI up.

  python -m brain run                    one session, then back to bed
  python -m brain loop --every 30        keep waking it every 30 minutes (on your PC)
  python -m brain status                 which brains are usable right now
"""
import argparse
import json
import os
import re
import sys
import time
from datetime import datetime, timedelta, timezone

from .llm import BrainUnavailable, Chain, Scripted
from .mind import Session
from .world import ROOT, World, save

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def load_config():
    with open(os.path.join(ROOT, "config.json"), encoding="utf-8") as f:
        config = json.load(f)
    secrets = os.path.join(ROOT, "secrets.json")  # local only, never committed
    if os.path.exists(secrets):
        with open(secrets, encoding="utf-8-sig") as f:
            text = f.read()
        try:
            keys = json.loads(text)
        except json.JSONDecodeError:  # forgive keys pasted without their quotes
            keys = dict(re.findall(r'"?([A-Z_]+_API_KEY)"?\s*:\s*"?([^",}\s]+)', text))
        for name, key in keys.items():
            if key and not str(key).startswith("paste-") and not os.environ.get(name):
                os.environ[name] = str(key)
    return config


def page_config(config, next_wake_minutes, next_wake=None):
    """Small file the web page reads: name, where notes go, when it next wakes."""
    repo = os.environ.get("GITHUB_REPOSITORY")
    if not next_wake and next_wake_minutes:
        next_wake = (datetime.now(timezone.utc) + timedelta(minutes=next_wake_minutes)).isoformat(timespec="seconds")
    me = World(config).me
    save("config.json", {
        "name": me.get("name", config["name"]),
        "visitor": config.get("visitor"),
        "pronouns": me.get("pronouns") or config.get("pronouns", ["it", "it", "its"]),
        "mode": "github" if repo else "local",
        "repo": repo,
        "next_wake": next_wake,
    })


def run_once(config, script=None, next_wake_minutes=None, force=False):
    world = World(config)
    from . import mailbox
    wake_after = world.me.get("wake_after")
    if not force and script is None and wake_after and datetime.fromisoformat(wake_after) > datetime.now(timezone.utc):
        before = len(world.pending_notes())
        mailbox.collect(world)   # a new note wakes him early
        if len(world.pending_notes()) == before:
            print(f"{config['name']} is asleep until {wake_after} (his choice).")
            return None
        world.save()
    chain = Chain(config, world.brain_status)
    if script is not None:
        chain.current = Scripted(script)
    elif chain.pick() is None:
        print("No brain available:", "; ".join(chain.problems))
        if os.environ.get("GITHUB_OUTPUT") and "ollama" in chain.order:
            with open(os.environ["GITHUB_OUTPUT"], "a") as f:
                f.write("needs_local=true\n")
        world.save()
        return False
    print(f"{config['name']} wakes up, thinking with {chain.current.label}", flush=True)
    page_config(config, None)
    try:
        Session(world, chain).run()
    except BrainUnavailable as e:
        world.me["state"] = "asleep"
        world.log("sleep", "Felt too foggy to think and went back to bed", str(e))
    page_config(config, next_wake_minutes, world.me.get("wake_after"))
    world.save()
    session = [e for e in world.recent if e["session"] == world.me["sessions"]]
    if os.environ.get("WORLD_PASSWORD") and os.environ.get("GITHUB_ACTIONS"):
        print(f"  ({len(session)} things done; details stay locked)")   # GitHub's logs are public
    else:
        for e in session:
            print(f"  [{e['place']:>8}] {e['summary']}")
    return True


def main():
    p = argparse.ArgumentParser(prog="brain")
    sub = p.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--next-wake", type=int, default=None, help="minutes until the next wake-up (shown on the page)")
    r.add_argument("--script", help="JSON file of actions for a test run without any AI")
    r.add_argument("--now", action="store_true", help="wake him even if he chose to sleep longer")
    loop = sub.add_parser("loop")
    loop.add_argument("--every", type=int, default=30, help="minutes between sessions")
    sub.add_parser("status")
    sub.add_parser("lock", help="seal docs/world into docs/vault with WORLD_PASSWORD")
    sub.add_parser("unlock", help="open docs/vault into docs/world with WORLD_PASSWORD")
    ans = sub.add_parser("answer", help="answer one of his requests")
    ans.add_argument("id")
    ans.add_argument("decision", choices=["yes", "no", "later"])
    ans.add_argument("message", nargs="?", default="")
    a = p.parse_args()
    config = load_config()

    if a.cmd == "run":
        script = None
        if a.script:
            with open(a.script, encoding="utf-8") as f:
                script = json.load(f)
        run_once(config, script, a.next_wake, force=a.now)
    elif a.cmd == "loop":
        print("Running on this PC. He wakes when he chooses to (Ctrl+C to stop).")
        while True:
            run_once(config)
            time.sleep(a.every * 60)   # check again in a little while
    elif a.cmd in ("lock", "unlock"):
        from . import vault
        if a.cmd == "lock":
            print(f"Locked his world ({vault.lock()} file(s) sealed).")
        else:
            print("Unlocked his world." if vault.unlock() else "")
    elif a.cmd == "answer":
        world = World(config)
        req = next((r for r in world.requests if r["id"] == a.id), None)
        if not req:
            sys.exit(f"no request {a.id}")
        req.update(status={"yes": "granted", "no": "declined", "later": "waiting"}[a.decision], answer=a.message or None)
        world.save()
        print(f"{a.id} -> {req['status']}")
    elif a.cmd == "status":
        world = World(config)
        chain = Chain(config, world.brain_status)
        brain = chain.pick()
        print("Thinking with:", brain.label if brain else "nothing available")
        for problem in chain.problems:
            print("  -", problem)


main()
