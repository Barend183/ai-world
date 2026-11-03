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
from .mind import live
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


def trigger_fired(world):
    """Checked while he sleeps, without using his thinking budget: did one of his wake-up triggers happen?"""
    import copy
    from . import env, specimens
    now_ = datetime.now(timezone.utc)
    last = datetime.fromisoformat(world.me.get("last_seen") or now_.isoformat())
    weather = None
    for t in world.me.get("wake_triggers", []):
        try:
            if t["kind"] == "rain":
                weather = weather or env.Weather(config_of(world))
                if not weather.hours:
                    weather.refresh(1)
                if weather.at(now_, True)["env_rain"] >= t["min_mm"]:
                    return "it started raining"
            elif t["kind"] == "time":
                h, m = map(int, t["at"].split(":"))
                offset = timedelta(hours=config_of(world).get("utc_offset_hours", 2))
                local_now = now_ + offset
                at = local_now.replace(hour=h, minute=m, second=0, microsecond=0)
                if at > local_now:
                    at -= timedelta(days=1)
                if at - offset > last:
                    return f"it's {t['at']}, the time you asked to be woken"
            elif t["kind"] == "creation":
                sp = world.specimen(t["specimen"])
                if sp and sp["status"] == "alive":
                    ghost = copy.deepcopy(sp)
                    specimens.advance(ghost)
                    scope = {**ghost["values"], **specimens.env_at(ghost, now_)}
                    if specimens.holds(t["if"], scope, specimens.season_at(ghost["spec"], now_)):
                        return f"{sp['spec']['name']} needs you ({t['if']})"
        except Exception as e:
            print("couldn't check a wake-up trigger:", type(e).__name__)
    return None


def config_of(world):
    return world.config


def health(session):
    """A content-free check-up for the public log: which kinds of actions he took and which went wrong,
    by action name only (never what he read, wrote or thought), so problems can be found and fixed."""
    import re
    from collections import Counter
    from .mind import ACTIONS
    did, trouble, brains = Counter(), Counter(), Counter()
    for e in session:
        who = "companion " if e.get("who") else ""
        if e["action"] == "wake":
            brains[who + str(e.get("brain", "?"))] += 1   # the model's name, so a stuck model shows
        elif e["action"] == "muddled":
            tried = str(e.get("tried", ""))
            if e.get("trouble") == "failed" and tried in ACTIONS:
                kind = f"{tried} failed"
            elif e.get("trouble") == "unknown":   # just the bare name he reached for, to see which action he's missing
                kind = f"unknown action '{re.sub(r'[^a-z_]', '', tried.lower())[:24]}'"
            elif e.get("trouble") == "lost" or "train of thought" in e["summary"]:
                kind = "bad reply"
            else:   # older entries without the tags
                word = re.sub(r"^(I )?[Cc]ouldn't ", "", e["summary"]).replace(" ", "_")
                kind = f"{word} failed" if word in ACTIONS else "unknown action"
            trouble[who + kind] += 1
        else:
            did[who + e["action"]] += 1
    fmt = lambda c: ", ".join(f"{k} x{n}" for k, n in c.most_common()) or "none"
    return "\n".join([f"  thinking with: {fmt(brains)}", f"  did: {fmt(did)}", f"  trouble: {fmt(trouble)}"])


def run_once(config, script=None, next_wake_minutes=None, force=False):
    world = World(config)
    from . import mailbox
    wake_after = world.me.get("wake_after")
    if not force and script is None and wake_after and datetime.fromisoformat(wake_after) > datetime.now(timezone.utc):
        before = len(world.pending_notes())
        mailbox.collect(world)   # a new note wakes him early
        reason = "a note arrived" if len(world.pending_notes()) > before else trigger_fired(world)
        if not reason:
            print(f"{config['name']} is asleep until {wake_after} (his choice).")
            return None
        world.me["woke_because"] = reason
        world.save()
    # his alarm clock rings only when it's what wakes him (not a note, nor someone waking him early)
    if world.me.pop("alarm_wake", False) and wake_after and not world.me.get("woke_because") \
            and datetime.fromisoformat(wake_after) <= datetime.now(timezone.utc):
        world.me["alarm_rang"] = True
        if (world.me.get("alarm") or {}).get("repeat") == "once":
            world.me["alarm"]["on"] = False
    chain = Chain(config, world.brain_status)

    def guest_chain():   # the companion thinks with its own brains first, so the two rarely compete for one
        if script is not None:
            gc = Chain(config, world.brain_status)
            gc.current = Scripted([a for a in script if a.get("who") == "companion"])
            return gc
        return Chain({**config, "brains": config.get("companion_brains", ["groq", "openrouter", "gemini", "ollama"])}, world.brain_status)

    if script is not None:
        chain.current = Scripted([a for a in script if a.get("who") != "companion"])
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
        live(world, chain, guest_chain)
    except BrainUnavailable as e:
        world.me = world.home
        world.me["state"] = "asleep"
        world.log("sleep", "Felt too foggy to think and went back to bed", str(e))
    page_config(config, next_wake_minutes, world.me.get("wake_after"))
    world.save()
    from . import live as live_view
    live_view.push(force=True)   # the page sees him go to bed right away
    session = [e for e in world.recent if e["session"] == world.me["sessions"]]
    if (os.environ.get("WORLD_PASSWORD") or os.environ.get("WORLD_PASSWORD_NEW")) and os.environ.get("GITHUB_ACTIONS"):
        print(f"  ({len(session)} things done; details stay locked)")   # GitHub's logs are public
        print(health(session))
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
