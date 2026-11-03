"""Things that happen to his world: storms, heat waves and cold snaps (read from the real weather where
he lives) and now and then a power cut, more likely in a storm.

They're real for him: a power cut switches off his computer and electric lights until it's back, and
his creations can react to them (env_storm, env_power). The state lives in his self.json under
"world_events", so the page can show it too.
"""
from datetime import datetime, timedelta, timezone

from .env import _chance

STORM_WIND, STORM_RAIN = 45, 6   # km/h, mm/h: a storm by either
HEAT, COLD = 32, 2               # C: three hot days running is a heat wave; a frosty night a cold snap
CUT_PER_HOUR, CUT_IN_STORM = 0.004, 0.06   # chance of the power going out in any hour (about once in ten days)

# What needs electricity: everything done at the computer.
COMPUTER = {"search", "read", "test", "run_code", "save_tool", "use_tool", "publish", "unpublish", "design_public_page",
            "view_public_page", "build_site", "write_site_page", "remove_site_page", "view_site"}


def _hour(t):
    return t.replace(minute=0, second=0, microsecond=0)


def stormy(weather, t):
    o = weather.at(t, True)
    return o["env_wind"] >= STORM_WIND or o["env_rain"] >= STORM_RAIN


def _days(weather, t, n, pick):
    """The daily highest (or lowest) temperature for the n days up to t."""
    return [pick(weather.at(t - timedelta(hours=24 * d + h), True)["env_temp"] for h in range(24)) for d in range(n)]


def state(world):
    return world.home.setdefault("world_events", {"cuts": [], "now": [], "checked": None})


def power_on(world, t):
    for c in state(world)["cuts"] if world else []:
        if c["since"] <= t.isoformat() < c["until"]:
            return False
    return True


def cut_now(world, t=None):
    t = t or datetime.now(timezone.utc)
    return next((c for c in state(world)["cuts"] if c["since"] <= t.isoformat() < c["until"]), None)


def update(world, weather, until=None):
    """Bring his world's happenings up to date, hour by hour since the last look, and note what changed."""
    s = state(world)
    until = _hour(until or datetime.now(timezone.utc))
    last = datetime.fromisoformat(s["checked"]) if s.get("checked") else until - timedelta(hours=1)
    t = max(_hour(last), until - timedelta(hours=72))
    local = lambda x: (x + timedelta(hours=weather.offset)).strftime("%H:%M")
    if world.config.get("power_cuts", True):
        while t < until:
            t += timedelta(hours=1)
            if power_on(world, t):
                p = CUT_PER_HOUR + (CUT_IN_STORM if stormy(weather, t) else 0)
                if _chance("power", t.isoformat()) < p:
                    end = t + timedelta(hours=2 + int(_chance("power-len", t.isoformat()) * 7))
                    s["cuts"].append({"since": t.isoformat(), "until": end.isoformat()})
                    if end <= until:
                        world.log("event", f"While I slept, the power went out from {local(t)} to {local(end)}", room="study")
    s["cuts"] = s["cuts"][-20:]

    now = until
    happening = []
    if stormy(weather, now):
        happening.append("storm")
    if all(x >= HEAT for x in _days(weather, now, 3, max)):
        happening.append("heat wave")
    if min(_days(weather, now, 1, min)) <= COLD:
        happening.append("cold snap")
    if cut_now(world, now):
        happening.append("power cut")
    words = {"storm": ("A storm rolled in", "The storm passed"), "heat wave": ("A heat wave set in", "The heat wave broke"),
             "cold snap": ("A cold snap arrived", "The cold snap eased"), "power cut": ("The power went out", "The power came back")}
    for kind in happening:
        if kind not in s["now"]:
            world.log("event", words[kind][0], describe(world, weather, [kind]), room="study")
    for kind in s["now"]:
        if kind not in happening:
            world.log("event", words[kind][1], room="study")
    s["now"], s["checked"] = happening, until.isoformat()
    return happening


def describe(world, weather, kinds=None):
    """What's happening, as he experiences it."""
    t = datetime.now(timezone.utc)
    o = weather.at(t, True)
    local = lambda iso: (datetime.fromisoformat(iso) + timedelta(hours=weather.offset)).strftime("%H:%M")
    out = []
    for kind in kinds if kinds is not None else state(world)["now"]:
        if kind == "storm":
            out.append(f"A storm is blowing: wind {o['env_wind']} km/h, rain {o['env_rain']} mm/h. Outdoors everything takes the "
                       "full force of it; indoors you hear it rattling the windows.")
        elif kind == "heat wave":
            out.append(f"A heat wave: over {HEAT} C three days running. Outdoors it's baking; things dry out fast.")
        elif kind == "cold snap":
            out.append(f"A cold snap: it drops to {COLD} C or below. Frost outdoors; tender things suffer.")
        elif kind == "power cut":
            c = cut_now(world, t)
            back = f", back around {local(c['until'])}" if c else ""
            out.append(f"The power is out (since {local(c['since']) if c else 'a while ago'}{back}). Your computer, screens and "
                       "electric lights don't work until it's back; daylight, candles and fires still do.")
    return " ".join(out)
