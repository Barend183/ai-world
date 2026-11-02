"""Weather and daylight in the AI's world.

It is the real weather of a real place (Open-Meteo: free, no key), hour by hour, so things in the
garden get rained on, baked and chilled for real. When the weather service can't be reached, an
average-climate stand-in is used instead. Indoor rooms are milder and always dry.
"""
import hashlib
import json
import math
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

from .world import load, save

NAMES = ("env_temp", "env_rain", "env_humidity", "env_wind", "env_daylight", "env_hour", "env_month", "age_days")
# Cape Town's averages per month: (mean temperature C, rain mm in the month, rainy days)
CLIMATE = {1: (21, 15, 3), 2: (21.5, 17, 3), 3: (20, 20, 4), 4: (17.5, 41, 7), 5: (15.5, 69, 10), 6: (13.5, 93, 11),
           7: (13, 82, 11), 8: (13.5, 77, 11), 9: (14.5, 40, 8), 10: (16.5, 30, 6), 11: (18.5, 14, 4), 12: (20, 17, 3)}


def _chance(*parts):
    """A repeatable 'random' number in [0, 1) for the same inputs."""
    return int(hashlib.sha1("|".join(map(str, parts)).encode()).hexdigest()[:8], 16) / 0x100000000


class Weather:
    def __init__(self, config):
        self.lat, self.lon = config.get("coords", [-33.93, 18.42])
        self.place = config.get("weather_place", "Cape Town")
        self.offset = config.get("utc_offset_hours", 2)
        self.hours = load("weather.json", {}).get("hours", {})   # "YYYY-MM-DDTHH" (UTC) -> [temp, rain, humidity, wind]

    def refresh(self, past_days=7):
        q = urllib.parse.urlencode({
            "latitude": self.lat, "longitude": self.lon, "timezone": "UTC", "forecast_days": 16,
            "past_days": min(92, max(1, int(past_days))),
            "hourly": "temperature_2m,precipitation,relative_humidity_2m,wind_speed_10m",
        })
        try:
            with urllib.request.urlopen(f"https://api.open-meteo.com/v1/forecast?{q}", timeout=20) as r:
                h = json.loads(r.read())["hourly"]
        except Exception as e:
            print("weather service unavailable, using average climate:", e)
            return False
        for i, t in enumerate(h["time"]):
            row = [h["temperature_2m"][i], h["precipitation"][i], h["relative_humidity_2m"][i], h["wind_speed_10m"][i]]
            if None not in row:
                self.hours[t[:13]] = row
        cutoff = (datetime.now(timezone.utc) - timedelta(days=100)).strftime("%Y-%m-%dT%H")
        self.hours = {k: v for k, v in self.hours.items() if k >= cutoff}
        return True

    def _climate(self, local):
        mean, mm, wet_days = CLIMATE[local.month]
        temp = mean + 5 * math.sin(2 * math.pi * (local.hour - 9) / 24)
        wet = _chance("wet", local.date()) < wet_days / 30
        rain = round(mm / wet_days / 8, 2) if wet and 2 <= local.hour < 10 else 0.0
        return temp, rain, 85 if wet else 65, 15

    def at(self, t, outdoors=True):
        local = t + timedelta(hours=self.offset)
        real = self.hours.get(t.strftime("%Y-%m-%dT%H"))
        temp, rain, humidity, wind = real if real else self._climate(local)
        day = local.timetuple().tm_yday
        length = 12.15 + 2.25 * math.cos(2 * math.pi * (day - 355) / 365)   # longest around 21 December
        sunrise = 12.95 - length / 2
        daylight = 1 if sunrise <= local.hour + 0.5 < sunrise + length else 0
        if not outdoors:   # indoors: milder, dry and still
            temp, rain, humidity, wind = 21 + (temp - 21) * 0.3, 0.0, 50 + (humidity - 50) * 0.4, 0
        return {"env_temp": round(temp, 1), "env_rain": round(rain, 2), "env_humidity": round(humidity),
                "env_wind": round(wind), "env_daylight": daylight, "env_hour": local.hour, "env_month": local.month}

    def describe(self, t=None):
        t = t or datetime.now(timezone.utc)
        o, i = self.at(t, True), self.at(t, False)
        sky = "raining" if o["env_rain"] > 0 else ("daytime" if o["env_daylight"] else "night")
        return (f"Outside (real weather in {self.place}): {o['env_temp']} C, {sky}, rain {o['env_rain']} mm/h, "
                f"humidity {o['env_humidity']}%, wind {o['env_wind']} km/h. Indoors: {i['env_temp']} C, dry.")

    def save(self):
        now = datetime.now(timezone.utc)
        save("weather.json", {"hours": self.hours})   # the hourly record, for the simulation
        # what the web page shows, kept small: the weather for the next three days by hour
        ahead = {(now + timedelta(hours=h)).strftime("%Y-%m-%dT%H"): self.at(now + timedelta(hours=h), True) for h in range(-1, 72)}
        save("weather_now.json", {"place": self.place, "offset": self.offset, "updated": now.isoformat(timespec="seconds"), "hours": ahead})


