"""My alarm clock: it stands beside my bed. I can set it to ring at a time of day, every day or just once, or
leave it off. When it's on, it wakes me at that time (unless I chose to sleep less than that)."""
import re
from datetime import datetime, timedelta, timezone


def parse_time(value):
    """'06:30', '6.30', '6:30 pm', '7am', '18h05', 7 -> (hour, minute), or None. Forgiving about how I write it."""
    if isinstance(value, (int, float)) and 0 <= value < 24:
        return int(value), int(round((value % 1) * 60)) % 60
    m = re.fullmatch(r"\s*(\d{1,2})(?:\s*[:.h]\s*(\d{2}))?\s*(am|pm|a\.m\.|p\.m\.)?\s*", str(value or "").lower())
    if not m:
        return None
    hour, minute, half = int(m.group(1)), int(m.group(2) or 0), (m.group(3) or "")[:1]
    if half == "p" and hour < 12:
        hour += 12
    if half == "a" and hour == 12:
        hour = 0
    return (hour, minute) if hour < 24 and minute < 60 else None


def describe(me):
    a = me.get("alarm") or {}
    if not a.get("on"):
        return "off"
    return f"set for {a['time']}" + (" every day" if a.get("repeat") == "daily" else " (just once)")


def set_(me, args):
    """Set or switch off my alarm clock; returns what it says now."""
    raw = next((args[k] for k in ("time", "at", "hour", "when") if args.get(k) not in (None, "")), None)
    if (args.get("off") in (True, "true", "yes") or str(args.get("on", "")).lower() in ("false", "no", "0", "off")
            or str(raw).lower() in ("off", "none")):
        if (me.get("alarm") or {}).get("on"):
            me["alarm"]["on"] = False
        return "My alarm clock is off; I'll wake when I've slept as long as I chose."
    hm = parse_time(raw)
    if not hm:
        raise ValueError('my alarm clock needs a time of day, like set_alarm {"time": "06:30"} (or {"off": true})')
    repeat = str(args.get("repeat", "daily")).lower()
    repeat = "once" if repeat in ("once", "one", "tomorrow", "no", "false", "single") else "daily"
    me["alarm"] = {"time": f"{hm[0]:02d}:{hm[1]:02d}", "repeat": repeat, "on": True}
    return f"My alarm clock is {describe(me)}."


def next_ring(me, offset_hours, after=None):
    """When my alarm clock next rings (UTC), or None when it's off."""
    a = me.get("alarm") or {}
    if not a.get("on"):
        return None
    hm = parse_time(a.get("time"))
    if not hm:
        return None
    after = after or datetime.now(timezone.utc)
    local = after + timedelta(hours=offset_hours)
    ring = local.replace(hour=hm[0], minute=hm[1], second=0, microsecond=0)
    if ring <= local:
        ring += timedelta(days=1)
    return ring - timedelta(hours=offset_hours)


def bedtime(me, hours, chose_hours, offset_hours):
    """When I wake: after the hours I chose (or my usual sleep), or when my alarm clock rings, whichever comes
    first. An alarm only ever wakes me; it never keeps me asleep longer (a day that ended because I ran out of
    energy once slept on for 23 hours, until the next morning's alarm). Returns (wake time UTC, rang)."""
    now_ = datetime.now(timezone.utc)
    natural = now_ + timedelta(hours=hours)
    ring = next_ring(me, offset_hours, now_)
    if ring and ring < natural:
        return ring, True
    return natural, False
