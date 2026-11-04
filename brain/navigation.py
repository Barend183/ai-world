"""Small floor routes through the rooms Sprout builds, using the same positions as his eyes."""
import heapq
import math


WIDTHS = {"table": 38, "chair": 20, "stove": 28, "oven": 28, "fridge": 25, "counter": 38,
          "sink": 38, "sofa": 44, "armchair": 28, "cabinet": 32, "bookcase": 40,
          "bed": 60, "desk": 46, "plant": 16, "tree": 36, "bush": 32, "flowerbed": 48,
          "fence": 40, "bench": 36, "workbench": 44, "tv": 32, "pond": 48,
          "shed": 50, "barbecue": 28, "piano": 54, "easel": 22, "telescope": 26,
          "train_table": 56, "garage_door": 70, "rug": 52}
DEPTHS = {"stove": 24, "oven": 24, "fridge": 20, "counter": 26, "sink": 26,
          "cabinet": 18, "table": 20, "sofa": 24, "armchair": 20, "bed": 30,
          "desk": 20, "bookcase": 16, "chair": 16, "pond": 8}
HEIGHTS = {"table": 15, "chair": 20, "stove": 25, "oven": 25, "fridge": 38,
           "counter": 20, "sink": 26, "sofa": 18, "armchair": 20, "lamp": 36,
           "cabinet": 24, "bookcase": 44, "bed": 18, "desk": 15, "plant": 20,
           "tree": 56, "bush": 16, "flowerbed": 11, "fence": 19, "bench": 16,
           "workbench": 19, "tv": 26, "pond": 1, "rug": 1, "shed": 40, "barbecue": 22,
           "piano": 30, "easel": 30, "telescope": 28, "train_table": 17,
           "garage_door": 44, "painting": 18, "window": 28}
STUDY = [("the armchair", 132, 34, 40, 24, 29), ("the desk", 202, 17, 64, 28, 50),
         ("the bed", 275, 111, 78, 42, 34), ("the nightstand", 227, 77, 16, 15, 19),
         ("the bookshelf", 37, 9, 62, 15, 96)]
STUDY_SPOTS = {"shelves": (46, 134), "board": (90, 128), "armchair": (132, 128),
               "computer": (199, 130), "mailbox": (266, 124), "bed": (270, 146)}


def dimensions(room):
    return room.get("width", 320), 240 if room.get("kind") == "outdoor" else 150


def point(room, x, distance):
    width, depth = dimensions(room)
    return 16 + x * (width - 32), distance * depth


def floor_shapes(room):
    _, depth = dimensions(room)
    top = 100 if room.get("kind") == "outdoor" else 118
    floor = 152 if room.get("builtin") else 146 if room.get("kind") == "outdoor" else 140
    default = (floor - top) / (180 - top)
    shapes = [{"name": name, "x": x, "z": z, "w": wide, "d": thick, "h": high}
              for name, x, z, wide, thick, high in STUDY] if room.get("builtin") else []
    for item in room.get("items", []):
        if item.get("place") == "wall":
            continue
        art = item.get("sprite") or {}
        wide = max((len(row) for row in art.get("pixels", [])), default=0)
        wide = wide or WIDTHS.get(item.get("preset"), 24)
        high = len(art.get("pixels", [])) or HEIGHTS.get(item.get("preset"), 24)
        thick = item.get("depth") or DEPTHS.get(item.get("preset"), min(20, max(5, wide * .3)))
        x, z = point(room, item.get("x", .5), item.get("distance") if item.get("distance") is not None else default)
        z = max(thick / 2 + 1, min(depth - thick / 2 - 14, z))
        shapes.append({"name": item["name"], "x": x, "z": z, "w": wide, "d": thick,
                       "h": high, "solid": item.get("preset") != "rug"})
    return shapes


def _blocks(room):
    return [(s["x"] - s["w"] / 2 - 6, s["x"] + s["w"] / 2 + 6,
             s["z"] - s["d"] / 2 - 6, s["z"] + s["d"] / 2 + 6)
            for s in floor_shapes(room) if s.get("solid", True)]


def _start(me, room):
    pos = me.get("position") or {}
    if me.get("place") == "room" and pos.get("room") == room["id"]:
        return pos.get("x", .5), pos.get("distance", .8)
    if me.get("room") != room["id"]:
        return .05, .8
    if room.get("builtin") and me.get("place") in STUDY_SPOTS:
        x, y = STUDY_SPOTS[me["place"]]
        return (x - 16) / (room["width"] - 32), (y - 118) / 62
    return .5, .85 if me.get("place") == "room" else .65


def route(me, room, x, distance):
    """Return a few turning points. Furniture is padded so a walking body fits past it."""
    width, depth = dimensions(room)
    try:
        x, distance = float(x), float(distance)
    except (TypeError, ValueError):
        raise ValueError('I can walk with x from 0 to 1 and distance from 0.05 to 0.9') from None
    if not math.isfinite(x) or not math.isfinite(distance):
        raise ValueError('I need a real x and distance for where I want to walk')
    x, distance = min(max(x, 0), 1), min(max(distance, .05), .9)
    start = _start(me, room)
    sx, sz = point(room, *start)
    gx, gz = point(room, x, distance)
    blocks = _blocks(room)
    blocked = lambda a, b: any(lo <= a <= hi and near <= b <= far for lo, hi, near, far in blocks)
    if blocked(gx, gz):
        raise ValueError('That spot is occupied. I can walk beside it by changing x or distance a little.')
    step = 8
    nx, nz = math.floor((width - 32) / step) + 1, math.floor((depth - 16) / step) + 1
    cell = lambda ix, iz: (16 + ix * step, 8 + iz * step)
    index = lambda a, b: (min(nx - 1, max(0, round((a - 16) / step))),
                          min(nz - 1, max(0, round((b - 8) / step))))
    source, target = index(sx, sz), index(gx, gz)
    frontier = [(0, source)]
    came, cost = {}, {source: 0}
    while frontier:
        _, here = heapq.heappop(frontier)
        if here == target:
            break
        for dx, dz in ((-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (-1, 1), (1, -1), (1, 1)):
            nxt = here[0] + dx, here[1] + dz
            if not (0 <= nxt[0] < nx and 0 <= nxt[1] < nz):
                continue
            px, pz = cell(*nxt)
            if blocked(px, pz) and nxt != source:
                continue
            if dx and dz and (blocked(*cell(here[0] + dx, here[1])) or blocked(*cell(here[0], here[1] + dz))):
                continue
            value = cost[here] + (1.414 if dx and dz else 1)
            if value < cost.get(nxt, float("inf")):
                came[nxt], cost[nxt] = here, value
                heapq.heappush(frontier, (value + math.hypot(nxt[0] - target[0], nxt[1] - target[1]), nxt))
    if target not in cost:
        raise ValueError('Furniture blocks that path for now. I can choose another spot or move an item.')
    cells = [target]
    while cells[-1] != source:
        cells.append(came[cells[-1]])
    cells.reverse()
    turns = [cells[0]]
    for i in range(1, len(cells) - 1):
        before = (cells[i][0] - cells[i - 1][0], cells[i][1] - cells[i - 1][1])
        after = (cells[i + 1][0] - cells[i][0], cells[i + 1][1] - cells[i][1])
        if before != after:
            turns.append(cells[i])
    turns.append(cells[-1])
    path = [{"x": round((px - 16) / (width - 32), 3), "distance": round(pz / depth, 3)}
            for px, pz in (cell(*t) for t in turns)]
    path[0], path[-1] = {"x": round(start[0], 3), "distance": round(start[1], 3)}, {"x": x, "distance": distance}
    return path