def _feel(temp):
    for limit, word in ((0, "freezing"), (7, "cold"), (13, "chilly"), (18, "cool"), (24, "mild"), (29, "warm"), (34, "hot")):
        if temp < limit:
            return word
    return "scorching"


def sensations(weather, t=None):
    """What the air feels and smells like outside and in, from the real weather: a world-given sense
    of touch and smell, so it has real causes instead of being imagined."""
    t = t or datetime.now(timezone.utc)
    o, i = weather.at(t, True), weather.at(t, False)
    dry_before = all(weather.at(t - timedelta(hours=h), True)["env_rain"] == 0 for h in range(2, 72, 3))
    humid = o["env_humidity"]
    wind = o["env_wind"]
    touch = [f"the air feels {_feel(o['env_temp'])} ({o['env_temp']} C)"]
    touch.append("damp and heavy" if humid >= 85 else "dry" if humid <= 35 else "neither damp nor dry")
    touch.append("perfectly still" if wind < 3 else "a light breeze" if wind < 15 else "a steady wind tugging at things" if wind < 30 else "strong gusts that push you around")
    if o["env_rain"] > 0:
        touch.append("raindrops on your skin" + (", heavy and cold" if o["env_rain"] > 2 else ", soft and light"))
    smell = []
    if o["env_rain"] > 0 and dry_before:
        smell.append("rain on dry ground, sharp and earthy")
    elif o["env_rain"] > 0:
        smell.append("wet leaves and soaked soil")
    elif humid >= 85:
        smell.append("damp earth and moss")
    elif humid <= 35:
        smell.append("dust and sun-warmed stone" if o["env_daylight"] else "dry, thin night air")
    if not o["env_daylight"]:
        smell.append("cool night air")
    elif o["env_temp"] >= 26:
        smell.append("warm plants")
    if wind >= 25:
        smell.append("something the wind carries from far away")
    sounds = []
    if o["env_rain"] > 2:
        sounds.append("heavy rain drumming on the roof and windows")
    elif o["env_rain"] > 0:
        sounds.append("rain pattering softly on the window and leaves")
    if wind >= 30:
        sounds.append("the wind howling around the corners")
    elif wind >= 15:
        sounds.append("leaves rustling in the wind")
    hour = o["env_hour"]
    if o["env_daylight"] and o["env_rain"] == 0 and 5 <= hour <= 9 and o["env_temp"] > 2:
        sounds.append("birds singing in the early light")
    elif o["env_daylight"] and o["env_rain"] == 0 and wind < 15:
        sounds.append("the odd bird and distant everyday sounds")
    if not o["env_daylight"] and o["env_rain"] == 0 and wind < 15:
        sounds.append("the deep quiet of the night" + (", a cricket somewhere" if o["env_temp"] > 15 else ""))
    indoor = f"Indoors the air is {_feel(i['env_temp'])} ({i['env_temp']} C) and still, and smells of books and wood."
    return (f"Outside, {', '.join(touch)}; it smells of {' and '.join(smell) or 'nothing in particular'}; "
            f"you hear {' and '.join(sounds) or 'very little'}. {indoor}")
