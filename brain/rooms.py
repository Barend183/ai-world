"""The AI's home: the study it starts in, plus any rooms and yards it decides to build and decorate.

Furniture is either a ready-made piece from CATALOG (tinted with its own colour) or pixel art
the AI draws itself (see specimens.sprite).
"""
import re

from .specimens import COLOR, SpecError, sprite
from .world import now, slug

MAX_ROOMS = 10
MAX_ITEMS = 18
SIZES = {"small": 320, "medium": 400, "large": 480}
PATTERNS = {"plain", "stripes", "dots", "brick", "wood", "checks", "tiles", "wallpaper"}
FLOORS = {"wood", "tile", "carpet", "stone", "grass", "dirt", "sand", "checks", "concrete"}
CATALOG = {
    "floor": ["table", "chair", "stove", "oven", "fridge", "counter", "sink", "sofa", "armchair", "lamp", "rug",
              "cabinet", "bookcase", "bed", "desk", "plant", "tree", "bush", "flowerbed", "fence", "bench",
              "workbench", "tv", "pond", "shed", "barbecue", "piano", "easel", "telescope", "train_table", "garage_door"],
    "wall": ["painting", "shelf", "clock", "window", "poster", "mirror", "cupboard", "lights", "plaque"],
}
PRESETS = set(CATALOG["floor"]) | set(CATALOG["wall"])

# The study's own furniture, which the AI can redraw with pixel art (drawn standing on its anchor).
STUDY_PIECES = ["bookshelf", "wishboard", "window", "armchair", "desk", "computer", "door", "mailbox", "bed", "alarm_clock", "plant", "rug"]

STUDY = {"id": "study", "name": "Study", "builtin": True, "kind": "indoor", "width": 320, "items": [],
         "purpose": "Where I live: my shelves, computer, wishlist board and bed."}


def _color(c, default):
    return c if isinstance(c, str) and COLOR.match(c) else default


def build(world, args):
    """Build a new room, or rebuild/repaint one with the same name (it keeps its furniture).
    The study can be repainted (walls, pattern, floor) but not resized."""
    name = str(args.get("name", "")).strip()
    if not name:
        raise SpecError("the room needs a name")
    rid = slug(name)
    old = world.room(rid)
    if not old and len(world.rooms) >= MAX_ROOMS:
        raise SpecError(f"your world already has {MAX_ROOMS} rooms")
    was = old or {}
    paint = dict(
        wall=_color(args.get("wall"), was.get("wall", "#c9b18f")),
        pattern=args.get("pattern") if args.get("pattern") in PATTERNS else was.get("pattern", "plain"),
        pattern_color=_color(args.get("pattern_color"), was.get("pattern_color", "#b89e7c")),
        floor_color=_color(args.get("floor_color"), was.get("floor_color")),
        updated=now(),
    )
    if old and old.get("builtin"):
        paint["floor"] = args.get("floor") if args.get("floor") in FLOORS else was.get("floor", "wood")
        old.update(paint, painted=True)
        return old, True
    kind = str(args.get("kind", was.get("kind", "indoor"))).lower()
    kind = "outdoor" if kind == "outdoor" else "indoor"
    room = old or {"id": rid, "items": [], "built": now()}
    windows = args.get("windows", was.get("windows", 1))
    room.update(
        paint, name=name[:40], kind=kind, purpose=str(args.get("purpose", was.get("purpose", "")))[:200],
        width=SIZES.get(str(args.get("size", "")).lower(), was.get("width", 400 if kind == "outdoor" else 320)),
        floor=args.get("floor") if args.get("floor") in FLOORS else was.get("floor", "grass" if kind == "outdoor" else "wood"),
        windows=min(max(int(windows), 0), 3) if str(windows).isdigit() else 1,
    )
    if not old:
        world.rooms.append(room)
    return room, bool(old)


def decorate(world, room_id, item):
    room = world.room(room_id or "study")
    if not room:
        raise SpecError(f"there's no room called '{room_id}'. Your rooms: {', '.join(r['id'] for r in world.rooms)}")
    if not isinstance(item, dict) or not str(item.get("name", "")).strip():
        raise SpecError("the item needs a name")
    name = str(item["name"]).strip()[:40]
    preset = str(item.get("preset", "")).lower().replace(" ", "_") or None
    art = sprite(item.get("sprite")) if item.get("sprite") else None
    if not art and preset not in PRESETS:
        raise SpecError(f"give a preset from the catalog or draw a sprite. Floor: {', '.join(CATALOG['floor'])}. "
                        f"Wall: {', '.join(CATALOG['wall'])}")
    place = item.get("place") if item.get("place") in ("wall", "floor") else ("wall" if preset in CATALOG["wall"] else "floor")
    try:
        x = min(max(float(item.get("x", 0.5)), 0.0), 1.0)
    except (TypeError, ValueError):
        x = 0.5
    iid = slug(name)
    old = next((i for i in room["items"] if i["id"] == iid), None)
    if not old and len(room["items"]) >= MAX_ITEMS:
        raise SpecError(f"{room['name']} is full; remove something first")
    entry = {"id": iid, "name": name, "preset": None if art else preset, "sprite": art, "place": place, "x": x,
             "color": _color(item.get("color"), None), "added": now()}
    if old:
        old.update(entry)
    else:
        room["items"].append(entry)
    return room, old or entry, bool(old)


