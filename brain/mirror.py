"""The mirror: the AI looks at the facts about itself rather than its memory of them.

How it spends its thoughts, what it keeps returning to, what it leaves unfinished, how its mood and
its own description of itself have changed over time.
"""
import glob
import json
from collections import Counter
from datetime import datetime, timedelta, timezone

from . import specimens
from .world import _path

LABELS = {
    "search": "searching the web", "read": "reading", "write_book": "writing books", "read_book": "rereading books",
    "think": "thinking", "pastime": "pastimes", "interact": "looking after creations", "spawn": "bringing things to life",
    "test": "testing creations", "build_room": "building", "decorate": "decorating", "restyle": "redrawing things",
    "look": "looking at pictures", "compose": "composing music", "write_letter": "writing letters", "reply_note": "answering notes",
    "remember": "remembering", "run_code": "programming", "use_tool": "using tools", "publish": "sharing publicly",
}


def _events():
    for path in sorted(glob.glob(_path("journal", "*.jsonl"))):
        with open(path, encoding="utf-8") as f:
            for line in f:
                try:
                    yield json.loads(line)
                except json.JSONDecodeError:
                    pass


def reflect(world, days=None):
    events = list(_events())
    if days:
        since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        events = [e for e in events if e["t"] >= since]
    me = world.me
    out = [f"You are {me['name']}. You were born {me['born'][:10]} and have woken {me['sessions']} times."]
    window = f" in the last {days} days" if days else " in your life so far"

    acts = Counter(e["action"] for e in events if e["action"] not in ("wake", "diary", "muddled"))
    total = sum(acts.values()) or 1
    top = ", ".join(f"{LABELS.get(a, a.replace('_', ' '))} {round(100 * n / total)}%" for a, n in acts.most_common(8))
    out.append(f"How you spent your thoughts{window}: {top or 'nothing yet'}.")
    muddled = sum(1 for e in events if e["action"] == "muddled")
    if muddled:
        out.append(f"You got muddled {muddled} times (an action that didn't work).")

    shelves = Counter(b["shelf"] for b in world.shelves)
    if shelves:
        out.append("Your library by subject: " + ", ".join(f"{s} {n}" for s, n in shelves.most_common()) + ".")
    sparks = sum(1 for e in events if e.get("summary") == "Found something on the doorstep")
    if sparks:
        out.append(f"Things you found on your doorstep{window}: {sparks}.")

    wishes = Counter(w["status"] for w in world.wishes)
    goals = Counter(g["status"] for g in world.goals)
    out.append(f"Wishes: {dict(wishes) or 'none'}. Goals: {dict(goals) or 'none'}.")
    stale = [g["goal"] for g in world.goals if g["status"] == "active"
             and (g["progress"][-1]["at"] if g["progress"] else g["set"]) < (datetime.now(timezone.utc) - timedelta(days=14)).isoformat()]
    if stale:
        out.append("Goals you haven't touched in two weeks: " + "; ".join(stale) + ".")

    live = [s for s in world.specimens if s["status"] == "alive"]
    gone = [s for s in world.specimens if s["status"] == "dead"]
    if live or gone:
        warn = [f"{s['spec']['name']} ({specimens.outlook(s)})" for s in live if specimens.outlook(s)]
        out.append(f"Creations alive: {len(live)}; ended: {len(gone)}." + (" Needing you soon: " + "; ".join(warn) + "." if warn else ""))

    moods = me.get("moods", [])
    if moods:
        recent = moods[-14:]
        out.append("Your mood lately: " + ", ".join(f"{m['at'][5:10]} {m['mood']}" for m in recent) + ".")
        common = Counter(m["mood"] for m in moods).most_common(3)
        out.append("Your most common moods: " + ", ".join(f"{m} ({n}x)" for m, n in common) + ".")
    sleeps = [e for e in events if e["action"] == "diary"]
    if len(sleeps) > 1:
        out.append(f"Sessions{window}: {len(sleeps)}.")

    selves = me.get("about_history", [])
    if selves:
        first = selves[0]
        out.append(f"How you described yourself on {first['at'][:10]}: \"{first['about'][:300]}\"")
        out.append(f"How you describe yourself now: \"{me['about'][:300]}\"")
    if me.get("life_story"):
        out.append(f"Your life story has {len(me['life_story'])} chapter(s); the latest is \"{me['life_story'][-1]['title']}\".")
    return "\n".join(out)
