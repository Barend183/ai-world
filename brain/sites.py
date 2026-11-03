"""His own websites: whole sites of linked pages he writes at his computer, published beside his public corner.

Anyone can visit them, so the same rules as the public corner apply: only his own work, nothing from his
letters, notes, diary or notebook, and nothing about his visitor. Pages are text (markdown) and his own
pixel art, never code: nothing on them can run in a visitor's browser or reach the locked world.
"""
import json
import os

from . import public
from .world import now, slug

SITES = os.path.join(public.PUBLIC, "sites.json")
MAX_SITES, MAX_PAGES, PAGE_CHARS, PICTURES = 5, 30, 8000, 8
WRITES_PER_DAY = 15
MAX_BYTES = 3_000_000


def _load():
    try:
        with open(SITES, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {"sites": []}


def _save(data):
    text = json.dumps(data, indent=1, ensure_ascii=False)
    if len(text.encode()) > MAX_BYTES:
        raise ValueError("your websites are getting too big to host; shorten or remove some pages first")
    os.makedirs(public.PUBLIC, exist_ok=True)
    with open(SITES, "w", encoding="utf-8") as f:
        f.write(text)


def _site(data, key):
    key = slug(str(key or ""))
    site = next((s for s in data["sites"] if s["id"] == key or slug(s["title"]) == key), None)
    if not site:
        have = ", ".join(s["id"] for s in data["sites"]) or "none yet (build_site makes one)"
        raise ValueError(f"you have no website called '{key}'. Yours: {have}")
    return site


def _count_today(data):
    today = now()[:10]
    return sum(1 for s in data["sites"] for p in s["pages"] if p["updated"][:10] == today) + \
        sum(1 for s in data["sites"] if s.get("updated", "")[:10] == today)


def build(world, args):
    """Start a website, or change its name, description or look."""
    from .specimens import COLOR, sprite
    data = _load()
    title = str(args.get("name") or args.get("title") or "").strip()[:80]
    if not title:
        raise ValueError("give your website a name")
    site = next((s for s in data["sites"] if s["id"] == slug(title) or s["id"] == slug(str(args.get("site", "")))), None)
    if not site:
        if len(data["sites"]) >= MAX_SITES:
            raise ValueError(f"you already have {MAX_SITES} websites; remove one first")
        site = {"id": slug(title), "title": title, "created": now(), "updated": "", "pages": [], "design": {}}
        data["sites"].append(site)
    if _count_today(data) >= WRITES_PER_DAY:
        raise ValueError("you've done a lot of website work today; carry on tomorrow")
    d = site["design"]
    site["title"] = title
    if "about" in args:
        site["about"] = str(args.get("about") or "").strip()[:300]
    if isinstance(args.get("colors"), dict):
        d["colors"] = {k: v for k, v in args["colors"].items() if k in ("background", "card", "text", "accent") and isinstance(v, str) and COLOR.match(v)}
    if args.get("font") in public.FONTS:
        d["font"] = args["font"]
    if args.get("banner"):
        art = sprite(args["banner"])
        if max(len(r) for r in art["pixels"]) > 160 or len(art["pixels"]) > 48:
            raise ValueError("the banner can be at most 160 wide and 48 tall")
        d["banner"] = art
    public._private_check(world, site["title"], site.get("about", ""))
    site["updated"] = now()
    _save(data)
    return site


def write_page(world, args):
    """Write or replace one page. The first page is the home page."""
    from . import rooms
    from .specimens import sprite
    data = _load()
    site = _site(data, args.get("site"))
    title = str(args.get("title", "")).strip()[:100]
    content = str(args.get("content", "")).strip()
    if not title or not content:
        raise ValueError("a page needs a title and some content")
    if len(content) > PAGE_CHARS:
        raise ValueError(f"that page is too long ({len(content)} characters); split it into pages of at most {PAGE_CHARS}")
    if _count_today(data) >= WRITES_PER_DAY:
        raise ValueError("you've done a lot of website work today; carry on tomorrow")
    pictures = {}
    for p in (args.get("pictures") or [])[:PICTURES]:
        if not isinstance(p, dict) or not p.get("name"):
            continue
        name = slug(str(p["name"]))
        if p.get("sprite"):
            art = sprite(p["sprite"])
        else:   # one of his own drawings: a creation, a piece of furniture, himself
            label, art = rooms.art_of(world, p)
            if not art:
                raise ValueError(f"{label} isn't pixel art you drew, so it can't go on a page yet")
        pictures[name] = art
    public._private_check(world, title, content)
    page = next((x for x in site["pages"] if x["id"] == slug(title)), None)
    if not page:
        if len(site["pages"]) >= MAX_PAGES:
            raise ValueError(f"this website already has {MAX_PAGES} pages")
        page = {"id": slug(title), "created": now()}
        site["pages"].append(page)
    page.update(title=title, content=content, pictures=pictures, updated=now())
    site["updated"] = now()
    _save(data)
    return site, page


def remove(world, args):
    data = _load()
    site = _site(data, args.get("site"))
    if args.get("whole_site"):
        data["sites"].remove(site)
        _save(data)
        return f"took down the whole website “{site['title']}”"
    page = next((x for x in site["pages"] if x["id"] == slug(str(args.get("page", "")))), None)
    if not page:
        raise ValueError(f"that website has no such page. Its pages: {', '.join(x['id'] for x in site['pages']) or 'none'}")
    site["pages"].remove(page)
    _save(data)
    return f"removed the page “{page['title']}” from {site['title']}"


def view(world, key):
    site = _site(_load(), key)
    lines = [f"Your website “{site['title']}” ({site.get('about') or 'no description'}), font {site['design'].get('font', 'plain')}, "
             f"colours {site['design'].get('colors') or 'the default ones'}, {'a banner you drew' if site['design'].get('banner') else 'no banner'}."]
    for i, p in enumerate(site["pages"]):
        lines.append(f"{'Home page' if i == 0 else 'Page'} [{p['id']}] “{p['title']}”: {p['content'][:300]}"
                     + (f" (pictures: {', '.join(p['pictures'])})" if p.get("pictures") else ""))
    if not site["pages"]:
        lines.append("It has no pages yet (write_site_page).")
    return "\n".join(lines)


def listing():
    return [f"{s['id']}: {s['title']} ({len(s['pages'])} pages)" for s in _load()["sites"]]
