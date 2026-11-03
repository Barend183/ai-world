"""Everything the AI owns, stored as plain files under docs/world so the web page can show it.

  self.json      who it is, what it's doing, where it's standing
  shelves.json   catalogue of books;  books/<id>.md holds each book
  wishlist.json  things it wants to learn
  notes.json     notes visitors left and its replies
  specimens.json things it brought to life: plants, animals, machines, food...
  rooms.json     the study it started in, plus rooms and yards it built and decorated
  goals.json     long-term projects it set itself
  requests.json  things it asked its visitor for (an account, a new ability...) and the answers
  companions.json  a companion who came to share the world, with a mind and a self of its own
  recent.json    the last few hundred things it did (the page replays these)
  journal/       every event ever, one file per month
  brain.json     which brains are out of free requests
"""
import json
import os
import re
import tempfile
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORLD = os.path.join(ROOT, "docs", "world")
RECENT_LIMIT = 300

# Where in the room each kind of activity happens (the page walks the AI there).
PLACES = {
    "wake": "bed", "sleep": "bed", "diary": "bed",
    "search": "computer", "read": "computer",
    "write_book": "shelves", "read_book": "shelves",
    "add_wish": "board", "complete_wish": "board", "drop_wish": "board",
    "think": "armchair", "muddled": "armchair",
    "reply_note": "mailbox",
    "spawn": "specimen", "interact": "specimen", "release": "specimen", "move": "specimen",
    "build_room": "room", "decorate": "item", "remove_item": "room",
    "look": "computer", "restyle": "room", "test": "computer",
    "set_goal": "board", "update_goal": "board", "write_letter": "mailbox",
    "make_request": "mailbox", "write_notebook": "armchair", "change_self": "armchair", "pastime": "room", "run_code": "computer", "compose": "armchair", "mirror": "room", "add_life_chapter": "armchair", "change_setting": "armchair", "think_hard": "armchair", "listen": "armchair", "publish": "computer", "unpublish": "computer", "design_public_page": "computer", "view_public_page": "computer",
    "talk": "talk", "invite_companion": "mailbox", "companion": "door", "event": "armchair",
    "build_site": "computer", "write_site_page": "computer", "remove_site_page": "computer", "view_site": "computer",
    "write_private": "armchair",
    "remember": "shelves", "set_rules": "armchair", "set_wake_triggers": "bed", "save_tool": "computer", "use_tool": "computer",
}


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def slug(text):
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return s[:60] or "untitled"


def _path(*parts):
    return os.path.join(WORLD, *parts)


def load(name, default):
    try:
        with open(_path(name), encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def save(name, data):
    path = _path(name)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path), suffix=".tmp")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=1, ensure_ascii=False)
    os.replace(tmp, path)


