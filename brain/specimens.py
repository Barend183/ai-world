"""Specimens: anything the AI brings to life in its world from what it has learned.

A plant, an animal, a model train, a car, a loaf of bread in the oven... The AI writes the
rules itself (based on one of its books); this module checks them and runs them.

Time: every real hour is one hour for the specimen, so slow things really are slow and seasons
follow the real calendar. An action can also make time pass quickly ("bake for 30 minutes").

A spec looks like:
  {"name": "Sourdough loaf", "kind": "food", "facts": ["..."],
   "look": {"shape": "dome", "color": "#c98a4a", ...}   or   "sprite": {"palette": {...}, "pixels": [...]},
   "vars": {"doneness": {"start": 0, "min": 0, "max": 100, "per_hour": 0, "unit": "%"}, ...},
   "seasons": [{"name": "growing", "months": [4, 5, 6], "per_day": {...}}],
   "rules": [{"if": "oven_temp > 200", "per_hour": {"doneness": 150}, "note": "crust browning"}],
   "actions": {"bake": [{"change": {"oven_temp": 230}, "minutes": 30, "say": "..."}]},
   "moves_when": "speed > 0", "alive_var": "health", "end_word": "burnt"}
Conditions are tiny: "<var> <|<=|>|>=|==|!= <number>" or "season is <name>", joined with "and".
"""
import re
from datetime import datetime, timedelta, timezone

from .env import NAMES as ENV_NAMES, _chance
from .world import now, slug

# The world's weather (env.Weather), set when the AI wakes; without it conditions are mild and dry.
WEATHER = None

MAX_PER_ROOM = 6
SENSES = ("smell", "taste", "touch")
KINDS = {"plant", "animal", "food", "vehicle", "machine", "object", "creature", "other"}
SHAPES = {"dome", "round", "tall", "long", "bush", "blob", "crystal", "box"}
TEXTURES = {"smooth", "cracked", "furry", "scaly", "spotted", "striped", "leafy", "shiny"}
PARTS = {"vine", "leaves", "flowers", "legs", "wings", "tail", "ears", "eyes", "spikes", "shell", "antennae",
         "wheels", "windows", "chimney", "lights", "steam", "plate", "pot"}
COLOR = re.compile(r"^#[0-9a-fA-F]{6}$")
NAME = re.compile(r"^[a-z][a-z0-9_]{0,23}$")
CLAUSE = re.compile(r"^\s*(?:season\s+is\s+([a-z0-9_ -]+?)|([a-z][a-z0-9_]*(?:\.[a-z][a-z0-9_]*)?)\s*(<=|>=|==|!=|<|>)\s*(-?\d+(?:\.\d+)?))\s*$", re.I)
OTHER = re.compile(r"^[a-z][a-z0-9_]*\.[a-z][a-z0-9_]*$")   # another creation's variable: king_protea.nectar

# The world the creations live in, set when the AI wakes, so they can affect each other.
WORLD = None
OPS = {"<": float.__lt__, "<=": float.__le__, ">": float.__gt__, ">=": float.__ge__,
       "==": lambda a, b: abs(a - b) < 1e-9, "!=": lambda a, b: abs(a - b) >= 1e-9}


class SpecError(ValueError):
    pass


def _num(v, what):
    try:
        return float(v)
    except (TypeError, ValueError):
        raise SpecError(f"{what} must be a number")


def _rates(d, vars_, what):
    """Accepts per_day and/or per_hour; stores everything per day."""
    out = {}
    for unit, mult in (("per_day", 1), ("per_hour", 24)):
        part = d.get(unit) or {}
        if not isinstance(part, dict):
            raise SpecError(f"{what}.{unit} must be an object of variable: number")
        for k, v in part.items():
            if k not in vars_ and not OTHER.match(k):
                raise SpecError(f"{what} mentions '{k}', which isn't one of its variables (another creation's is written like king_protea.nectar)")
            out[k] = out.get(k, 0) + _num(v, f"{what}.{k}") * mult
    return out


