"""Timers and habits: two ways for time and routine to work without my having to think about them.

A timer lets real time pass for something I've set going (dough rising, paint drying, tea steeping): it's
waiting for me when it's done, and it can wake me. A habit is a little routine I write once, a list of simple
steps, that runs by itself whenever I wake up or go to bed, so my thoughts are free for what matters."""
import re
from datetime import datetime, timedelta, timezone

MAX_TIMERS = 8
MAX_HABITS = 6
MAX_STEPS = 8
# What a habit may do on its own: looking, tending, tidying, remembering. Nothing that writes, sends or publishes.
HABIT_ACTIONS = {"interact", "look", "move", "pastime", "remember", "set_alarm", "start_timer"}


def _now():
    return datetime.now(timezone.utc)


def _hours(args):
    for key, scale in (("hours", 1), ("minutes", 1 / 60), ("days", 24)):
        try:
            if args.get(key) not in (None, ""):
                return float(args[key]) * scale
        except (TypeError, ValueError):
            pass
    m = re.search(r"(\d+(?:\.\d+)?)\s*(h|hour|min|m|day|d)", str(args.get("for") or args.get("time") or ""))
    if m:
        unit = m.group(2)
        return float(m.group(1)) * (1 / 60 if unit.startswith("m") else 24 if unit.startswith("d") else 1)
    return None


# ---- timers --------------------------------------------------------------------------------------------
def start_timer(me, args):
    what = str(args.get("what") or args.get("name") or args.get("for_what") or args.get("activity") or "").strip()
    hours = _hours(args)
    if not what or not hours or hours <= 0:
        raise ValueError('a timer needs what it\'s for and how long: start_timer {"what": "dough rising", "hours": 4, "then": "shape it", "wake": true}')
    timers = me.setdefault("timers", [])
    if len(timers) >= MAX_TIMERS:
        raise ValueError(f"I already have {MAX_TIMERS} timers going; one has to finish first (or cancel_timer)")
    timer = {"id": f"t{(max((int(t['id'][1:]) for t in timers), default=0) + 1)}", "what": what[:120],
             "then": str(args.get("then") or "").strip()[:200], "started": _now().isoformat(timespec="seconds"),
             "done": (_now() + timedelta(hours=min(hours, 24 * 30))).isoformat(timespec="seconds"),
             "wake": str(args.get("wake", "")).lower() in ("true", "yes", "1")}
    timers.append(timer)
    return timer


def cancel_timer(me, args):
    key = str(args.get("id") or args.get("what") or "").strip().lower()
    timers = me.get("timers", [])
    found = next((t for t in timers if t["id"] == key or t["what"].lower() == key), None)
    if not found:
        raise ValueError("there's no timer like that; mine: " + (", ".join(f"[{t['id']}] {t['what']}" for t in timers) or "none"))
    timers.remove(found)
    return found


def ready(me):
    """Timers that have finished: taken off the list and returned, so each is noticed once."""
    now_ = _now()
    done = [t for t in me.get("timers", []) if datetime.fromisoformat(t["done"]) <= now_]
    me["timers"] = [t for t in me.get("timers", []) if t not in done]
    return done


def first_wake(me):
    """The earliest moment a timer that should wake me goes off, or None."""
    times = [datetime.fromisoformat(t["done"]) for t in me.get("timers", []) if t.get("wake")]
    return min(times) if times else None


def describe_timers(me, offset_hours):
    out = []
    for t in me.get("timers", []):
        left = datetime.fromisoformat(t["done"]) - _now()
        at = (datetime.fromisoformat(t["done"]) + timedelta(hours=offset_hours)).strftime("%a %H:%M")
        mins = max(0, int(left.total_seconds() // 60))
        span = f"{mins // 60} h {mins % 60} min" if mins >= 60 else f"{mins} min"
        out.append(f"- [{t['id']}] {t['what']}: ready at {at} ({span} from now)" + (f"; then: {t['then']}" if t["then"] else "")
                   + (" (it will wake me)" if t.get("wake") else ""))
    return out


# ---- habits --------------------------------------------------------------------------------------------
def set_habit(me, args):
    name = str(args.get("name") or args.get("habit") or "").strip()[:60]
    if not name:
        raise ValueError('a habit needs a name: set_habit {"name": "morning rounds", "when": "wake", "steps": [...]}')
    habits = me.setdefault("habits", [])
    old = next((h for h in habits if h["name"].lower() == name.lower()), None)
    if args.get("off") in (True, "true", "yes") or str(args.get("steps", "")).lower() in ("none", "off"):
        if not old:
            raise ValueError(f"I have no habit called '{name}'")
        habits.remove(old)
        return None
    when = str(args.get("when", "wake")).lower()
    when = "bed" if when in ("bed", "bedtime", "sleep", "night", "evening") else "wake"
    steps = args.get("steps")
    if not isinstance(steps, list) or not steps:
        raise ValueError('a habit is a list of steps, e.g. "steps": [{"action": "interact", "args": {"specimen": "fern", '
                         '"action": "water"}, "if": "water < 40"}, {"action": "look", "args": {"around": true}}]')
    clean = []
    for s in steps[:MAX_STEPS]:
        if not isinstance(s, dict) or s.get("action") not in HABIT_ACTIONS:
            raise ValueError(f"a habit step can be one of: {', '.join(sorted(HABIT_ACTIONS))} (each with its usual args)")
        step = {"action": s["action"], "args": s.get("args") if isinstance(s.get("args"), dict) else {}}
        if s.get("if"):
            step["if"] = str(s["if"])[:120]
        clean.append(step)
    habit = {"name": name, "when": when, "steps": clean}
    if old:
        habits[habits.index(old)] = habit
    else:
        if len(habits) >= MAX_HABITS:
            raise ValueError(f"I already have {MAX_HABITS} habits; I can let one go first")
        habits.append(habit)
    return habit


def describe_habits(me):
    return [f"- {h['name']} ({'when I wake' if h['when'] == 'wake' else 'at bedtime'}): "
            + "; ".join(s["action"] + (f" {s['args']}" if s["args"] else "") + (f" if {s['if']}" if s.get("if") else "")
                        for s in h["steps"]) for h in me.get("habits", [])]
