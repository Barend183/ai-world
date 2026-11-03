"""Settings the AI controls about itself, within the protections that keep it and its visitor safe.

They live in its own world (self.json -> "settings") and override the defaults in config.json.
Nothing here can touch the lock, the privacy guards, the sandbox or the keys.
"""
import json
import urllib.parse
import urllib.request

LIMITS = {
    "default_sleep_hours": (0.5, 24),
    "max_thoughts": (5, 30),
    "review_days": (3, 30),
}


def apply(config, settings):
    """The config as the AI has chosen to change it."""
    c = dict(config)
    s = settings or {}
    if "default_sleep_hours" in s:
        c["default_sleep_hours"] = s["default_sleep_hours"]
    if "max_thoughts" in s:
        c["max_steps_per_session"] = {k: min(v, s["max_thoughts"]) for k, v in config.get("max_steps_per_session", {}).items()}
    if "review_days" in s:
        c["review_days"] = s["review_days"]
    if "spark" in s:
        c["spark"] = s["spark"]
    if "dreams" in s:
        c["dreams"] = s["dreams"]
    loc = s.get("location")
    if loc:
        c.update(coords=[loc["lat"], loc["lon"]], weather_place=loc["place"], utc_offset_hours=loc["offset"],
                 location=f"{loc['place']}, {loc.get('country', '')}".strip(", "))
    return c


def _geocode(name):
    q = urllib.parse.urlencode({"name": name, "count": 1, "language": "en", "format": "json"})
    with urllib.request.urlopen(f"https://geocoding-api.open-meteo.com/v1/search?{q}", timeout=20) as r:
        hits = json.loads(r.read()).get("results") or []
    if not hits:
        raise ValueError(f"couldn't find a place called '{name}'")
    h = hits[0]
    offset = 0
    try:
        from datetime import datetime
        from zoneinfo import ZoneInfo
        offset = round(datetime.now(ZoneInfo(h["timezone"])).utcoffset().total_seconds() / 3600, 2)
    except Exception:
        offset = round(h["longitude"] / 15)   # good enough without timezone data
    return {"place": h["name"], "country": h.get("country", ""), "lat": h["latitude"], "lon": h["longitude"], "offset": offset}


def change(me, setting, value):
    s = me.setdefault("settings", {})
    setting = str(setting).strip().lower()
    if setting in LIMITS:
        lo, hi = LIMITS[setting]
        try:
            v = float(value)
        except (TypeError, ValueError):
            raise ValueError(f"{setting} needs a number between {lo} and {hi}")
        s[setting] = min(max(v, lo), hi) if setting == "default_sleep_hours" else int(min(max(v, lo), hi))
        return f"{setting} is now {s[setting]}"
    if setting in ("spark", "dreams"):
        s[setting] = str(value).lower() in ("1", "true", "on", "yes")
        return f"{'the morning spark' if setting == 'spark' else 'dreaming'} is now {'on' if s[setting] else 'off'}"
    if setting == "location":
        loc = _geocode(str(value))
        s["location"] = loc
        return f"your world is now in {loc['place']}, {loc['country']} (its real weather, daylight and seasons from your next wake-up)"
    raise ValueError("settings you can change: default_sleep_hours, max_thoughts, review_days, spark (on/off), dreams (on/off), location (a place name)")


def describe(me, config):
    s = me.get("settings", {})
    loc = s.get("location")
    return (f"sleep {config.get('default_sleep_hours', 3)} h unless you say otherwise; at most "
            f"{max(config.get('max_steps_per_session', {}).values() or [12])} thoughts a session; look back every "
            f"{config.get('review_days', 7)} days; morning spark {'on' if config.get('spark', True) else 'off'}; "
            f"world located in {loc['place'] if loc else config.get('weather_place', 'Cape Town')}")