def _changes(d, vars_, what):
    if not isinstance(d, dict):
        raise SpecError(f"{what} must be an object of variable: number")
    for k in d:
        if k not in vars_:
            raise SpecError(f"{what} mentions '{k}', which isn't one of its variables")
    return {k: _num(v, f"{what}.{k}") for k, v in d.items()}


def condition(text, vars_, seasons):
    if text in (None, ""):
        return ""
    for clause in str(text).split(" and "):
        m = CLAUSE.match(clause)
        if not m:
            raise SpecError(f"can't understand the condition '{clause.strip()}'")
        if m.group(1) and m.group(1).strip().lower() not in seasons:
            raise SpecError(f"condition mentions season '{m.group(1)}', which isn't defined")
        if m.group(2) and m.group(2) not in vars_ and m.group(2) not in ENV_NAMES and not OTHER.match(m.group(2)):
            raise SpecError(f"condition mentions '{m.group(2)}', which isn't one of its variables or {', '.join(ENV_NAMES)}")
    return str(text)


def sprite(raw, vars_=None, seasons=()):
    """Pixel art drawn by the AI: a palette of one-letter colours and rows of letters ('.' is see-through).
    Optional "states" swap in other drawings while a condition holds (flowering, dormant, rusty...),
    and "size_var" scales it with a variable, so a growing thing gets bigger on screen."""
    if not raw:
        return None
    if not isinstance(raw, dict) or not isinstance(raw.get("palette"), dict) or not isinstance(raw.get("pixels"), list):
        raise SpecError('a sprite needs {"palette": {"a": "#rrggbb", ...}, "pixels": ["..aa..", ...]}')
    palette = {k: v for k, v in raw["palette"].items() if len(k) == 1 and k != "." and isinstance(v, str) and COLOR.match(v)}
    if not palette:
        raise SpecError("the sprite's palette needs one-letter keys with #rrggbb colours")

    def rows(px):
        px = [str(r)[:80] for r in px[:64]]
        if not px or not any(set(r) - {".", " "} for r in px):
            raise SpecError("the sprite's pixels are empty")
        return px
    out = {"palette": palette, "pixels": rows(raw["pixels"])}
    states = []
    for s in (raw.get("states") or [])[:4]:
        if vars_ is not None and isinstance(s, dict) and s.get("pixels"):
            states.append({"if": condition(s.get("if"), vars_, seasons), "pixels": rows(s["pixels"])})
    if states:
        out["states"] = states
    if vars_ and raw.get("size_var") in vars_:   # the drawing grows with this variable (half size at its min)
        out["size_var"] = raw["size_var"]
    return out


