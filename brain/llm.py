"""Swappable brains.

Every brain takes a system prompt and a user prompt and returns one JSON object
as text. The chain tries them in order: Gemini's free tier first, then a small
open model through Ollama when Gemini is out of free requests for the day.
"""
import json
import os
import re
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone


class BrainUnavailable(Exception):
    """This brain can't be used right now (no key, not installed...)."""


class QuotaExhausted(BrainUnavailable):
    """Free requests for the day are used up."""


def _request(url, body=None, headers=None, timeout=300):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json", **(headers or {})})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


class Gemini:
    """Google's free tier. Tries the best Flash model first and moves down the list when one is
    overloaded, hangs or runs out of free requests (each model has its own daily allowance)."""
    kind = "gemini"
    sees = True
    BASE = "https://generativelanguage.googleapis.com/v1beta"
    SKIP = ("image", "tts", "live", "audio", "exp", "thinking", "8b", "preview", "customtools", "omni")

    def __init__(self, cfg, status=None):
        self.key = os.environ.get("GEMINI_API_KEY") or cfg.get("api_key")
        if not self.key:
            raise BrainUnavailable("no GEMINI_API_KEY set")
        self.status = status if status is not None else {}
        wanted = cfg.get("model", "auto")
        self.candidates = self._models() if wanted == "auto" else [wanted]
        self.model = None
        self._next_working()

    def _models(self):
        """Every usable Flash model, best first: newest full models, the rolling alias, then the lite ones."""
        try:
            data = _request(f"{self.BASE}/models?pageSize=200", headers={"x-goog-api-key": self.key}, timeout=30)
        except urllib.error.HTTPError as e:
            raise BrainUnavailable(f"Gemini key rejected ({e.code})") from e
        except Exception as e:
            raise BrainUnavailable(f"couldn't reach Gemini ({e})") from e
        names = [m["name"].split("/")[-1] for m in data.get("models", [])
                 if "generateContent" in m.get("supportedGenerationMethods", [])]
        flash = [n for n in names if "flash" in n and not any(s in n for s in self.SKIP)]

        def rank(n):
            m = re.search(r"gemini-(\d+(?:\.\d+)?)", n)
            return ("lite" in n, "latest" in n, -(float(m.group(1)) if m else 0.0))
        return sorted(flash, key=rank)

    def _usable(self, model, kinds=("gemini_models_out", "gemini_models_busy")):
        now_ = datetime.now(timezone.utc)
        return all(datetime.fromisoformat(self.status.get(k, {}).get(model, now_.isoformat())) <= now_ for k in kinds)

    def _call(self, model, body, timeout):
        # The free tier allows only a few requests a minute, so thoughts are paced a few seconds apart.
        wait = getattr(self, "_last_call", 0) + 6.5 - time.time()
        if wait > 0:
            time.sleep(wait)
        self._last_call = time.time()
        data = _request(f"{self.BASE}/models/{model}:generateContent", body, headers={"x-goog-api-key": self.key}, timeout=timeout)
        day = (next_reset() - timedelta(days=1)).date().isoformat()   # the free allowance runs from reset to reset
        used = self.status.setdefault("gemini_used", {})
        if used.get("day") != day:
            used.clear()
            used["day"] = day
        used[model] = used.get(model, 0) + 1
        parts = data["candidates"][0]["content"].get("parts", [])
        return "".join(p.get("text", "") for p in parts if not p.get("thought"))

    def _next_working(self, waited=False):
        """Pick the first model on the list that answers a tiny question quickly.
        The model that worked last time is trusted without a test, since every request counts
        against the free daily allowance (20 per model)."""
        last = self.status.get("gemini_last_good")
        if self.model is None and last in self.candidates and self._usable(last):
            self.model, self.label = last, f"Gemini ({last})"
            return
        probe = {"contents": [{"role": "user", "parts": [{"text": 'Reply {"ok": true}'}]}],
                 "generationConfig": {"responseMimeType": "application/json"}}
        tried = []
        order = ([last] if last in self.candidates else []) + self.candidates
        for model in order:
            if model in tried or not self._usable(model) or model in getattr(self, "_failed", set()):
                continue
            tried.append(model)
            try:
                self._call(model, probe, 25)
                self.model, self.label = model, f"Gemini ({model})"
                self.status["gemini_last_good"] = model
                return
            except urllib.error.HTTPError as e:
                if e.code == 429:
                    if self._mark_out(model, e.read().decode(errors="replace")):
                        self._failed = getattr(self, "_failed", set()) | {model}
                    continue
                self._rest(model)
            except Exception:
                self._rest(model)
            self._failed = getattr(self, "_failed", set()) | {model}
        if not waited:   # if a model is only paused by the per-minute limit, wait for it
            now_ = datetime.now(timezone.utc)
            soon = [datetime.fromisoformat(u) for m, u in self.status.get("gemini_models_out", {}).items()
                    if m in self.candidates and m not in getattr(self, "_failed", set())
                    and now_ < datetime.fromisoformat(u) < now_ + timedelta(minutes=3)]
            if soon:
                time.sleep((min(soon) - now_).total_seconds() + 1)
                return self._next_working(waited=True)
        if all(not self._usable(m, ("gemini_models_out",)) for m in self.candidates):
            raise QuotaExhausted("every Gemini model is out of free requests for today")
        raise BrainUnavailable("no Gemini model is answering right now")

    def _mark_out(self, model, detail):
        # A per-day limit lasts until the daily reset; a per-minute one only briefly.
        daily = "PerDay" in detail or "per day" in detail.lower()
        until = next_reset() if daily else datetime.now(timezone.utc) + timedelta(minutes=1)
        self.status.setdefault("gemini_models_out", {})[model] = until.isoformat()
        return daily

    DAILY = 20   # free requests per model per day

    def budget(self):
        """Roughly how many thoughts are left today across the models that still work."""
        used = self.status.get("gemini_used", {})
        fresh = used.get("day") == (next_reset() - timedelta(days=1)).date().isoformat()
        return sum(max(0, self.DAILY - (used.get(m, 0) if fresh else 0)) for m in self.candidates
                   if self._usable(m, ("gemini_models_out",)) and m not in getattr(self, "_failed", set()))

    def _rest(self, model):
        """A busy or hanging model is skipped for half an hour."""
        self.status.setdefault("gemini_models_busy", {})[model] = (datetime.now(timezone.utc) + timedelta(minutes=30)).isoformat()
        if self.status.get("gemini_last_good") == model:
            del self.status["gemini_last_good"]

    def think(self, system, prompt, images=(), best=False):
        import base64
        if best:   # important thinking: the strongest full model that's available right now
            strongest = next((m for m in self.candidates if "lite" not in m and self._usable(m)
                              and m not in getattr(self, "_failed", set())), None)
            if strongest and strongest != self.model:
                everyday, self.model = self.model, strongest
                try:
                    return self.think(system, prompt, images)
                except Exception:
                    self.model = everyday   # fall back to the everyday model
        pictures = [{"inline_data": {"mime_type": mime, "data": base64.b64encode(data).decode()}} for mime, data in images]
        body = {
            "systemInstruction": {"parts": [{"text": system}]},
            "contents": [{"role": "user", "parts": [{"text": prompt}, *pictures]}],
            "generationConfig": {"responseMimeType": "application/json", "temperature": 0.9},
        }
        for attempt in range(6):
            try:
                return self._call(self.model, body, 150)
            except urllib.error.HTTPError as e:
                detail = e.read().decode(errors="replace")
                if e.code == 429:
                    if not self._mark_out(self.model, detail):
                        self._next_working()   # just the per-minute limit: same or another model shortly
                        continue
                elif e.code < 500:
                    raise BrainUnavailable(f"Gemini error {e.code}: {detail[:200]}") from e
            except (KeyError, IndexError):
                if attempt < 2:   # an empty answer now and then is normal; ask again
                    time.sleep(3)
                    continue
            except Exception:
                self._rest(self.model)   # timed out or the connection dropped
            self._failed = getattr(self, "_failed", set()) | {self.model}
            self._next_working()   # move down the list (raises when nothing is left)
        raise BrainUnavailable("Gemini kept failing")


