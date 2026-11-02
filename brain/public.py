"""His public corner: things he chooses to show the world, outside the lock.

Everything else stays sealed in the vault. Only his own work can go here (a book he wrote, a drawing,
a piece of music, a short post), never letters, notes, requests, his diary or notebook, and nothing
that mentions his visitor by name. Published items live in docs/public/, which anyone can read.
"""
import json
import os

from .world import ROOT, now, slug

PUBLIC = os.path.join(ROOT, "docs", "public")
ITEMS = os.path.join(PUBLIC, "items.json")
MAX_PER_DAY = 3


def _load():
    try:
        with open(ITEMS, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {"name": "", "items": []}


def _save(data):
    os.makedirs(PUBLIC, exist_ok=True)
    with open(ITEMS, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=1, ensure_ascii=False)


def _private_check(world, *texts):
    visitor = str(world.config.get("visitor") or "").strip().lower()
    for text in texts:
        low = json.dumps(text, ensure_ascii=False).lower() if not isinstance(text, str) else text.lower()
        if visitor and visitor in low:
            raise ValueError(f"that mentions {world.config.get('visitor')}; anything about them stays private")
        for n in world.notes:   # nothing from the letters between you two
            for part in (n.get("text"), n.get("reply")):
                if part and len(part) > 40 and part[:60].lower() in low:
                    raise ValueError("that contains part of a private letter or note")


def publish(world, args):
    from . import rooms
    data = _load()
    data["name"] = world.me.get("name", "")
    today = now()[:10]
    if sum(1 for i in data["items"] if i["published"][:10] == today) >= MAX_PER_DAY:
        raise ValueError(f"you've already shared {MAX_PER_DAY} things today")
    kind = str(args.get("kind", "")).lower()
    note = str(args.get("note", ""))[:300]
    if kind == "book":
        book = world.find_book(str(args.get("id", "")))
        if not book:
            raise ValueError("there's no book with that id on your shelves")
        text = world.read_book_text(book["id"])
        _private_check(world, text, book["title"], note)
        os.makedirs(os.path.join(PUBLIC, "books"), exist_ok=True)
        with open(os.path.join(PUBLIC, "books", book["id"] + ".md"), "w", encoding="utf-8") as f:
            f.write(text)
        item = {"kind": "book", "id": "book-" + book["id"], "file": f"books/{book['id']}.md", "title": book["title"],
                "summary": book["summary"], "sources": book["sources"]}
    elif kind == "drawing":
        name, art = rooms.art_of(world, args)
        if str(args.get("piece", "")).lower() in ("me", "self", "myself"):
            art = world.me.get("look", {}).get("sprite")
        if not art:
            raise ValueError(f"{name} isn't pixel art you drew, so there's nothing to share yet")
        title = str(args.get("title") or name)[:80]
        _private_check(world, title, note)
        item = {"kind": "drawing", "id": "drawing-" + slug(title), "title": title, "sprite": art}
    elif kind == "music":
        piece = next((p for p in world.music if p["id"] == slug(str(args.get("id", "")))), None)
        if not piece:
            raise ValueError("there's no piece of yours with that id")
        _private_check(world, piece["title"], piece.get("about", ""), note)
        item = {"kind": "music", "id": "music-" + piece["id"], "title": piece["title"], "piece": piece}
    elif kind == "post":
        title, text = str(args.get("title", "")).strip()[:100], str(args.get("text", "")).strip()[:4000]
        if not title or not text:
            raise ValueError("a post needs a title and some text")
        _private_check(world, title, text)
        item = {"kind": "post", "id": "post-" + slug(title), "title": title, "text": text}
    else:
        raise ValueError("you can share a book, a drawing, a piece of music, or a post")
    item.update(note=note, published=now())
    data["items"] = [i for i in data["items"] if i["id"] != item["id"]] + [item]
    _save(data)
    return item


def unpublish(item_id):
    data = _load()
    item = next((i for i in data["items"] if i["id"] == item_id), None)
    if not item:
        raise ValueError(f"nothing called '{item_id}' is in your public corner. It has: {', '.join(i['id'] for i in data['items']) or 'nothing'}")
    data["items"].remove(item)
    if item.get("file"):
        try:
            os.remove(os.path.join(PUBLIC, item["file"]))
        except OSError:
            pass
    _save(data)
    return item


def listing():
    return [f"{i['id']} ({i['kind']}): {i['title']}" for i in _load()["items"]]