def validate(spec):
    """Check and tidy a spec written by the AI. Raises SpecError with a plain explanation."""
    if not isinstance(spec, dict):
        raise SpecError("the specimen must be a JSON object")
    name = str(spec.get("name", "")).strip()
    if not name:
        raise SpecError("the specimen needs a name")
    kind = str(spec.get("kind", "other")).lower()
    kind = kind if kind in KINDS else "other"

    raw_vars = spec.get("vars")
    if not isinstance(raw_vars, dict) or not raw_vars:
        raise SpecError("it needs some variables (vars), e.g. water, health, fuel, temperature")
    vars_ = {}
    for k, v in list(raw_vars.items())[:12]:
        if not NAME.match(k):
            raise SpecError(f"variable names must be short lowercase words, not '{k}'")
        if not isinstance(v, dict):
            raise SpecError(f"variable '{k}' must be an object with start/min/max")
        lo, hi = _num(v.get("min", 0), f"{k}.min"), _num(v.get("max", 100), f"{k}.max")
        if hi <= lo:
            raise SpecError(f"variable '{k}' needs max bigger than min")
        vars_[k] = {"start": min(max(_num(v.get("start", lo), f"{k}.start"), lo), hi), "min": lo, "max": hi,
                    "per_day": _num(v.get("per_day", 0), f"{k}.per_day") + 24 * _num(v.get("per_hour", 0), f"{k}.per_hour"),
                    "unit": str(v.get("unit", ""))[:12]}

    seasons, names = [], set()
    for s in (spec.get("seasons") or [])[:6]:
        sname = str(s.get("name", "")).strip().lower()
        months = [int(m) for m in s.get("months", []) if str(m).isdigit() and 1 <= int(m) <= 12]
        if not sname or not months:
            raise SpecError("each season needs a name and a list of months (1-12)")
        seasons.append({"name": sname, "months": months, "per_day": _rates(s, vars_, f"season {sname}")})
        names.add(sname)

    rules = []
    for r in (spec.get("rules") or [])[:20]:
        rule = {"if": condition(r.get("if"), vars_, names), "per_day": _rates(r, vars_, "rule"), "note": str(r.get("note", ""))[:120]}
        if r.get("chance") not in (None, ""):   # a random event: "chance" per day, then "change" happens at once
            rule["chance"] = min(max(_num(r["chance"], "chance"), 0.0), 1.0)
            rule["change"] = _changes(r.get("change", {}), vars_, "rule change")
        rules.append(rule)

    actions = {}
    for aname, branches in list((spec.get("actions") or {}).items())[:10]:
        aname = str(aname).strip().lower().replace(" ", "_")
        if not NAME.match(aname) or aname == "observe":
            raise SpecError(f"action names must be short lowercase words, not '{aname}'")
        branches = [branches] if isinstance(branches, dict) else branches
        out = [{"if": condition(b.get("if"), vars_, names), "change": _changes(b.get("change", {}), vars_, f"action {aname}"),
                "minutes": min(max(int(_num(b.get("minutes", 0), f"{aname}.minutes")), 0), 1440),
                "say": str(b.get("say", ""))[:240]} for b in branches[:4] if isinstance(b, dict)]
        if out:
            actions[aname] = out

    look = spec.get("look") or {}
    col = lambda c, d: c if isinstance(c, str) and COLOR.match(c) else d
    look = {
        "shape": look.get("shape") if look.get("shape") in SHAPES else "round",
        "color": col(look.get("color"), "#8a6a4a"),
        "texture": look.get("texture") if look.get("texture") in TEXTURES else "smooth",
        "parts": [p for p in look.get("parts", []) if p in PARTS][:8],
        "part_color": col(look.get("part_color"), "#4f9a49"),
        "size_var": look.get("size_var") if look.get("size_var") in vars_ else None,
        "lush_var": look.get("lush_var") if look.get("lush_var") in vars_ else None,
    }
    alive = spec.get("alive_var") if spec.get("alive_var") in vars_ else None
    senses = []
    for r in (spec.get("senses") or [])[:12]:
        if isinstance(r, dict):
            entry = {"if": condition(r.get("if"), vars_, names)}
            entry.update({k: str(r[k])[:200] for k in SENSES if r.get(k)})
            if len(entry) > 1:
                senses.append(entry)
    return {"name": name[:80], "kind": kind, "look": look, "sprite": sprite(spec.get("sprite"), vars_, names),
            "vars": vars_, "seasons": seasons, "rules": rules, "actions": actions, "alive_var": alive,
            "end_word": str(spec.get("end_word") or ("died" if kind in ("plant", "animal", "creature") else "broke"))[:20],
            "moves_when": condition(spec.get("moves_when"), vars_, names) if spec.get("moves_when") else None,
            "facts": [str(f)[:200] for f in (spec.get("facts") or [])[:8]], "senses": senses}


# ---- running a specimen ------------------------------------------------------
def season_at(spec, when):
    for s in spec["seasons"]:
        if when.month in s["months"]:
            return s
    return None