class Ollama:
    kind = "ollama"

    def __init__(self, cfg, status=None):
        self.host = os.environ.get("OLLAMA_HOST_URL") or cfg.get("host", "http://127.0.0.1:11434")
        self.model = cfg.get("model", "qwen3:4b")
        try:
            tags = _request(f"{self.host}/api/tags", timeout=5)
        except Exception as e:
            raise BrainUnavailable("Ollama is not running") from e
        have = {m["name"] for m in tags.get("models", [])}
        if self.model not in have and f"{self.model}:latest" not in have:
            raise BrainUnavailable(f"Ollama doesn't have {self.model} downloaded")
        self.label = f"{self.model} (open model)"
        self.sees = bool(cfg.get("vision"))   # gemma3 can look at pictures; qwen3 can't

    def think(self, system, prompt, images=()):
        import base64
        user = {"role": "user", "content": prompt}
        if images and self.sees:
            user["images"] = [base64.b64encode(data).decode() for _, data in images]
        body = {
            "model": self.model,
            "messages": [{"role": "system", "content": system}, user],
            "format": "json",
            "stream": False,
            "options": {"num_ctx": 8192, "temperature": 0.8},
        }
        try:
            return _request(f"{self.host}/api/chat", body, timeout=900)["message"]["content"]
        except Exception as e:
            raise BrainUnavailable(f"Ollama failed: {e}") from e


