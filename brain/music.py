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


SEMI = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}


def _freq(note):
    m = re.match(r"^([A-Ga-g])([#b]?)([0-8])$", note)
    if not m:
        return 0.0
    n = SEMI[m.group(1).upper()] + {"#": 1, "b": -1}.get(m.group(2), 0) + (int(m.group(3)) + 1) * 12
    return 440.0 * 2 ** ((n - 69) / 12)


def render_wav(piece, rate=16000, max_seconds=90):
    """The piece as a real sound file (16-bit mono WAV), so it can actually be listened to."""
    import io
    import math
    import struct
    import wave
    beat = 60.0 / piece.get("tempo", 100)
    inst = piece.get("instrument", "piano")
    voices = [(piece.get("melody", ""), 0.5), (piece.get("bass", ""), 0.3)]
    length = max(sum(float(t.split(":")[1]) for t in v.split()) for v, _ in voices if v) * beat + 1.0
    total = int(min(length, max_seconds) * rate)
    buf = [0.0] * total

    def wave_at(phase):
        x = phase % 1.0
        if inst in ("sine", "flute"):
            return math.sin(2 * math.pi * x)
        if inst in ("square", "organ"):
            return 0.6 if x < 0.5 else -0.6
        if inst == "sawtooth":
            return 0.7 * (2 * x - 1)
        return 4 * abs(x - 0.5) - 1   # triangle (and piano)

    for text, level in voices:
        t = 0.0
        for tok in text.split():
            note, beats = tok.split(":")
            dur = float(beats) * beat
            f = _freq(note) if note != "R" else 0.0
            if f:
                start = int(t * rate)
                ring = max(dur, 0.35) if inst == "piano" else dur
                for i in range(int(ring * rate)):
                    j = start + i
                    if j >= total:
                        break
                    s = i / rate
                    env = min(1.0, s / 0.01) * (math.exp(-3.0 * s) if inst == "piano" else (1.0 if s < dur - 0.03 else max(0.0, (dur - s) / 0.03)))
                    buf[j] += level * env * wave_at(f * s)
            t += dur
    peak = max(1e-9, max(abs(x) for x in buf))
    scale = 0.9 / peak if peak > 0.9 else 1.0
    out = io.BytesIO()
    with wave.open(out, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(b"".join(struct.pack("<h", int(max(-1, min(1, x * scale)) * 32000)) for x in buf))
    return out.getvalue()