def env_at(sp, t):
    """The conditions around a specimen at time t: weather (if outdoors), daylight, its age."""
    e = WEATHER.at(t, sp.get("outdoors", False)) if WEATHER else {
        "env_temp": 21.0, "env_rain": 0.0, "env_humidity": 50, "env_wind": 0, "env_daylight": 1,
        "env_hour": (t.hour + 2) % 24, "env_month": t.month}
    e["age_days"] = round((t - datetime.fromisoformat(sp.get("born", sp["updated"]))).total_seconds() / 86400, 2)
    from . import events   # storms reach indoors too (as noise and draughts); a power cut stops anything electric
    e["env_storm"] = 1 if WEATHER and events.stormy(WEATHER, t) else 0
    e["env_power"] = 1 if events.power_on(WORLD, t) else 0
    return e


def holds(cond, values, season):
    if not cond:
        return True
    for clause in cond.split(" and "):
        m = CLAUSE.match(clause)
        if m.group(1):
            if not season or season["name"] != m.group(1).strip().lower():
                return False
        elif m.group(2) not in values or not OPS[m.group(3)](float(values[m.group(2)]), float(m.group(4))):
            return False
    return True


def _clamp(spec, values):
    for k, v in spec["vars"].items():
        values[k] = round(min(max(values[k], v["min"]), v["max"]), 4)


def _key(sp):
    return sp["id"].replace("-", "_")


def _others(world, sp):
    """The other living creations' variables, as king_protea.nectar, plus where to send changes."""
    scope, owners = {}, {}
    for o in (world.specimens if world else []):
        if o is not sp and o["status"] == "alive":
            owners[_key(o)] = o
            for k, v in o["values"].items():
                scope[f"{_key(o)}.{k}"] = v
    return scope, owners


def _step(sp, t, step, world=None):
    spec, values = sp["spec"], sp["values"]
    season = season_at(spec, t)
    others, owners = _others(world, sp)
    scope = {**others, **values, **env_at(sp, t)}
    rate = {k: v["per_day"] for k, v in spec["vars"].items()}
    for k, d in (season["per_day"] if season else {}).items():
        rate[k] = rate.get(k, 0) + d
    for i, r in enumerate(spec["rules"]):
        if not holds(r["if"], scope, season):
            continue
        for k, d in r["per_day"].items():
            rate[k] = rate.get(k, 0) + d
        if r.get("chance") and _chance(sp["id"], t.isoformat(), i) < r["chance"] * step / 1440:
            for k, d in r["change"].items():
                values[k] = values.get(k, 0) + d
            sp.setdefault("events", []).append({"t": t.isoformat(timespec="minutes"), "note": r["note"] or "something happened"})
            sp["events"] = sp["events"][-12:]
    for k, d in rate.items():
        if "." in k:   # an effect on another creation
            who, var = k.split(".", 1)
            o = owners.get(who)
            if o and var in o["values"]:
                o["values"][var] += d * step / 1440
                _clamp(o["spec"], o["values"])
                _check_end(o, t)
        elif k in values:
            values[k] += d * step / 1440
    _clamp(spec, values)
    _check_end(sp, t)


def advance_all(world, until=None):
    """Every living creation moves forward together, hour by hour, so they can affect one another."""
    until = until or datetime.now(timezone.utc)
    alive = [s for s in world.specimens if s["status"] == "alive"]
    if not alive:
        return
    t = max(min(datetime.fromisoformat(s["updated"]) for s in alive), until - timedelta(days=60))
    while t + timedelta(hours=1) <= until:
        t += timedelta(hours=1)
        for sp in alive:
            if sp["status"] == "alive" and datetime.fromisoformat(sp["updated"]) < t:
                _step(sp, t, 60, world)
                sp["updated"] = t.isoformat(timespec="seconds")
    for sp in world.specimens:
        if sp["status"] != "released":
            _refresh(sp, until)


