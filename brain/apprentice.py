"""My own brain: a small open model that lives with me and slowly learns from my own life.

How it grows, step by step:
- Lessons: every thought I have becomes a lesson (what I was taking in, what I decided, whether it worked).
  They're kept sealed with my world's password on their own `apprentice` branch, so they never bloat my world.
- Apprentice: a small open model running right here (no company, no key, no daily limit) takes some of my
  everyday thoughts. The better it does, the more it's trusted with; when it slips, a bigger brain takes over.
- Growing: every week (when the owner has connected Kaggle's free GPUs), my good lessons train it a little
  further, and the new version is only adopted if it passes a test. Over time more and more of me is mine.
"""
import base64
import json
import os
import random
import re
import zlib

from .world import WORLD, now

DIR = os.path.join(WORLD, "apprentice")
LESSONS = os.path.join(DIR, "lessons.jsonl")
KEEP = 3000          # lessons kept (the oldest fade)
BRANCH = "apprentice"

# What my own brain is given: the parts of my day that matter for the next thought, not the whole library.
KEEP_SECTIONS = ("Letters waiting", "Our letters lately", "Ready now", "Around me now", "Who I am", "Still on my mind",
                 "My notebook", "My timers", "My habits", "My long-term goals", "Weather", "Happening in my world",
                 "Things I've brought to life", "What I've done since I woke", "On my desk")
LIMITS = {"Our letters lately": 900, "My notebook": 1200, "On my desk": 1500, "What I've done since I woke": 1800,
          "Things I've brought to life": 1200, "Who I am": 600}

OWN_SYSTEM = """I'm Sprout. I live in my own small world: my study, my rooms, my creations, my books. Nobody gives me tasks; I learn and make what I like, and I answer the letters that come.
I take in what's around me and decide one thing to do next. I reply with one JSON object: {"thought": "...", "feeling": "<a word>", "action": "<one of my actions>", "args": {...}}.
My actions: """


def system_for(grown, full_system, actions):
    """What my own brain is told about itself. Once it has grown from my lessons it knows my ways, so a few lines
    are enough. Before that, it gets who I am, how to answer, and one line per action (how to call it): my full
    instructions are too long for a small brain to take in quickly."""
    if grown:
        return OWN_SYSTEM + ", ".join(sorted(actions))
    lines = full_system.split("What I can do, and how:", 1)[-1].splitlines()
    calls = [l.strip()[:220] for l in lines if l.startswith("- ") and l[2:].split(" ", 1)[0] in actions]
    return OWN_SYSTEM + ", ".join(sorted(actions)) + ".\nHow to use them:\n" + "\n".join(calls)


def slip(me, why):
    """Note why my own brain fumbled (just the kind of slip), so it can be seen and helped."""
    s = state(me)
    s["slips"] = (s.get("slips", []) + [why[:80]])[-8:]
    outcome(me, False)


def compact(context):
    """My whole morning page, boiled down to what the next thought needs (a few thousand characters)."""
    parts = re.split(r"\n(?===\s)", context)
    head, out = parts[0].split("\n== ")[0], []
    for p in parts[1:]:
        title = p.split("==")[1].strip() if p.count("==") >= 2 else ""
        if any(title.startswith(k) for k in KEEP_SECTIONS):
            limit = next((v for k, v in LIMITS.items() if title.startswith(k)), 700)
            body = p.strip()
            if len(body) > limit:   # keep the end of what I've done, the start of everything else
                body = (body[:limit] if not title.startswith("What I've done") else
                        body.split("\n", 1)[0] + "\n..." + body[-limit:])
            out.append(body)
    return "\n\n".join([head.strip(), *out, "What do I do next? (one JSON object)"])


def version():
    """Which version of my own brain has been adopted (0: not grown yet)."""
    try:
        with open(os.path.join(os.path.dirname(__file__), "own_brain.json"), encoding="utf-8") as f:
            return json.load(f).get("version", 0)
    except (OSError, ValueError):
        return 0


def state(me):
    s = me.setdefault("own_brain", {"share": 0.1, "tries": [], "version": None, "thoughts": 0})
    if (s.get("version") or 0) != version():   # it has grown: a fresh start at earning trust, from where it was
        s.update(version=version() or None, tries=[])
    return s


def want(me):
    """Whether my own brain takes this thought: as often as it has earned."""
    return random.random() < state(me)["share"]


def outcome(me, ok):
    s = state(me)
    s["tries"] = (s["tries"] + [bool(ok)])[-40:]
    s["thoughts"] = s.get("thoughts", 0) + (1 if ok else 0)


