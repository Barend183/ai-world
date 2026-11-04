"""My programs at work while I sleep: tools I made in my workshop, set to run by themselves every few hours.

They run in the workshop's locked-down corner, exactly like when I use a tool myself, but without me: no
thought, no brain, nothing but my own code. What they print waits for me in the morning, and if a program
prints the words I told it to watch for, it wakes me (a frost warning, a rare bird on a webcam, a finished
calculation...)."""
from datetime import datetime, timedelta, timezone

from . import workshop
from .world import now

MAX = 5


def set_schedule(me, args):
    tool = str(args.get("tool") or args.get("name") or "").strip().lower()
    schedules = me.setdefault("schedules", [])
    old = next((s for s in schedules if s["tool"] == tool), None)
    if args.get("off") in (True, "true", "yes"):
        if not old:
            raise ValueError(f"'{tool}' isn't running on its own")
        schedules.remove(old)
        return None
    if tool not in workshop.tools():
        raise ValueError(f"I have no tool called '{tool}' (I make one with save_tool first). "
                         f"My tools: {', '.join(workshop.tools()) or 'none yet'}")
    try:
        every = max(1.0, min(24 * 7.0, float(args.get("every_hours", 3))))
    except (TypeError, ValueError):
        raise ValueError("every_hours is how often it runs, from 1 to 168")
    sched = {"tool": tool, "every_hours": every, "input": args.get("input"),
             "wake_if": str(args.get("wake_if") or "").strip()[:60], "last": None}
    if old:
        schedules[schedules.index(old)] = sched
    elif len(schedules) >= MAX:
        raise ValueError(f"{MAX} of my programs already run on their own; I can stop one first")
    else:
        schedules.append(sched)
    return sched


def due(me, when=None):
    when = when or datetime.now(timezone.utc)
    return [s for s in me.get("schedules", [])
            if not s.get("last") or datetime.fromisoformat(s["last"]) + timedelta(hours=s["every_hours"]) <= when]


def run_due(world, config):
    """Run the programs whose time has come. Returns a reason to wake me, or None."""
    me = world.home
    if not workshop.enabled(config):
        return None
    reason = None
    for s in due(me):
        s["last"] = now()
        try:
            out = workshop.use_tool(s["tool"], s.get("input"))
        except Exception as e:
            out = f"(it couldn't run: {e})"
        log = me.setdefault("program_log", [])
        log.append({"at": now(), "tool": s["tool"], "out": out[:800]})
        del log[:-20]
        if s.get("wake_if") and s["wake_if"].lower() in out.lower() and not reason:
            reason = f"my program '{s['tool']}' noticed something ({s['wake_if']})"
    return reason


def since(me, last_awake):
    """What my programs found since I was last up."""
    return [x for x in me.get("program_log", []) if not last_awake or x["at"] > last_awake]


def describe(me):
    return [f"- {s['tool']}: every {s['every_hours']:g} h" + (f", wakes me if it says “{s['wake_if']}”" if s.get("wake_if") else "")
            + (f" (last ran {s['last'][:16].replace('T', ' ')} UTC)" if s.get("last") else " (hasn't run yet)")
            for s in me.get("schedules", [])]