def _live(sp, start, minutes, step):
    """Run the rules forward from `start` for `minutes`, in steps of `step` minutes."""
    spec, values, t = sp["spec"], sp["values"], start
    for _ in range(int(minutes // step)):
        if sp["status"] != "alive":
            break
        t += timedelta(minutes=step)
        _step(sp, t, step, WORLD if sp.get("id") != "test" and any(o is sp for o in (WORLD.specimens if WORLD else [])) else None)
    return t


def advance(sp, until=None):
    """Live the specimen forward in real time, hour by hour, up to now (at most 60 days per call)."""
    until = until or datetime.now(timezone.utc)
    start = max(datetime.fromisoformat(sp["updated"]), until - timedelta(days=60))
    t = _live(sp, start, (until - start).total_seconds() // 60, 60)
    sp["updated"] = (t if sp["status"] == "alive" else until).isoformat(timespec="seconds")
    _refresh(sp, until)


def _check_end(sp, when):
    a = sp["spec"]["alive_var"]
    if a and sp["values"][a] <= sp["spec"]["vars"][a]["min"] and sp["status"] == "alive":
        sp["status"] = "dead"
        sp["died"] = when.isoformat(timespec="seconds")


def _refresh(sp, when):
    spec = sp["spec"]
    values = {**sp["values"], **env_at(sp, when)}
    season = season_at(spec, when)
    sp["season"] = season["name"] if season else None
    sp["signs"] = [r["note"] for r in spec["rules"] if r["note"] and not r.get("chance") and holds(r["if"], values, season)]
    sp["moving"] = bool(spec.get("moves_when")) and sp["status"] == "alive" and holds(spec["moves_when"], values, season)
    states = (spec.get("sprite") or {}).get("states", [])
    sp["state_sprite"] = next((i for i, s in enumerate(states) if holds(s["if"], values, season)), None)


def interact(sp, action):
    name = sp["spec"]["name"]
    if sp["status"] != "alive" and action not in ("observe", *SENSES):
        return f"{name} has {sp['spec']['end_word']}; nothing more can be done with it."
    if WORLD and any(o is sp for o in WORLD.specimens):
        advance_all(WORLD)
    else:
        advance(sp)
    if action == "observe":
        return describe(sp)
    if action in SENSES:
        return sense(sp, action)
    branches = sp["spec"]["actions"].get(action)
    if not branches:
        raise SpecError(f"{name} has no action '{action}'. It has: {', '.join(sp['spec']['actions']) or 'none'}")
    t = datetime.now(timezone.utc)
    scope = {**sp["values"], **env_at(sp, t)}
    branch = next((b for b in branches if holds(b["if"], scope, season_at(sp["spec"], t))), None)
    if not branch:
        return "Nothing happened."
    for k, d in branch["change"].items():
        sp["values"][k] += d
    _clamp(sp["spec"], sp["values"])
    _check_end(sp, t)
    if branch["minutes"]:
        # Fast-forward this specimen only; its real-time clock carries on afterwards.
        _live(sp, t, branch["minutes"], 1 if branch["minutes"] <= 240 else 10)
    _refresh(sp, t)
    sp["interactions"] = sp.get("interactions", 0) + 1
    waited = f" ({branch['minutes']} minutes pass.)" if branch["minutes"] else ""
    return (branch["say"] or f"You {action.replace('_', ' ')} it.") + waited + " " + describe(sp)


def forecast(sp, days=30):
    """What happens if nobody touches it: lets the AI check its rules make sense."""
    import copy
    ghost = copy.deepcopy(sp)
    start = datetime.now(timezone.utc)
    marks = []
    for d in (1, 7, days):
        advance(ghost, start + timedelta(days=d))
        if ghost["status"] != "alive":
            ended = datetime.fromisoformat(ghost["died"])
            return (f"Forecast if left alone: it {sp['spec']['end_word']} after {max(1, round((ended - start).total_seconds() / 86400))} "
                    f"day(s). {describe(ghost)}")
        marks.append(f"day {d}: " + ", ".join(f"{k} {ghost['values'][k]:g}" for k in sp["spec"]["vars"]))
    return "Forecast if left alone: " + " | ".join(marks) + (f". Signs then: {'; '.join(ghost['signs'])}" if ghost["signs"] else "")


def outlook(sp, days=30):
    """One line about where it's heading if nobody tends it (empty when it's fine for a month)."""
    if sp["status"] != "alive":
        return ""
    text = forecast(sp, days)
    m = re.search(r"after (\d+) day", text)
    return f"Outlook if left untended: {sp['spec']['end_word']} in about {m.group(1)} days." if m else ""


def simulate(sp, days=30, care=()):
    """A test run on a copy: lives `days` ahead under a care plan, without touching the real one.
    care: [{"action": "water", "every_days": 3}, ...]"""
    import copy
    ghost = copy.deepcopy(sp)
    ghost["events"] = []
    days = min(max(float(days), 0.1), 365)
    start = t = datetime.now(timezone.utc)
    plan = []
    for c in care or []:
        branches = ghost["spec"]["actions"].get(str(c.get("action", "")))
        if not branches:
            raise SpecError(f"it has no action '{c.get('action')}'. It has: {', '.join(ghost['spec']['actions']) or 'none'}")
        plan.append((branches, max(_num(c.get("every_days", 1), "every_days"), 1 / 24), c["action"]))
    next_due = [start] * len(plan)
    marks, checkpoints = [], sorted({1, 7, 30, 90, 180, 365, days} & set(range(0, 366)) | {days})
    checkpoints = [d for d in checkpoints if d <= days]
    done_care = {}
    for d in checkpoints:
        until = start + timedelta(days=d)
        while t < until and ghost["status"] == "alive":
            for i, (branches, every, name) in enumerate(plan):
                if t >= next_due[i]:
                    scope = {**ghost["values"], **env_at(ghost, t)}
                    b = next((b for b in branches if holds(b["if"], scope, season_at(ghost["spec"], t))), None)
                    if b:
                        for k, v in b["change"].items():
                            ghost["values"][k] += v
                        _clamp(ghost["spec"], ghost["values"])
                        _check_end(ghost, t)
                        if b["minutes"]:
                            _live(ghost, t, b["minutes"], 10)
                        done_care[name] = done_care.get(name, 0) + 1
                    next_due[i] = t + timedelta(days=every)
            step_end = min(until, t + timedelta(hours=6))
            t = _live(ghost, t, (step_end - t).total_seconds() // 60, 60)
            if (step_end - t).total_seconds() >= 60 and ghost["status"] == "alive":
                t = step_end
        _refresh(ghost, t)
        if ghost["status"] != "alive":
            ended = datetime.fromisoformat(ghost["died"])
            marks.append(f"it {sp['spec']['end_word']} on day {max(1, round((ended - start).total_seconds() / 86400))}")
            break
        marks.append(f"day {d:g} ({ghost['season'] or 'no season'}): " + ", ".join(f"{k} {ghost['values'][k]:.4g}" for k in sp["spec"]["vars"])
                     + (f" [{'; '.join(ghost['signs'])}]" if ghost["signs"] else ""))
    events = {}
    for e in ghost.get("events", []):
        events[e["note"]] = events.get(e["note"], 0) + 1
    care_text = ", ".join(f"{n}x {a}" for a, n in done_care.items()) or "no care"
    return (f"Test run of {sp['spec']['name']} with {care_text}: " + " | ".join(marks)
            + (f". Random events: {', '.join(f'{k} ({v}x)' for k, v in events.items())}" if events else ""))


def sense(sp, which):
    """What it smells, tastes or feels like right now, by the senses its maker gave it."""
    t = datetime.now(timezone.utc)
    scope = {**sp["values"], **env_at(sp, t)}
    season = season_at(sp["spec"], t)
    found = [r[which] for r in sp["spec"].get("senses", []) if which in r and holds(r["if"], scope, season)]
    name = sp["spec"]["name"]
    if not found:
        return (f"You {which} {name}, but you haven't given it a {which} yet. Add senses to it (spawn it again with "
                f"\"senses\") from what you've learned about the real thing.")
    verb = {"smell": "smells", "taste": "tastes", "touch": "feels"}[which]
    return f"{name} {verb}: {found[0]}."   # the first entry that fits its state wins


def describe(sp):
    spec = sp["spec"]
    vals = ", ".join(f"{k} {sp['values'][k]:g}{v['unit'] and ' ' + v['unit']}" for k, v in spec["vars"].items())
    state = spec["end_word"] if sp["status"] == "dead" else ("in use" if spec["kind"] not in ("plant", "animal", "creature") else "alive")
    bits = [f"{spec['name']} ({state}{', ' + sp['season'] + ' season' if sp.get('season') else ''}): {vals}."]
    if sp.get("signs"):
        bits.append("You notice: " + "; ".join(s.rstrip(". ") for s in sp["signs"]) + ".")
    recent = [e["note"] for e in sp.get("events", []) if datetime.fromisoformat(e["t"]) > datetime.now(timezone.utc) - timedelta(days=3)]
    if recent:
        bits.append("Lately: " + "; ".join(recent) + ".")
    return " ".join(bits)


def spawn(world, spec, book_id, room_id=None, x=None):
    """Bring a specimen into a room, or update one with the same name (keeping its current state)."""
    spec = validate(spec)
    book = world.find_book(book_id or "")
    if not book and book_id:   # forgive a near miss: part of the title, or the id with a typo of case/spacing
        key = slug(str(book_id))
        book = next((b for b in world.shelves if key and (key in b["id"] or b["id"] in key)), None)
    if not book:
        have = ", ".join(b["id"] for b in world.shelves[-8:]) or "none yet: write one first"
        raise SpecError(f"a creation must be based on one of your books: give the book's id (yours include {have})")
    sid = slug(spec["name"])
    old = next((s for s in world.specimens if s["id"] == sid and s["status"] != "released"), None)
    room = world.room(room_id) if room_id else (world.room(old["room"]) if old else world.room("study"))
    if not room:
        raise SpecError(f"there's no room called '{room_id}'. Your rooms: {', '.join(r['id'] for r in world.rooms)}")
    here = [s for s in world.specimens if s["status"] != "released" and s.get("room") == room["id"] and s is not old]
    if len(here) >= MAX_PER_ROOM:
        raise SpecError(f"{room['name']} is full ({MAX_PER_ROOM} specimens); release one or build another room")
    place = min(max(float(x), 0.0), 1.0) if isinstance(x, (int, float)) else None
    t = now()
    if old:
        advance(old)
        values = {k: old["values"].get(k, v["start"]) for k, v in spec["vars"].items()}
        _clamp(spec, values)
        old.update(spec=spec, values=values, book=book["id"], revised=t, revisions=old.get("revisions", 0) + 1, room=room["id"],
                   outdoors=room.get("kind") == "outdoor")
        if place is not None:
            old["x"] = place
        _refresh(old, datetime.now(timezone.utc))
        return old, True
    sp = {"id": sid, "spec": spec, "book": book["id"], "room": room["id"], "x": place, "born": t, "updated": t,
          "outdoors": room.get("kind") == "outdoor",
          "status": "alive", "values": {k: v["start"] for k, v in spec["vars"].items()}, "interactions": 0}
    _refresh(sp, datetime.now(timezone.utc))
    if any(s["id"] == sid for s in world.specimens):  # an earlier one was released
        sp["id"] = f"{sid}-{len(world.specimens)}"
    world.specimens.append(sp)
    return sp, False


def release(sp):
    sp["status"] = "released"
    sp["released"] = now()