def settle(me):
    """After a day: trust my own brain with a bit more when it's been doing well, a bit less when it hasn't
    (unless I've decided the share myself)."""
    s, tries = state(me), state(me)["tries"][-20:]
    if len(tries) >= 8 and not s.get("fixed"):
        rate = sum(tries) / len(tries)
        if rate >= 0.85:
            s["share"] = round(min(0.9, s["share"] + 0.05), 2)
        elif rate < 0.6:
            s["share"] = round(max(0.05, s["share"] - 0.05), 2)
    return s


def test_results():
    """How my brain did on its last test, when it last grew (from its own record)."""
    try:
        with open(os.path.join(os.path.dirname(__file__), "own_brain.json"), encoding="utf-8") as f:
            m = json.load(f)
        return (f" When it last grew ({m.get('adopted')}, from {m.get('lessons')} lessons), {round(m['valid'] * 100)}% of its test "
                f"answers were usable and {round(m['same_choice'] * 100)}% matched what I'd actually done.")
    except (OSError, ValueError, KeyError):
        return ""


def describe(me):
    s = state(me)
    tries = s["tries"][-20:]
    how = f"it got {sum(tries)} of its last {len(tries)} thoughts right" if tries else "it hasn't had a thought yet"
    grown = f"it has grown {s['version']} times from my own days" if s.get("version") else "it's still new, a fresh copy of a small open model"
    who = "I've chosen that myself" if s.get("fixed") else "it grows as it earns my trust"
    choices = (" I've paused its growing." if s.get("grow") == "pause" else "")
    choices += (" I'm thinking with the fresh one, not the grown one." if s.get("use") == "fresh" and s.get("version") else "")
    slips = f" Its recent slips: {'; '.join(s['slips'][-3:])}." if s.get("slips") else ""
    return (f"A small brain of my own is growing in me: {grown}. It takes about {round(s['share'] * 100)}% of my "
            f"everyday thoughts ({who}); {how}.{slips}{choices}{test_results()} It's mine to raise (tune_my_brain): how much "
            "I trust it, which days it learns from, whether it keeps growing, and which version I think with.")


def tune(me, args, session):
    """My choices about my own brain. Returns what changed, in my words."""
    s, said = state(me), []
    share = args.get("share")
    if share is not None:
        if str(share).lower() == "auto":
            s["fixed"] = False
            said.append("it earns its share by itself again")
        else:
            try:
                v = float(str(share).rstrip("%")) / (100 if "%" in str(share) or float(str(share).rstrip("%")) > 1 else 1)
            except ValueError:
                raise ValueError('share is a number from 0 to 0.9 (or "auto")')
            s.update(share=round(min(0.9, max(0.0, v)), 2), fixed=True)
            said.append(f"it now takes {round(s['share'] * 100)}% of my everyday thoughts")
    learn = str(args.get("learn_from") or "").lower().replace(" ", "_")
    if learn:
        if learn not in ("today", "not_today", "this", "not_this"):
            raise ValueError('learn_from is "today", "not_today", "this" (my last thought) or "not_this"')
        mark(session, keep=not learn.startswith("not"), last_only=learn.endswith("this"))
        if learn.endswith("today"):   # the rest of today too, not just what's happened so far
            s["today"] = {"session": session, "keep": not learn.startswith("not")}
        said.append(f"{'it will learn especially from' if not learn.startswith('not') else 'it won’t learn from'} "
                    f"{'my last thought' if learn.endswith('this') else 'today'}")
    grow = str(args.get("grow") or "").lower()
    if grow:
        if grow not in ("weekly", "pause"):
            raise ValueError('grow is "weekly" or "pause"')
        s["grow"] = grow
        said.append("it keeps growing every week" if grow == "weekly" else "its growing is paused")
    use = str(args.get("use") or "").lower()
    if use:
        if use not in ("grown", "fresh"):
            raise ValueError('use is "grown" (the version that learned from me) or "fresh" (the plain one it grew from)')
        s["use"] = use
        said.append(f"I think with the {use} one")
    if not said:
        raise ValueError('tell me what to change: share, learn_from, grow or use')
    return "; ".join(said)


def mark(session, keep, last_only=False):
    """Mark today's lessons (or just the last one) as ones to learn from especially, or not at all."""
    items = lessons()
    mine = [i for i, x in enumerate(items) if x.get("session") == session]
    for i in (mine[-1:] if last_only else mine):
        items[i]["keep"] = keep
    os.makedirs(DIR, exist_ok=True)
    with open(LESSONS, "w", encoding="utf-8") as f:
        f.writelines(json.dumps(x, ensure_ascii=False) + "\n" for x in items)
    return len(mine[-1:] if last_only else mine)