def remove(world, room_id, item_name):
    room = world.room(room_id or "study")
    if not room:
        raise SpecError(f"there's no room called '{room_id}'")
    key = slug(str(item_name))
    item = next((i for i in room["items"] if i["id"] == key), None)
    if not item:
        raise SpecError(f"there's no '{item_name}' in {room['name']}")
    room["items"].remove(item)
    return room, item


def describe(world):
    lines = []
    for r in world.rooms:
        stuff = ", ".join(f"{i['name']} ({i['place']}, x={i['x']:.2f})" for i in r["items"]) or "no added furniture"
        size = {v: k for k, v in SIZES.items()}.get(r["width"], "")
        look = "" if r.get("builtin") else f" {size} {r['kind']}, {r['pattern']} {r['wall']} walls, {r['floor']} floor."
        if r.get("builtin"):
            redrawn = sorted(r.get("skins", {}))
            look = (f" Built in (you can restyle these pieces): {', '.join(STUDY_PIECES)}"
                    + (f"; you've redrawn: {', '.join(redrawn)}" if redrawn else "") + "."
                    + (f" Painted: {r.get('pattern', 'plain')} {r.get('wall')} walls, {r.get('floor')} floor." if r.get("painted") else ""))
            stuff = stuff.replace("no added furniture", "nothing else added")
        lines.append(f"- [{r['id']}] {r['name']}:{look} {r.get('purpose', '')} Furniture you added: {stuff}.")
    return lines


def restyle(world, args):
    """Redraw something with new pixel art (or "sprite": null to go back to how it looked before)."""
    from . import specimens
    raw = args.get("sprite")
    if args.get("specimen"):
        sp = world.specimen(args["specimen"])
        if not sp:
            raise SpecError("there's no creation with that id")
        sp["spec"]["sprite"] = specimens.sprite(raw, sp["spec"]["vars"], {x["name"] for x in sp["spec"]["seasons"]}) if raw else None
        sp["state_sprite"] = None
        specimens.advance(sp)
        return sp["room"], sp["spec"]["name"], sp
    if str(args.get("piece", "")).lower() in ("me", "self", "myself", "sprout"):
        look = world.me.setdefault("look", {})
        colors = args.get("colors") if isinstance(args.get("colors"), dict) else {}
        look["colors"] = {**look.get("colors", {}), **{k: v for k, v in colors.items() if k in ("body", "belly", "leaf", "cheeks", "eyes") and _color(v, None)}}
        if raw:
            look["sprite"] = sprite(raw)
            if isinstance(raw, dict) and raw.get("sleeping"):   # optional drawing of him tucked in bed
                look["sleeping"] = sprite({"palette": raw["palette"], "pixels": raw["sleeping"]})
        elif "sprite" in args:
            look.pop("sprite", None)
            look.pop("sleeping", None)
        return world.me.get("room", "study"), "myself", None
    if args.get("surface"):
        room = world.room(args.get("room") or "study")
        surface = str(args["surface"]).lower()
        if not room or surface not in ("wall", "floor"):
            raise SpecError('surface needs a room and "wall" or "floor"')
        if raw:
            tile = sprite(raw)
            if max(len(r) for r in tile["pixels"]) > 48 or len(tile["pixels"]) > 48:
                raise SpecError("a texture tile can be at most 48 by 48 (it repeats across the whole surface)")
            room[surface + "_tile"] = tile
        else:
            room.pop(surface + "_tile", None)
        return room["id"], f"the {room['name']} {surface}", None
    if args.get("piece"):
        piece = str(args["piece"]).lower().replace(" ", "_")
        if piece not in STUDY_PIECES:
            raise SpecError(f"the study's own pieces are: {', '.join(STUDY_PIECES)}")
        skins = world.room("study").setdefault("skins", {})
        if raw:
            skins[piece] = sprite(raw)
        else:
            skins.pop(piece, None)
        return "study", f"the study's {piece}", None
    room = world.room(args.get("room") or "study")
    item = room and next((i for i in room["items"] if i["id"] == slug(str(args.get("item", "")))), None)
    if not item:
        raise SpecError("say which creation (specimen), piece of the study (piece) or item in a room (room + item) to restyle")
    if not raw and not item.get("preset"):
        raise SpecError("that item is your own drawing; give it a new sprite instead")
    item["sprite"] = sprite(raw) if raw else None
    return room["id"], item["name"], None


def art_of(world, args):
    """The pixel art for something, to look at: (name, sprite) or raises."""
    if args.get("specimen"):
        sp = world.specimen(args["specimen"])
        if not sp:
            raise SpecError("there's no creation with that id")
        art = sp["spec"].get("sprite")
        if art and sp.get("state_sprite") is not None:
            art = {**art, "pixels": art["states"][sp["state_sprite"]]["pixels"]}
        return sp["spec"]["name"], art
    if str(args.get("piece", "")).lower() in ("me", "self", "myself", "sprout"):
        return "yourself", world.me.get("look", {}).get("sprite")
    if args.get("surface"):
        room = world.room(args.get("room") or "study")
        return f"the {args['surface']} texture", room and room.get(str(args["surface"]).lower() + "_tile")
    if args.get("piece"):
        return f"the study's {args['piece']}", world.room("study").get("skins", {}).get(str(args["piece"]).lower().replace(" ", "_"))
    room = world.room(args.get("room") or "study")
    item = room and next((i for i in room["items"] if i["id"] == slug(str(args.get("item", "")))), None)
    if not item:
        raise SpecError("there's no such item")
    return item["name"], item.get("sprite")