def next_utc_midnight():
    now = datetime.now(timezone.utc)
    return (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)


class OpenAICompat:
    """A free OpenAI-style service such as Groq or OpenRouter. It rotates across the service's models,
    since each model has its own free limits, and switches to one that can see when there's a picture."""

    def __init__(self, cfg, status=None, kind="openai"):
        self.kind, self.cfg = kind, cfg
        self.key = os.environ.get(cfg.get("key_env", "")) or cfg.get("api_key")
        if not self.key:
            raise BrainUnavailable(f"no {cfg.get('key_env')} set")
        self.base = cfg["base"].rstrip("/")
        self.status = status if status is not None else {}
        self.vision = set(cfg.get("vision", []))
        self.models = self._models()
        self.sees = bool(self.vision & set(self.models))
        self.no_json = set()
        usable = [m for m in self.models if self._usable(m)]
        if not usable:
            if any(self._usable(m, ("out",)) for m in self.models):
                raise BrainUnavailable(f"every {kind} model is busy right now")
            raise QuotaExhausted(f"{kind} is out of free requests for today")
        self.model = usable[0]
        self.name = cfg.get("label", kind.title())
        self.label = f"{self.name} ({self.model})"

    def _headers(self):
        return {"Authorization": f"Bearer {self.key}", "HTTP-Referer": "https://github.com", "X-Title": "AI World"}

    def _models(self):
        if self.cfg.get("models") != "free":
            return list(self.cfg.get("models", []))
        # OpenRouter: every model that's free to use, the ones with the most room to think first
        try:
            data = _request(f"{self.base}/models", headers=self._headers(), timeout=30)["data"]
        except Exception as e:
            raise BrainUnavailable(f"couldn't reach {self.kind} ({e})") from e
        free = [m for m in data if m["id"].endswith(":free")]
        free.sort(key=lambda m: -(m.get("context_length") or 0))
        self.vision |= {m["id"] for m in free if "image" in ((m.get("architecture") or {}).get("input_modalities") or [])}
        return [m["id"] for m in free][:10]

    def _key(self, which):
        return f"{self.kind}_{which}"

    def _usable(self, model, kinds=("out", "busy")):
        now_ = datetime.now(timezone.utc)
        return all(datetime.fromisoformat(self.status.get(self._key(k), {}).get(model, now_.isoformat())) <= now_ for k in kinds)

    def _mark(self, model, which, until):
        self.status.setdefault(self._key(which), {})[model] = until.isoformat()

    def _used(self):
        used = self.status.setdefault(self._key("used"), {})
        day = (next_utc_midnight() - timedelta(days=1)).date().isoformat()
        if used.get("day") != day:
            used.clear()
            used["day"] = day
        return used

    def budget(self):
        used = self._used()
        if self.cfg.get("daily_tokens"):
            per = self.cfg.get("tokens_per_thought", 7000)
            return sum(max(0, self.cfg["daily_tokens"] - used.get(m, 0)) // per for m in self.models if self._usable(m, ("out",)))
        if self.cfg.get("daily_requests"):
            return max(0, self.cfg["daily_requests"] - used.get("requests", 0))
        return None

    def _pick(self, images):
        order = sorted(self.models, key=lambda m: (bool(images) and m not in self.vision, m != self.model))
        for m in order:
            if self._usable(m):
                return m
        return None

    def think(self, system, prompt, images=()):
        import base64
        for attempt in range(12):
            model = self._pick(images)
            if model is None:
                soon = [datetime.fromisoformat(u) for m, u in self.status.get(self._key("busy"), {}).items()
                        if m in self.models and self._usable(m, ("out",))]
                if not soon:
                    raise QuotaExhausted(f"{self.kind} is out of free requests for today")
                time.sleep(min(90, max(1, (min(soon) - datetime.now(timezone.utc)).total_seconds() + 1)))
                continue
            self.model, self.label = model, f"{self.name} ({model})"
            content = prompt
            if images and model in self.vision:
                content = [{"type": "text", "text": prompt}] + [
                    {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{base64.b64encode(data).decode()}"}}
                    for mime, data in images]
            elif images:
                content = prompt + "\n\n(The pictures didn't come through: the brain you're using right now can't see.)"
            body = {"model": model, "temperature": 0.9,
                    "messages": [{"role": "system", "content": system}, {"role": "user", "content": content}]}
            if model not in self.no_json:
                body["response_format"] = {"type": "json_object"}
            wait = getattr(self, "_last_call", 0) + self.cfg.get("min_interval", 2) - time.time()
            if wait > 0:
                time.sleep(wait)
            self._last_call = time.time()
            try:
                data = _request(f"{self.base}/chat/completions", body, headers=self._headers(), timeout=180)
                used = self._used()
                used[model] = used.get(model, 0) + (data.get("usage") or {}).get("total_tokens", 0)
                used["requests"] = used.get("requests", 0) + 1
                text = (data["choices"][0]["message"].get("content") or "").strip()
                if text:
                    return text
                self._mark(model, "busy", datetime.now(timezone.utc) + timedelta(minutes=5))
            except urllib.error.HTTPError as e:
                detail = e.read().decode(errors="replace")
                low = detail.lower()
                if e.code == 429:
                    daily = any(w in low for w in ("per day", "tokens per day", "requests per day", "(tpd)", "(rpd)", "daily"))
                    if self.cfg.get("daily_requests") and "free-models-per-day" in low:
                        daily = True
                    if daily:
                        self._mark(model, "out", next_utc_midnight())
                    else:
                        self._mark(model, "busy", datetime.now(timezone.utc) + timedelta(seconds=65))
                elif e.code == 400 and "response_format" in low and model not in self.no_json:
                    self.no_json.add(model)
                elif e.code in (401, 403):
                    raise BrainUnavailable(f"{self.kind} refused the key ({e.code})") from e
                else:
                    self._mark(model, "busy", datetime.now(timezone.utc) + timedelta(minutes=30))
            except (KeyError, IndexError):
                self._mark(model, "busy", datetime.now(timezone.utc) + timedelta(minutes=5))
            except Exception:
                self._mark(model, "busy", datetime.now(timezone.utc) + timedelta(minutes=30))
        raise BrainUnavailable(f"{self.kind} kept failing")


class Scripted:
    """A fake brain for testing the world without any AI: replays a list of actions."""
    kind = "scripted"
    sees = True

    def __init__(self, actions):
        self.actions = list(actions)
        self.label = "scripted test brain"

    def think(self, system, prompt, images=(), best=False):
        return json.dumps(self.actions.pop(0) if self.actions else {"thought": "Nothing left to do.", "action": "sleep", "args": {}})


BRAINS = {
    "gemini": Gemini,
    "groq": lambda cfg, status: OpenAICompat(cfg, status, "groq"),
    "openrouter": lambda cfg, status: OpenAICompat(cfg, status, "openrouter"),
    "ollama": Ollama,
}


def next_reset():
    """Gemini's free quota resets at midnight Pacific time (~08:00 UTC)."""
    now = datetime.now(timezone.utc)
    reset = now.replace(hour=8, minute=0, second=0, microsecond=0)
    return reset if reset > now else reset + timedelta(days=1)


class Chain:
    """Uses the first brain that works and falls back when one runs out."""

    def __init__(self, config, status):
        self.config = config
        self.status = status  # persisted dict: {"exhausted": {kind: iso_time}}
        self.order = list(config.get("brains", ["gemini", "ollama"]))
        self.current = None
        self.problems = []

    def _usable(self, kind):
        until = self.status.get("exhausted", {}).get(kind)
        return not until or datetime.fromisoformat(until) <= datetime.now(timezone.utc)

    def pick(self):
        self.problems = []
        for kind in self.order:
            if not self._usable(kind):
                self.problems.append(f"{kind}: out of free requests until {self.status['exhausted'][kind]}")
                continue
            try:
                self.current = BRAINS[kind](self.config.get(kind, {}), self.status)
                return self.current
            except BrainUnavailable as e:
                self.problems.append(f"{kind}: {e}")
        self.current = None
        return None

    def budget(self):
        """Roughly how many fast thoughts are left today across all the free services; None means no limit."""
        if self.current is None:
            self.pick()
        if self.current is None or not hasattr(self.current, "budget"):
            return None
        total = self.current.budget() or 0
        later = self.order[self.order.index(self.current.kind) + 1:] if self.current.kind in self.order else []
        for kind in later:
            cfg = self.config.get(kind, {})
            if not self._usable(kind) or (cfg.get("key_env") and not os.environ.get(cfg["key_env"])):
                continue
            used = self.status.get(f"{kind}_used", {})
            if cfg.get("daily_tokens") and isinstance(cfg.get("models"), list):
                total += sum(max(0, cfg["daily_tokens"] - used.get(m, 0)) for m in cfg["models"]) // cfg.get("tokens_per_thought", 7000)
            elif cfg.get("daily_requests"):
                total += max(0, cfg["daily_requests"] - used.get("requests", 0))
        return total

    def think(self, system, prompt, images=(), best=False):
        while True:
            if self.current is None and self.pick() is None:
                raise BrainUnavailable("; ".join(self.problems))
            try:
                if best and self.current.kind == "gemini":
                    return self.current.think(system, prompt, images, best=True)
                return self.current.think(system, prompt, images)
            except QuotaExhausted:
                until = next_reset() if self.current.kind == "gemini" else next_utc_midnight()
                self.status.setdefault("exhausted", {})[self.current.kind] = until.isoformat()
                self.current = None