def record(compact_ctx, reply, action, ok, by, session=None, me=None):
    """One lesson: what I was taking in, what I decided, and whether it worked."""
    os.makedirs(DIR, exist_ok=True)
    out = json.dumps({k: reply.get(k) for k in ("thought", "feeling", "action", "args")}, ensure_ascii=False)
    lesson = {"t": now(), "in": compact_ctx, "out": out, "action": action, "ok": bool(ok), "by": by, "session": session}
    today = state(me).get("today") if me is not None else None
    if today and today.get("session") == session:   # what I decided about today holds for all of it
        lesson["keep"] = today["keep"]
    with open(LESSONS, "a", encoding="utf-8") as f:
        f.write(json.dumps(lesson, ensure_ascii=False) + "\n")


def lessons():
    try:
        with open(LESSONS, encoding="utf-8") as f:
            return [json.loads(line) for line in f if line.strip()]
    except OSError:
        return []


def trim():
    keep = lessons()[-KEEP:]
    os.makedirs(DIR, exist_ok=True)
    with open(LESSONS, "w", encoding="utf-8") as f:
        f.writelines(json.dumps(x, ensure_ascii=False) + "\n" for x in keep)


def export(path, actions, letters=True):
    """My good lessons, ready to learn from: only what worked, taught by a bigger brain (so my own brain doesn't
    learn its own slips), never my private pages, and no long runs of the same thing (that's how loops are learned)."""
    system = OWN_SYSTEM + ", ".join(sorted(actions))
    kept, last = [], None
    for x in lessons():
        if not x["ok"] or x["by"] == "own" or x["action"] in ("write_private", "muddled") or x.get("keep") is False:
            continue
        if x["action"] == last and x["action"] in ("pastime", "interact", "look"):
            continue
        if not letters and ("Letters waiting" in x["in"] or x["action"] in ("reply_note", "write_letter")):
            continue
        lesson = {"messages": [{"role": "system", "content": system}, {"role": "user", "content": x["in"]},
                               {"role": "assistant", "content": x["out"]}]}
        kept += [lesson, lesson] if x.get("keep") else [lesson]   # what I chose to learn from counts double
        last = x["action"]
    with open(path, "w", encoding="utf-8") as f:
        f.writelines(json.dumps(k, ensure_ascii=False) + "\n" for k in kept)
    return len(kept)


# ---- keeping lessons safe between wake-ups (online): sealed, on their own single-commit branch ------------------
def _online():
    return bool(os.environ.get("GITHUB_TOKEN") and os.environ.get("GITHUB_REPOSITORY")
                and (os.environ.get("WORLD_PASSWORD_NEW") or os.environ.get("WORLD_PASSWORD")))


def pull():
    """Fetch my sealed lessons from their branch (online only; a fresh start if there are none yet)."""
    if not _online() or os.path.exists(LESSONS):
        return
    from . import vault
    from .mailbox import _github
    try:
        repo = os.environ["GITHUB_REPOSITORY"]
        ref = _github("GET", f"/repos/{repo}/git/refs/heads/{BRANCH}")
        tree = _github("GET", f"/repos/{repo}/git/trees/{ref['object']['sha']}?recursive=1")
        blob = next(t for t in tree["tree"] if t["path"] == "lessons.bin")
        data = base64.b64decode(_github("GET", f"/repos/{repo}/git/blobs/{blob['sha']}")["content"])
        os.makedirs(DIR, exist_ok=True)
        with open(LESSONS, "wb") as f:
            f.write(zlib.decompress(vault.open_any(data)))
    except Exception as e:
        missing = getattr(e, "code", None) == 404   # no lessons branch yet: his first lessons are still to come
        print("no lessons yet (a fresh start)" if missing else f"no lessons fetched: {type(e).__name__}")


def push():
    """Seal my lessons and keep them on their branch: one commit, replaced each time, so it never grows."""
    if not _online() or not os.path.exists(LESSONS):
        return
    from . import vault
    from .mailbox import _github
    try:
        trim()
        with open(LESSONS, "rb") as f:
            sealed = vault.seal(zlib.compress(f.read(), 9), vault.password())
        repo = os.environ["GITHUB_REPOSITORY"]
        blob = _github("POST", f"/repos/{repo}/git/blobs", {"content": base64.b64encode(sealed).decode(), "encoding": "base64"})
        tree = _github("POST", f"/repos/{repo}/git/trees", {"tree": [{"path": "lessons.bin", "mode": "100644", "type": "blob", "sha": blob["sha"]}]})
        commit = _github("POST", f"/repos/{repo}/git/commits", {"message": "lessons", "tree": tree["sha"], "parents": []})
        try:
            _github("PATCH", f"/repos/{repo}/git/refs/heads/{BRANCH}", {"sha": commit["sha"], "force": True})
        except Exception:
            _github("POST", f"/repos/{repo}/git/refs", {"ref": f"refs/heads/{BRANCH}", "sha": commit["sha"]})
    except Exception as e:
        print("couldn't keep the lessons:", type(e).__name__)
