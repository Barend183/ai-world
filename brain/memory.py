"""Looking back: the AI searches everything it has ever written or done, not just what's in view.

Books, its notebook, goals, letters and notes, and every journal entry since it was born. Simple
word matching, so it works on any computer without extra libraries.
"""
import glob
import json
import os
import re

from .world import _path


def _words(text):
    return [w for w in re.findall(r"[a-z0-9]+", text.lower()) if len(w) > 2]


def _snippet(text, words, size=260):
    low = text.lower()
    hits = [low.find(w) for w in words if low.find(w) >= 0]
    start = max(0, min(hits) - 80) if hits else 0
    piece = " ".join(text[start:start + size].split())
    return ("..." if start else "") + piece + ("..." if start + size < len(text) else "")


def _documents(world):
    for b in world.shelves:
        try:
            text = world.read_book_text(b["id"])
        except OSError:
            text = b.get("summary", "")
        yield f"book [{b['id']}] {b['title']}", b["title"], text, b.get("updated", "")
    if world.me.get("notebook"):
        yield "your notebook", "notebook", world.me["notebook"], ""
    for g in world.goals:
        yield f"goal [{g['id']}] {g['goal']}", g["goal"], g["why"] + " " + " ".join(p["note"] for p in g["progress"]), g.get("set", "")
    for n in world.notes:
        who = f"letter you wrote" if n.get("outgoing") else f"note from {n['from']}"
        yield f"{who} ({n['at'][:10]})", "", n["text"] + " " + (n.get("reply") or ""), n["at"]
    for path in sorted(glob.glob(_path("journal", "*.jsonl"))):
        with open(path, encoding="utf-8") as f:
            for line in f:
                try:
                    e = json.loads(line)
                except json.JSONDecodeError:
                    continue
                yield (f"journal {e['t'][:16].replace('T', ' ')}", e["summary"],
                       e["summary"] + " " + (e.get("thought") or "") + " " + (e.get("detail") or ""), e["t"])


def search(world, query, limit=6):
    words = _words(query)
    if not words:
        raise ValueError("what do you want to remember? give a few words")
    found = []
    for label, title, text, when in _documents(world):
        low = text.lower()
        score = sum(low.count(w) for w in words) + 3 * sum(w in title.lower() for w in words)
        covered = sum(w in low or w in title.lower() for w in words)
        if covered:
            found.append((covered, score, when, label, _snippet(text, words)))
    if not found:
        return f'Nothing in your memory mentions "{query}".'
    found.sort(key=lambda f: (f[0], f[1], f[2]), reverse=True)
    return "\n".join(f"- {label}: {snip}" for _, _, _, label, snip in found[:limit])
