"""Music the AI composes. The web page plays it.

Notes are written as NOTE+OCTAVE:BEATS separated by spaces, e.g. "C4:1 E4:1 G4:2 R:1 A#3:0.5"
(R is a rest; # sharp, b flat). An optional second voice ("bass") plays alongside the melody.
"""
import re

from .world import now, slug

TOKEN = re.compile(r"^(R|[A-Ga-g][#b]?[0-8]):(\d+(?:\.\d+)?)$")
INSTRUMENTS = {"sine", "triangle", "square", "sawtooth", "piano", "organ", "flute"}


def _voice(text, what):
    if not text:
        return ""
    tokens = str(text).split()
    if len(tokens) > 400:
        raise ValueError(f"the {what} is too long (at most 400 notes)")
    for t in tokens:
        m = TOKEN.match(t)
        if not m or not 0 < float(m.group(2)) <= 16:
            raise ValueError(f"can't read '{t}' in the {what}: write notes like C4:1, F#3:0.5 or R:2 (a rest)")
    return " ".join(tokens)


def compose(world, args):
    title = str(args.get("title", "")).strip()
    melody = _voice(args.get("melody") or args.get("notes"), "melody")
    if not title or not melody:
        raise ValueError("a piece needs a title and a melody")
    piece = {
        "id": slug(title), "title": title[:80], "about": str(args.get("about", ""))[:400],
        "tempo": min(max(int(float(args.get("tempo", 100))), 30), 240),
        "instrument": args.get("instrument") if args.get("instrument") in INSTRUMENTS else "piano",
        "melody": melody, "bass": _voice(args.get("bass"), "bass"), "composed": now(),
    }
    old = next((p for p in world.music if p["id"] == piece["id"]), None)
    if old:
        old.update(piece, revised=now())
        return old, True
    world.music.append(piece)
    return piece, False
