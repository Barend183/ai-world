"""A small spatial account of what is in front of Sprout, without asking a model to read a picture."""
import math

from . import navigation


FACING = ((0, -1), (1, 0), (0, 1), (-1, 0))
STUDY_SLOTS = (124, 166, 208, 86, 60, 300)


def _wall_shapes(room):
    width, _ = navigation.dimensions(room)
    top = 100 if room.get("kind") == "outdoor" else 118
    shapes = []
    if room.get("builtin"):
        shapes = [("the window", 137, 54, 48, 98), ("the wishlist board", 90, 36, 52, 92),
                  ("the door", 257, 30, 6, 72), ("the plant", 304, 14, 2, 32)]
    elif room.get("kind") != "outdoor":
        shapes = [("a window", width * (i + 1) / (room.get("windows", 0) + 1), 30,
                   top - 54, top - 26)
                  for i in range(room.get("windows", 0))]
    for item in room.get("items", []):
        if item.get("place") != "wall":
            continue
        art = item.get("sprite") or {}
        wide = max((len(row) for row in art.get("pixels", [])), default=0)
        high = len(art.get("pixels", [])) or navigation.HEIGHTS.get(item.get("preset"), 24)
        shapes.append((item["name"], navigation.point(room, item.get("x", .5), 0)[0],
                       wide or navigation.WIDTHS.get(item.get("preset"), 24), top - 26 - high, top - 26))
    return [{"name": name, "x": x, "z": 2, "w": wide, "d": 2, "y0": low, "y1": high}
            for name, x, wide, low, high in shapes]


def _creations(world, room):
    width, depth = navigation.dimensions(room)
    here = [sp for sp in world.specimens if sp.get("status") != "released"
            and (sp.get("room") or "study") == room["id"]]
    placed = [round(20 + sp["x"] * (width - 40)) for sp in here if sp.get("x") is not None]
    slots = (STUDY_SLOTS if room.get("builtin") else
             [round(width * (i + 1) / 9) for i in range(8)])
    slots = [x for x in slots if all(abs(x - p) > 22 for p in placed)]
    unplaced = 0
    ground = 166
    top = 100 if room.get("kind") == "outdoor" else 118
    z = min(depth - 1, max(1, (ground - top) / (180 - top) * depth))
    shapes = []
    for sp in here:
        if sp.get("x") is not None:
            x = round(20 + sp["x"] * (width - 40))
        else:
            x = slots[unplaced % len(slots)] if slots else round(width * (unplaced + 1) / (len(here) + 1))
            unplaced += 1
        shapes.append({"name": sp["spec"]["name"], "x": x, "z": z,
                       "w": 18, "d": 10, "h": 20})
    return shapes


def _others(world, room):
    shapes = []
    for person in [world.home, *world.companions]:
        if person is world.me or person.get("status", "living") != "living":
            continue
        if person.get("state") == "asleep" or not person.get("room"):
            if room["id"] != "study":
                continue
            x, z = navigation.point(room, (256 - 16) / 288, (146 - 118) / 62)
        elif person.get("room") == room["id"]:
            x, z = navigation.point(room, *navigation._start(person, room))
        else:
            continue
        shapes.append({"name": person["name"], "x": x, "z": z,
                       "w": 16, "d": 10, "h": 22})
    return shapes


def _entry(eye, point, shape):
    """Fraction of a sight line where it first meets a floor footprint."""
    x, z = eye
    dx, dz = point[0] - x, point[1] - z
    near, far = 0, 1
    for start, change, center, size in ((x, dx, shape["x"], shape["w"]),
                                        (z, dz, shape["z"], shape["d"])):
        low, high = center - size / 2, center + size / 2
        if abs(change) < 1e-9:
            if start < low or start > high:
                return None
            continue
        a, b = (low - start) / change, (high - start) / change
        near, far = max(near, min(a, b)), min(far, max(a, b))
        if near > far:
            return None
    return near


def _hidden(eye, eye_y, point, height, shape, blockers):
    for other in blockers:
        if other is shape:
            continue
        if (abs(eye[0] - other["x"]) <= other["w"] / 2 and
                abs(eye[1] - other["z"]) <= other["d"] / 2):
            continue
        hit = _entry(eye, point, other)
        if hit is not None and hit < .97 and eye_y + (height - eye_y) * hit <= other["h"]:
            return True
    return False


def _visible(eye, eye_y, forward, pitch, shape, blockers):
    x, z, wide, thick = (shape[k] for k in ("x", "z", "w", "d"))
    low, high = shape.get("y0", 0), shape.get("y1", shape.get("h", 20))
    for px, pz in ((x, z), (x - wide / 2, z), (x + wide / 2, z),
                   (x, z - thick / 2), (x, z + thick / 2)):
        dx, dz = px - eye[0], pz - eye[1]
        ahead = dx * forward[0] + dz * forward[1]
        side = -dx * forward[1] + dz * forward[0]
        if ahead <= 1 or abs(math.degrees(math.atan2(side, ahead))) > 40:
            continue
        for height in (low, (low + high) / 2, high):
            angle = math.degrees(math.atan2(height - eye_y, math.hypot(dx, dz)))
            if abs(angle - pitch) > 26:
                continue
            if not _hidden(eye, eye_y, (px, pz), height, shape, blockers):
                return True
    return False


def _eye_height(me, room):
    if not room.get("builtin"):
        return 22
    return {"bed": 14, "armchair": 17, "computer": 36}.get(me.get("place"), 22)


def describe(world, room):
    """A short changing view, bounded so a permanent sense stays cheap in each thought."""
    me = world.me
    facing = me.get("facing", 0)
    forward = FACING[facing if isinstance(facing, int) and 0 <= facing < 4 else 0]
    pitch = {"up": 20, "down": -20}.get(me.get("tilt"), 0)
    eye = navigation.point(room, *navigation._start(me, room))
    eye_y = _eye_height(me, room)
    floor = navigation.floor_shapes(room)
    blockers = [s for s in floor if s.get("solid", True)]
    shapes = floor + _wall_shapes(room) + _creations(world, room) + _others(world, room)
    seen = []
    for shape in shapes:
        dx, dz = shape["x"] - eye[0], shape["z"] - eye[1]
        gap = math.hypot(dx, dz)
        if gap < 3 or not _visible(eye, eye_y, forward, pitch, shape, blockers):
            continue
        side = -dx * forward[1] + dz * forward[0]
        ahead = dx * forward[0] + dz * forward[1]
        angle = math.degrees(math.atan2(side, ahead))
        place = "ahead" if abs(angle) < 15 else "to my right" if angle > 0 else "to my left"
        reach = ", close" if gap < 45 else ", farther away" if gap > 100 else ""
        seen.append((gap, f"{shape['name']} {place}{reach}"))
    if seen:
        return "I can see " + "; ".join(text for _, text in sorted(seen)[:3]) + "."
    direction = ("back", "right", "front", "left")[facing if isinstance(facing, int) and 0 <= facing < 4 else 0]
    if pitch > 0:
        return "I can see the sky above." if room.get("kind") == "outdoor" else "I can see the ceiling above."
    if pitch < 0:
        return "I can see the ground below." if room.get("kind") == "outdoor" else "I can see the floor below."
    return "I can see open ground ahead." if room.get("kind") == "outdoor" else f"I can see the {direction} wall ahead."