class World:
    def __init__(self, config):
        self.me = load("self.json", None) or {
            "name": config["name"], "born": now(), "about": config["personality"],
            "mood": "curious", "sessions": 0, "steps": 0,
        }
        self.home = self.me   # whose world it is; `me` is whoever is thinking right now
        self.companions = load("companions.json", [])
        from .settings import apply
        self.config = apply(config, self.me.get("settings"))
        self.shelves = load("shelves.json", [])
        self.wishes = load("wishlist.json", None)
        if self.wishes is None:
            self.wishes = []
            for w in config.get("starting_wishes", []):
                self.add_wish(w["topic"], w["why"])
        self.notes = load("notes.json", [])
        self.goals = load("goals.json", [])
        self.requests = load("requests.json", [])
        self.music = load("music.json", [])
        self.specimens = load("specimens.json", [])
        from .rooms import STUDY
        self.rooms = load("rooms.json", None) or [{**STUDY, "items": []}]
        self.recent = load("recent.json", [])
        self.brain_status = load("brain.json", {})

    # ---- journal -------------------------------------------------------
    def log(self, action, summary, detail=None, **extra):
        event = {"t": now(), "session": self.home["sessions"], "action": action, "room": extra.pop("room", None) or "study",
                 "place": PLACES.get(action, "armchair"), "summary": summary[:300]}
        if detail:
            event["detail"] = detail[:4000]
        event.update({k: v for k, v in extra.items() if v is not None})
        if self.me is not self.home:
            event["who"] = self.me.get("id", "companion")
        self.recent.append(event)
        self.recent = self.recent[-RECENT_LIMIT:]
        self.me.update(activity=summary[:160], place=event["place"], room=event["room"], last_seen=event["t"])
        os.makedirs(_path("journal"), exist_ok=True)
        with open(_path("journal", event["t"][:7] + ".jsonl"), "a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")
        self.save()  # save as we go so the page can watch live
        from . import live
        live.push()   # online: a sealed snapshot for the owner's page, about once a minute
        return event

    @contextmanager
    def being(self, me):
        """Lend the world to whoever is thinking: everything they do is theirs (their notebook, their look, their journal)."""
        was, self.me = self.me, me
        try:
            yield me
        finally:
            self.me = was

    def mark(self, what, days=2):
        """Something that stays on his mind for a while (a loss, a joy, a new arrival)."""
        until = (datetime.now(timezone.utc) + timedelta(days=days)).isoformat(timespec="seconds")
        marks = self.home.setdefault("on_my_mind", [])
        marks.append({"at": now(), "what": what[:200], "until": until})
        del marks[:-12]

    def companion(self):
        return next((c for c in self.companions if c.get("status") == "living"), None)

    # ---- books ---------------------------------------------------------
    def book(self, book_id):
        return next((b for b in self.shelves if b["id"] == book_id), None)

    def find_book(self, title_or_id):
        key = slug(title_or_id)
        return self.book(title_or_id) or self.book(key) or next(
            (b for b in self.shelves if slug(b["title"]) == key), None)

    def read_book_text(self, book_id):
        with open(_path("books", book_id + ".md"), encoding="utf-8") as f:
            return f.read()

    def write_book(self, title, shelf, summary, content, sources, verified):
        existing = self.find_book(title)
        book = existing or {"id": slug(title), "created": now(), "revisions": 0}
        if not existing and self.book(book["id"]):
            book["id"] += "-" + str(len(self.shelves))
        book.update(title=title.strip(), shelf=(shelf or "Miscellaneous").strip().title(), summary=summary.strip(),
                    sources=sources, sources_checked=verified, updated=now(),
                    words=len(content.split()), revisions=book["revisions"] + (1 if existing else 0))
        os.makedirs(_path("books"), exist_ok=True)
        with open(_path("books", book["id"] + ".md"), "w", encoding="utf-8") as f:
            f.write(content.strip() + "\n")
        if not existing:
            self.shelves.append(book)
        return book, bool(existing)

    # ---- wishes --------------------------------------------------------
    def add_wish(self, topic, why):
        wish = {"id": f"w{len(self.wishes) + 1}", "topic": topic.strip(), "why": (why or "").strip(),
                "added": now(), "status": "want"}
        self.wishes.append(wish)
        return wish

    def wish(self, wish_id):
        return next((w for w in self.wishes if w["id"] == wish_id), None)

    def open_wishes(self):
        return [w for w in self.wishes if w["status"] in ("want", "learning")]

    # ---- notes ---------------------------------------------------------
    def add_note(self, author, text, source="local", ref=None):
        note = {"id": f"n{len(self.notes) + 1}", "from": author, "text": text.strip()[:2000],
                "at": now(), "source": source, "ref": ref}
        self.notes.append(note)
        return note

    def pending_notes(self):
        return [n for n in self.notes if not n.get("reply") and not n.get("outgoing")]

    def specimen(self, key):
        key = slug(str(key))
        live = [s for s in self.specimens if s["status"] != "released"]
        return next((s for s in live if s["id"] == key), None) or next(
            (s for s in live if slug(s["spec"]["name"]) == key), None)

    def room(self, key):
        key = slug(str(key))
        return next((r for r in self.rooms if r["id"] == key or slug(r["name"]) == key), None)

    def save(self):
        save("self.json", self.home)
        save("companions.json", self.companions)
        save("shelves.json", self.shelves)
        save("wishlist.json", self.wishes)
        save("notes.json", self.notes)
        save("goals.json", self.goals)
        save("requests.json", self.requests)
        save("music.json", self.music)
        save("specimens.json", self.specimens)
        save("rooms.json", self.rooms)
        save("recent.json", self.recent)
        save("brain.json", self.brain_status)
