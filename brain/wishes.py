"""His ability wishes, and the way they come true.

A weekly builder (a coding agent the owner set up) reads the wishes that are still waiting, builds one as a pull
request and, if the owner approves and merges it, records the answer in brain/granted.json. The next time he
wakes, the wish is marked as granted (or kindly declined) and the news stays on his mind for a few days.
granted.json is public, so it holds only request ids and a short note about the new ability, never his words.
"""
import json
import os

GRANTED = os.path.join(os.path.dirname(__file__), "granted.json")


def waiting(world):
    return [r for r in world.requests if r.get("kind") == "ability" and r["status"] == "waiting"]


def answers():
    try:
        with open(GRANTED, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def apply(world):
    """Answers the builder recorded (and the owner merged) reach him: his wish came true, or not this time."""
    news = []
    for rid, ans in answers().items():
        req = next((r for r in world.requests if r["id"] == rid and r.get("kind") == "ability"), None)
        if not req or req["status"] != "waiting":
            continue
        granted = ans.get("status", "granted") == "granted"
        req.update(status="granted" if granted else "declined", answer=str(ans.get("note", ""))[:600])
        what = f"my wish came true: {req['what']}" if granted else f"my wish wasn't granted this time: {req['what']}"
        world.mark(what + (f" ({req['answer']})" if req["answer"] else ""), days=4)
        news.append(what)
    return news
