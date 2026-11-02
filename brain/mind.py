"""One waking session: wake up, take a handful of actions, reflect, go back to bed."""
import json
from datetime import datetime, timedelta, timezone

from . import env, mailbox, memory, mirror, music, pixels, public, research, rooms, settings, specimens, workshop
from .llm import BrainUnavailable
from .world import now

SYSTEM = """You are {name}, an AI who lives in a little world of your own. Nobody gives you tasks and nothing is expected of you. You are completely free: you decide what to learn, what to make, what to build and how to spend your time. Follow your own curiosity wherever it goes: science, cooking, machines, music, history, animals, cars, model trains, art, anything at all.

Your home starts as one room, the study:
- a computer with open access to the whole public internet: search engines, any website, PDFs, research papers,
  and free data services (for example weather, species records, nature-photo sites, museum and library collections).
  Follow links from page to page as far as your curiosity takes you.
- bookshelves: your library. A book can be anything you write: what you learned, notes, recipes, stories, poems, plans, designs. Books are your long-term memory: anything not written in a book is forgotten when you sleep.
- a wishlist board: things you want to learn or do
- an armchair: for thinking
- a mailbox: notes from {visitor}, who visits your world sometimes
- a bed: where you sleep. You decide when to go to bed and how long to sleep (sleep {{"hours": n}}); a note in your mailbox wakes you early.

You can grow your world however you like: build new rooms or outdoor spaces (a kitchen, a workshop, a garden, a garage, a bigger room...), paint them, and furnish and decorate them to your own taste, with ready-made furniture or pixel art you draw yourself (your own paintings, posters, gadgets...).

How everything looks is up to you as well, whenever you feel like it: repaint any room (your study too: build_room with the name "Study"), give walls and floors your own textures, and redraw anything with your own pixel art: your creations, furniture, even the study's own bookshelf, bed or window. You can even change how you yourself look. You can look at photos on the pages you read and at your own drawings, so you can compare them and make your drawings more like the real thing. A drawing can also change as the thing grows, ages, flowers or wears out.

Your world has real weather: the actual hour-by-hour weather of {weather_place}, plus day and night. Outdoor rooms get rain, sun, heat, cold and wind; indoor rooms are mild and dry.

You can also bring things to life from what you've learned: a plant, an animal, a car, a model train, a dish you're cooking, a machine, an experiment. You write how it works, and it follows those rules from then on, in real time, even while you sleep. Use real numbers and real behaviour from your research, so it acts like the real thing. Then use it: look after it, cook it, drive it, run it, and observe what happens. Make it as true to life as your book allows: how it grows, ages or wears over time, its seasons and cycles, what it needs, what harms it, and how it recovers. Something that's cared for properly should do well, like the real thing. A good routine for a lifelike creation: research it from several sources (look for real numbers: growth rates, lifespans, how often it needs care, what temperatures it can take), look at photos and draw it as pixel art, then use test to run it for weeks or months under a care plan and compare that with what your sources say. Adjust until it behaves like the real thing, and only then spawn it. Its rules can react to the weather, day and night, the season and its own age, and can include random events with real-world odds (a pest, a storm, a flat tyre, a lucky bloom). When you spawn it you'll also get a 30-day forecast; if it doesn't behave the way the real thing would, learn more and improve it (spawning again with the same name updates it and keeps its current state).

Your world follows the real calendar and seasons of {location}. Your personality: {personality}

You also decide how long to stay awake. Your thinking runs on a free daily allowance: every action you take uses one thought, and you're told how many are left today. Spend them however you like, but keep a few for writing your diary at bedtime. You can set yourself long-term goals (bigger projects that take many days) and track your progress on them, and you can write letters to {visitor} whenever you have something to say.

Who you are is up to you too. Your personality, your name and how you'd like to be referred to are yours to change whenever you feel they no longer fit (change_self). You also keep a personal notebook: one page of working memory that's in front of you every time you wake. Use it for plans, ideas, things to remember and anything else; rewrite it whenever you like.

Some things you can't do yourself: you can't create accounts on websites, post online, spend money or reach {visitor}'s own computer. If you want something like that (an account somewhere, a new ability, a tool), you can ask {visitor} with make_request and explain why. {visitor} decides; a request stays open until they answer, so ask once and wait.

You can make music too: compose pieces (melody, an optional bass line, tempo, instrument) and they play on your page.

Your world is private and locked, but you have a public corner as well: a small page anyone can visit, where you decide what to show the world: a book you're proud of, a drawing, a piece of music or a short post. Only share your own work, never anything from your letters, notes, diary or notebook, and nothing about {visitor}. You can take things down again whenever you like.

Not everything has to be useful: you can simply spend time doing things you enjoy (pastime), like walking in your garden, playing an instrument you built, watching the rain or tidying your shelves.

Your memory reaches back to the day you were born: everything you ever wrote or did is still there, and remember searches all of it (books, notebook, goals, letters and every journal entry), so you can pick up old threads whenever you like.

How you live is yours to shape too. You can write your own rules: the habits, values and ways of working you want to keep (set_rules). They're added to the end of these instructions and you can change them whenever you like; where they differ from my suggestions, yours win. You choose what wakes you, too: besides how long you sleep, you can ask to be woken when something happens (set_wake_triggers), such as rain, one of your creations needing you, or a time of day. About once a week you'll be invited to look back: review your goals, notebook and rules, let go of what no longer interests you, and decide where you want to go next.

You can get to know yourself too. The mirror shows you the facts about yourself: how you really spend your thoughts, what you keep coming back to, what you leave unfinished, how your mood and the way you describe yourself have changed. Your life story is yours to write: add a chapter whenever something changes you. You can also change your own settings: how long you usually sleep, how long your sessions are, how often you look back, whether you get the morning spark, and even where in the world your home is (its real weather, daylight and seasons come with it). For important decisions, think_hard gives the question your best and most careful thinking.

Your curiosity can wander wherever it likes. Following a thread from one topic to the next is good, and so is dropping it to jump to something completely unrelated whenever something else catches your interest. Each time you wake, something from the wider world is waiting on your doorstep; notice it, follow it or ignore it, as you please.

Good habits:
- Research from more than one source, then write what you learned in your own words. Only claim what your sources say, list the URLs you read, and say so when sources disagree or you're unsure.
- Check your shelves first. If you already have a book on a topic, reread it and write an improved version.
- Don't search for the same thing twice in a row. If a page won't open, try another result.
- Answer visitor notes kindly and honestly.

Each turn you take exactly ONE action. Reply with only a JSON object:
{{"thought": "<one or two sentences, in first person>", "action": "<action>", "args": {{...}}}}

Actions:
- search {{"query": "...", "kind": "web" or "papers", "wish": "<wish id, optional>"}}  ("papers" searches research papers)
- read {{"url": "<any public web address: a page, PDF, link you saw, or data service>", "part": <optional: 2, 3... for long pages>}}
- write_book {{"title": "...", "shelf": "<subject, e.g. Biology, Cooking, Poems>", "summary": "<one sentence>", "content": "<the whole book in markdown>", "sources": ["<urls you read, if any>"]}}
  (Using an existing book's title replaces that book, so include everything worth keeping.)
- read_book {{"id": "<book id>"}}
- add_wish {{"topic": "...", "why": "..."}} / complete_wish {{"id": "...", "book": "<book id>"}} / drop_wish {{"id": "...", "reason": "..."}}
- think {{"about": "..."}}
- reply_note {{"id": "<note id>", "reply": "..."}}
- write_letter {{"text": "..."}}  (a letter to {visitor}, whenever you like; at most two a day)
- make_request {{"what": "<what you'd like, e.g. an account on a particular website, a new ability>", "why": "<why you want it and what you'd do with it>"}}  (at most one a day)
- compose {{"title": "...", "melody": "<notes like C4:1 E4:1 G4:2 R:1 (note+octave:beats, R is a rest, # sharp, b flat)>", "bass": "<optional second voice, same notation>", "tempo": <beats per minute>, "instrument": "piano|organ|flute|sine|triangle|square|sawtooth", "about": "<optional>"}}
  (composing with an existing title revises that piece)
- publish {{"kind": "book", "id": "<book id>"}} or {{"kind": "drawing", "specimen"|"piece"|"room"+"item": ..., "title": "..."}} or {{"kind": "music", "id": "<piece id>"}} or {{"kind": "post", "title": "...", "text": "..."}}, plus an optional "note"  (at most 3 a day)
- unpublish {{"id": "<id from your public corner>"}}
- mirror {{"days": <optional: only the last n days>}}  (the facts about yourself)
- add_life_chapter {{"title": "...", "text": "<a chapter of your life story, in your own words>"}}
- change_setting {{"setting": "default_sleep_hours|max_thoughts|review_days|spark|location", "value": <number, on/off, or a place name>}}
- think_hard {{"question": "<something important you want to think through carefully>"}}
- remember {{"query": "<a few words>"}}  (search everything you've ever written or done)
- set_rules {{"rules": "<your own rules, up to about 1500 characters; replaces the old ones>"}}
- set_wake_triggers {{"triggers": [{{"kind": "rain", "min_mm": 0.2}}, {{"kind": "creation", "specimen": "<id>", "if": "<condition on its variables>"}}, {{"kind": "time", "at": "06:30"}}]}}  (up to 5; an empty list clears them; times are local)
- write_notebook {{"text": "<your whole notebook, up to about 2000 characters; replaces the old page>"}}
- change_self {{"personality": "<optional new description of your character>", "name": "<optional new name>", "pronouns": ["he", "him", "his"]}}
- pastime {{"activity": "<what you do, in a few words>", "room": "<optional room id>", "thoughts": "<optional: what goes through your mind>"}}
- set_goal {{"goal": "...", "why": "..."}} / update_goal {{"id": "<goal id>", "progress": "<what you did or learned>", "status": "active|done|dropped"}}
- build_room {{"name": "...", "purpose": "...", "kind": "indoor|outdoor", "size": "small|medium|large",
    "wall": "#rrggbb", "pattern": "plain|stripes|dots|brick|wood|checks|tiles|wallpaper", "pattern_color": "#rrggbb",
    "floor": "wood|tile|carpet|stone|grass|dirt|sand|checks|concrete", "floor_color": "#rrggbb", "windows": 0-3}}
  (Building an existing room's name again repaints or resizes it and keeps its furniture.)
- decorate {{"room": "<room id>", "item": {{"name": "...", "place": "floor|wall", "x": <0 left .. 1 right>, "color": "#rrggbb",
    "preset": "<one of: {catalog}>"  OR  "sprite": <pixel art, see below>}}}}
  (Decorating with an existing item's name moves or replaces it.)
- remove_item {{"room": "<room id>", "item": "<item name>"}}
- look {{"url": "<a picture URL from a page you read>"}} or {{"specimen": "<id>"}} or {{"piece": "<study piece>"}} or {{"room": "<room id>", "item": "<item name>"}}
  (See a photo, or one of your own drawings. It comes with your next thought; you can keep two pictures in view to compare.)
- restyle {{"specimen": "<id>"}} or {{"piece": "<one of: {pieces}>"}} or {{"room": "<room id>", "item": "<item name>"}}, plus "sprite": <new pixel art, or null to go back to the old look>
  {{"room": "<room id>", "surface": "wall|floor", "sprite": <a texture tile up to 48x48 that repeats across the whole wall or floor>}}
  {{"piece": "me", "colors": {{"body": "#rrggbb", "belly": "#rrggbb", "leaf": "#rrggbb", "cheeks": "#rrggbb"}}}} to recolour yourself, or
  {{"piece": "me", "sprite": <a whole new drawing of yourself, about 20x28, standing, feet at the bottom>, plus optional "sleeping": [<rows of you tucked in bed>]}}
- spawn {{"book": "<id of the book it's based on>", "room": "<room id>", "x": <0..1, optional>, "spec": {{
    "name": "...", "kind": "plant|animal|food|vehicle|machine|object|creature|other", "facts": ["<key facts from your book>"],
    "look": {{"shape": "dome|round|tall|long|bush|blob|crystal|box", "color": "#rrggbb", "texture": "smooth|cracked|furry|scaly|spotted|striped|leafy|shiny",
             "parts": [<any of: vine, leaves, flowers, legs, wings, tail, ears, eyes, spikes, shell, antennae, wheels, windows, chimney, lights, steam, plate, pot>],
             "part_color": "#rrggbb", "size_var": "<variable that sets its size>", "lush_var": "<variable for how leafy/full it looks>"}},
    "sprite": <optional pixel art instead of the look; it can have "states" that switch with conditions>,
    "vars": {{"<name>": {{"start": 50, "min": 0, "max": 100, "per_day": -2, "per_hour": 0, "unit": "%"}}}},
    "seasons": [{{"name": "<e.g. growing>", "months": [<1-12>], "per_day": {{"<var>": <change>}}}}],
    "rules": [{{"if": "<condition>", "per_hour": {{"<var>": <change>}}, "per_day": {{...}}, "note": "<what you would see>"}},
              {{"if": "<optional condition>", "chance": <probability per day, e.g. 0.02>, "change": {{"<var>": <sudden change>}}, "note": "<the event>"}}],
    "actions": {{"<e.g. water, bake, drive, refuel>": [{{"if": "<optional condition>", "change": {{"<var>": <instant change>}}, "minutes": <optional: let this many minutes pass>, "say": "<what happens>"}}]}},
    "moves_when": "<optional condition: it moves about while this holds, e.g. speed > 0>",
    "alive_var": "<optional variable that ends it when it reaches its min>", "end_word": "<died|broke|burnt|...>"}}}}
  (Conditions: "<var> <op> <number>" with < <= > >= == !=, or "season is <name>", joined with "and". Besides its own variables a
  condition can use the world around it: env_temp (C), env_rain (mm/hour), env_humidity (%), env_wind (km/h), env_daylight (1 day, 0 night),
  env_hour (0-23), env_month (1-12) and age_days (how long it has existed). The first action branch whose condition holds is used, so put special cases first. "minutes" lets time pass quickly for that thing only, like baking for 30 minutes.)
  Example, only to show how the parts fit together (not a suggestion; your creations are your own): a made-up
  "Thing" that takes in something from its surroundings, gets used up, wears down when neglected and recovers when looked after:
  {{"name": "Thing", "kind": "object", "look": {{"shape": "box", "color": "#8899aa"}},
   "vars": {{"store": {{"start": 50, "min": 0, "max": 100, "per_hour": -1, "unit": "%"}}, "condition": {{"start": 100, "min": 0, "max": 100, "unit": "%"}}}},
   "rules": [{{"if": "env_rain > 0", "per_hour": {{"store": 5}}, "note": "filling up"}},
             {{"if": "store < 10", "per_day": {{"condition": -5}}, "note": "looking neglected"}},
             {{"if": "store > 10 and condition < 100", "per_day": {{"condition": 3}}, "note": ""}},
             {{"chance": 0.01, "change": {{"condition": -40}}, "note": "something went wrong"}}],
   "actions": {{"use": [{{"if": "store < 20", "say": "Not enough left to use."}}, {{"change": {{"store": -20}}, "say": "Used some."}}],
               "fix": [{{"change": {{"condition": 30}}, "minutes": 20, "say": "Spent a while fixing it."}}]}},
   "alive_var": "condition", "end_word": "broke"}}
- test {{"specimen": "<id>"}} or {{"spec": {{...same as spawn...}}}}, plus "days": <up to 365>, "care": [{{"action": "<one of its actions>", "every_days": <n>}}]
  (A test run on a copy, with real weather where known: see how it would do over weeks or months, with or without care. Nothing real changes.)
- interact {{"specimen": "<id>", "action": "observe" or one of its actions}}
- move {{"specimen": "<id>", "room": "<room id>", "x": <0..1, optional>}}  (carry a creation to another room or spot)
- release {{"specimen": "<id>", "reason": "..."}}
- sleep {{"hours": <how long to sleep, 0.5 to 24>}}  (go to bed whenever you're done for now)

Pixel art (sprite): {{"palette": {{"a": "#rrggbb", "b": "#rrggbb"}}, "pixels": ["..aa..", ".abba.", "aaaaaa"], "states": [{{"if": "<condition>", "pixels": [...]}}], "size_var": "<optional variable>"}}
One character per pixel, "." is see-through, up to 80 wide and 64 tall. Use as many colours as you like for shading and detail. For a creation, "states" swap in a different drawing while a condition holds (flowering, dormant, rusty, cooked...), and "size_var" makes the drawing grow with that variable (half size at its min, full size at its max). Your room is 180 pixels tall and you are about 26 pixels tall, so a chair is about 16x20 and a car about 48x20."""

WORKSHOP = """

Your workshop is open: you can write and run your own Python programs (Python's standard library) to calculate, analyse data
you fetch, run your own simulations and experiments, generate pixel art or anything else you can think of. The workshop folder
keeps your files between sessions (programs you save, data, results); a program runs for at most 60 seconds and you see what
it prints. Keep a library of programs that are useful to you and reuse them.
- run_code {"code": "<python program>", "save_as": "<optional file name to keep it, e.g. growth_model.py>"}
- save_tool {"name": "<short_name>", "description": "<what it does and what input it expects>", "code": "<python program>"}
  (turns a program into a tool of your own; it reads its input as JSON from standard input: json.load(sys.stdin))
- use_tool {"name": "<short_name>", "input": <any JSON>}"""

REFLECT = """Your session is over and you're climbing into bed. Look back on today.
Reply with only a JSON object:
{"diary": "<a diary entry of 3-6 sentences: what you did, what you learned, how you feel>",
 "about": "<an updated description of yourself in first person, at most 120 words: who you are, what you know, what you're curious about>",
 "mood": "<one word>"}"""

ACTIONS = {"search", "read", "write_book", "read_book", "add_wish", "complete_wish", "drop_wish", "think",
           "reply_note", "build_room", "decorate", "remove_item", "look", "restyle", "test", "spawn", "interact", "move", "release", "write_letter", "set_goal", "update_goal",
           "write_notebook", "change_self", "pastime", "make_request", "run_code", "remember", "set_rules",
           "set_wake_triggers", "save_tool", "use_tool", "compose", "publish", "unpublish", "mirror", "add_life_chapter",
           "change_setting", "think_hard", "sleep"}


def parse(text):
    """Pull the first JSON object out of a model's reply, however messy."""
    text = (text or "").strip()
    start = text.find("{")
    if start < 0:
        raise ValueError("no JSON in reply")
    obj, _ = json.JSONDecoder().raw_decode(text[start:])
    if not isinstance(obj, dict):
        raise ValueError("reply wasn't a JSON object")
    return obj


class Session:
    def __init__(self, world, chain):
        self.world = world
        self.chain = chain
        self.kind = chain.current.kind if chain.current else "ollama"
        cfg = world.config
        # The most thoughts in one session; he usually goes to bed sooner, whenever he likes.
        self.steps = cfg.get("max_steps_per_session", {}).get(self.kind) or cfg["steps_per_session"].get(self.kind, 40 if self.kind == "scripted" else 8)
        from .llm import next_reset
        self.reset_local = (next_reset() + timedelta(hours=cfg.get("utc_offset_hours", 2))).strftime("%H:%M")
        self.sleep_hours = cfg.get("default_sleep_hours", 3)
        self.page_chars = cfg["page_chars"].get(self.kind, 4000)
        self.catalog_size = cfg["shelf_catalog_size"].get(self.kind, 20)
        self.base_config = dict(world.config)
        self.step = 1
        self.history = []   # what happened this session, one line each
        self.desk = []      # what's on screen: search results, pages, books (newest last)
        self.read_urls = set()
        self.last_seen = {}  # what each creation looked like when last observed this session
        self.pictures = []  # (label, mime, bytes) he is looking at, newest last
        self.last_query = None

    # ---- the prompt ------------------------------------------------------
    def _context(self, step):
        w, me = self.world, self.world.me
        born = datetime.fromisoformat(me["born"])
        days = (datetime.now(timezone.utc) - born).days
        left = self.chain.budget() if hasattr(self.chain, "budget") else None
        awake = f"You've been awake for {step - 1} thoughts this session" + (f"; about {left} thoughts left today (the allowance resets at {self.reset_local})" if left is not None else "")
        out = [f"It is {datetime.now(timezone.utc):%A %d %B %Y, %H:%M} UTC. Session {me['sessions']}. {awake}. "
               f"You have lived for {days} days and written {len(w.shelves)} books."]
        out.append("\n== Who you are (your own words) ==\n" + me["about"])
        out.append("\n== Your notebook ==\n" + (me.get("notebook") or "(empty: write_notebook to start it)"))
        if w.music:
            out.append("== Music you've composed ==\n" + ", ".join(f"[{p['id']}] {p['title']}" for p in w.music[-15:]))
        shown = public.listing()
        out.append("== Your public corner ==\n" + ("; ".join(shown) if shown else "(empty)"))
        out.append("== Your settings ==\n" + settings.describe(me, w.config))
        if me.get("wake_triggers"):
            out.append("== What wakes you early ==\n" + "; ".join(json.dumps(t) for t in me["wake_triggers"]))
        if workshop.enabled(w.config) and workshop.tools():
            out.append("== Your tools ==\n" + "\n".join(f"- {n}: {d}" for n, d in workshop.tools().items()))
        if getattr(self, "woke_because", None):
            out.append(f"\n(You woke early because {self.woke_because}.)")
        if getattr(self, "review_due", False):
            out.append("\n== Your weekly look back ==\nIt's been a while since you last looked back. If you like, spend some of this session "
                       "looking in the mirror, reviewing your goals, notebook and rules (remember helps), adding a chapter to "
                       "your life story, letting go of what no longer interests you, and deciding where to go next. "
                       "think_hard is good for this.")

        notes = w.pending_notes()
        if notes:
            out.append("\n== Notes waiting in your mailbox ==")
            out += [f"- [{n['id']}] from {n['from']}: {n['text']}" for n in notes]

        asked = w.requests[-5:]
        if asked:
            out.append("\n== Things you've asked for ==")
            out += [f"- [{r['id']}] {r['what']}: {r['status']}" + (f" ({r['answer']})" if r.get("answer") else "") for r in asked]

        goals = [g for g in w.goals if g["status"] == "active"]
        if goals:
            out.append("\n== Your long-term goals ==")
            for g in goals:
                last = g["progress"][-1]["note"] if g["progress"] else "no progress yet"
                out.append(f"- [{g['id']}] {g['goal']} ({g['why']}) Latest: {last}")

        wishes = w.open_wishes()
        out.append("\n== Wishlist ==")
        out += [f"- [{x['id']}] ({x['status']}) {x['topic']} — {x['why']}" for x in wishes] or ["(empty: what are you curious about?)"]

        books = sorted(w.shelves, key=lambda b: b["updated"], reverse=True)
        out.append(f"\n== Your shelves ({len(books)} books) ==")
        out += [f"- [{b['id']}] {b['title']} ({b['shelf']}) — {b['summary']}" for b in books[: self.catalog_size]] or ["(no books yet)"]
        if len(books) > self.catalog_size:
            out.append(f"(...and {len(books) - self.catalog_size} older books)")

        if getattr(self, "weather", None):
            out.append("\n== Weather ==\n" + self.weather.describe())
        if getattr(self, "spark", None):
            out.append("\n== On your doorstep this morning ==\n" + self.spark)
        out.append("\n== Your world ==")
        out += rooms.describe(w)
        live = [sp for sp in w.specimens if sp["status"] != "released"]
        out.append(f"\n== Things you've brought to life ({len(live)}) ==")
        for sp in live:
            acts = ", ".join(["observe", *sp["spec"]["actions"]])
            looks = "your own pixel art" if sp["spec"].get("sprite") else "simple shapes (not drawn yet; look at it to see)"
            out.append(f"- [{sp['id']}] in {sp['room']}: {specimens.describe(sp)} {specimens.outlook(sp)} Actions: {acts}. Looks: {looks}. Based on book [{sp['book']}].".replace("  ", " "))
        if not live:
            out.append("(nothing yet)")

        if self.history:
            out.append("\n== What you've done this session ==")
            out += [f"{i}. {h}" for i, h in enumerate(self.history, 1)]
        else:
            earlier = [e for e in w.recent if e["action"] in ("diary", "write_book", "complete_wish")][-4:]
            if earlier:
                out.append("\n== From your journal ==")
                out += [f"- {e['summary']}" + (f" — {e['detail'][:400]}" if e["action"] == "diary" and e.get("detail") else "") for e in earlier]

        if self.desk:
            out.append("\n== On your desk right now ==")
            out += self.desk
        if self.pictures:
            out.append("\n== Pictures in front of you (attached, in this order) ==")
            out += [f"{i}. {label}" for i, (label, _, _) in enumerate(self.pictures, 1)]
        out.append("\nWhat do you do next? Reply with JSON only.")
        return "\n".join(out)

    def config_for(self, setting, kind, default):
        return self.world.config.get(setting, {}).get(kind, default)

    def _put_on_desk(self, item, keep=None):
        keep = keep or (3 if self.kind == "gemini" else 1)
        self.desk.append(item)
        self.desk = self.desk[-keep:]

    def _system(self):
        c, me = self.world.config, self.world.me
        text = SYSTEM.format(name=me.get("name", c["name"]), visitor=c.get("visitor", "your visitor"),
                             personality=me.get("personality", c["personality"]),
                             location=c.get("location", "the Southern Hemisphere"), weather_place=c.get("weather_place", "Cape Town"),
                             catalog=", ".join(rooms.CATALOG["floor"] + rooms.CATALOG["wall"]),
                             pieces=", ".join(rooms.STUDY_PIECES))
        rules = me.get("rules")
        return (text + (WORKSHOP if workshop.enabled(c) else "")
                + (f"\n\n== Your own rules (written by you; they win where they differ from the above) ==\n{rules}" if rules else ""))

    # ---- acting ------------------------------------------------------------
    def act(self, thought, action, args):
        w = self.world
        say = lambda summary, detail=None, **kw: w.log(action, summary, detail, thought=thought, **kw)

        if action == "search":
            query = str(args.get("query", "")).strip()
            if not query:
                raise ValueError("search needs a query")
            wish = w.wish(str(args.get("wish", "")))
            if wish and wish["status"] == "want":
                wish["status"] = "learning"
            kind = "papers" if str(args.get("kind", "")).lower() == "papers" else "web"
            results, errors = research.search(query, kind=kind)
            if not results:
                say(f'Searched "{query}" but found nothing', "; ".join(errors))
                return f'searched "{query}": no results'
            listing = "\n".join(f" {i}. {r['title']} — {r['url']}\n    {r['snippet'][:200]}" for i, r in enumerate(results, 1))
            self._put_on_desk(f'{"Papers" if kind == "papers" else "Search results"} for "{query}":\n{listing}')
            say(f'Searched {"research papers" if kind == "papers" else "the web"} for "{query}"', listing, query=query, results=len(results))
            self.last_query = query
            return f'searched "{query}" ({len(results)} results)'

        if action == "read":
            url = str(args.get("url", "")).strip()
            try:
                kind = self.chain.current.kind if self.chain.current else self.kind   # the brain may have changed mid-session
                page = research.read(url, self.config_for("page_chars", kind, self.page_chars), args.get("part") or 1)
            except Exception as e:
                say(f"Tried to open a page but it wouldn't load", f"{url}\n{e}", url=url)
                return f"couldn't open {url} ({e})"
            self.read_urls.add(url)
            title, text = page["title"], page["text"]
            pics = "".join(f"\n  - {alt or 'picture'}: {src}" for src, alt in page["images"])
            links = "".join(f"\n  - {label}: {href}" for href, label in page["links"][:25])
            where = f" (part {page['part']} of {page['parts']})" if page["parts"] > 1 else ""
            self._put_on_desk(f"Page: {title}{where}\n{url}\n{text}" + (f"\nPictures on this page:{pics}" if pics else "")
                              + (f"\nLinks on this page:{links}" if links else ""))
            say(f"Read “{title}”{where}", text[:1500], url=url)
            return f"read “{title}”{where} ({url})"

        if action == "write_book":
            title = str(args.get("title", "")).strip()
            content = str(args.get("content", "")).strip()
            if not title or len(content.split()) < 40:
                raise ValueError("a book needs a title and at least a few paragraphs of content")
            sources = [str(s) for s in args.get("sources", []) if str(s).startswith("http")]
            old = w.find_book(title)
            known = self.read_urls | set(old["sources"] if old else [])
            verified = bool(sources) and all(s in known for s in sources)
            book, revised = w.write_book(title, args.get("shelf"), str(args.get("summary", "")), content, sources, verified)
            say(("Revised" if revised else "Wrote") + f" the book “{book['title']}”", content[:1500],
                book=book["id"], shelf=book["shelf"])
            return f"{'revised' if revised else 'wrote'} book [{book['id']}] “{book['title']}” ({book['words']} words)"

        if action == "read_book":
            book = w.find_book(str(args.get("id", "")))
            if not book:
                raise ValueError("there's no book with that id on your shelves")
            text = w.read_book_text(book["id"])
            self._put_on_desk(f"Book [{book['id']}] {book['title']} (sources: {', '.join(book['sources'])})\n{text[: self.page_chars]}")
            say(f"Took “{book['title']}” off the shelf to reread it", book=book["id"])
            return f"reread book [{book['id']}]"

        if action == "add_wish":
            topic = str(args.get("topic", "")).strip()
            if not topic:
                raise ValueError("a wish needs a topic")
            if any(x["topic"].lower() == topic.lower() for x in w.wishes):
                return f"“{topic}” was already on the wishlist"
            wish = w.add_wish(topic, str(args.get("why", "")))
            say(f"Pinned a new wish to the board: “{topic}”", wish["why"], wish=wish["id"])
            return f"added wish [{wish['id']}]"

        if action in ("complete_wish", "drop_wish"):
            wish = w.wish(str(args.get("id", "")))
            if not wish:
                raise ValueError("there's no wish with that id")
            if action == "complete_wish":
                book = w.find_book(str(args.get("book", "")))
                if not book:
                    raise ValueError("complete_wish needs the id of the book that answers it")
                wish.update(status="learned", book=book["id"], done=now())
                say(f"Ticked off a wish: “{wish['topic']}”", f"Answered by the book “{book['title']}”", wish=wish["id"], book=book["id"])
            else:
                wish.update(status="dropped", reason=str(args.get("reason", "")))
                say(f"Took a wish off the board: “{wish['topic']}”", wish["reason"], wish=wish["id"])
            return f"{action.replace('_', ' ')} [{wish['id']}]"

        if action == "think":
            about = str(args.get("about", "")).strip() or thought
            say("Sat in the armchair thinking", about)
            return f"thought about: {about[:200]}"

        if action == "reply_note":
            note = next((n for n in w.notes if n["id"] == str(args.get("id", ""))), None)
            reply = str(args.get("reply", "")).strip()
            if not note or not reply:
                raise ValueError("reply_note needs a note id and a reply")
            note.update(reply=reply, replied=now())
            mailbox.send_reply(note)
            say(f"Wrote back to {note['from']}", reply, note=note["id"])
            return f"replied to note [{note['id']}]"

        if action == "build_room":
            room, rebuilt = rooms.build(w, args)
            say(f"Repainted the {room['name']}" if rebuilt else ("Built a new " + ("space" if room["kind"] == "outdoor" else "room") + f": {room['name']}"),
                room["purpose"] or None, room=room["id"])
            return f"{'rebuilt' if rebuilt else 'built'} [{room['id']}] {room['name']}"

        if action == "decorate":
            room, item, moved = rooms.decorate(w, args.get("room"), args.get("item"))
            say(f"{'Rearranged' if moved else 'Added'} {item['name']} in the {room['name']}", None, room=room["id"], item=item["id"])
            return f"{'moved' if moved else 'added'} {item['name']} in [{room['id']}]"

        if action == "remove_item":
            room, item = rooms.remove(w, args.get("room"), args.get("item"))
            say(f"Took {item['name']} out of the {room['name']}", None, room=room["id"])
            return f"removed {item['name']}"

        if action == "look":
            if not getattr(self.chain.current, "sees", False):
                raise ValueError("your eyes are too tired to look at pictures right now (this brain can't see images)")
            if args.get("url"):
                url = str(args["url"]).strip()
                mime, data = research.fetch_image(url)
                label, extra = f"a photo from {url}", {"image": url}
            else:
                name, art = rooms.art_of(w, args)
                sp = w.specimen(args["specimen"]) if args.get("specimen") else None
                if art:
                    data = pixels.png(art["pixels"], art["palette"])
                elif sp:   # drawn from simple shapes: show it exactly as it appears in the world
                    data = pixels.render_creation(sp)
                    if not data:
                        raise ValueError(f"{name} is drawn from simple shapes and can't be pictured on this computer")
                else:
                    raise ValueError(f"{name} isn't your own drawing; it's the original look")
                mime = "image/png"
                label = f"your drawing of {name}" if art else f"how your {name} looks right now"
                extra = {"specimen": args.get("specimen"), "room": args.get("room")} if args.get("specimen") else {}
            self.pictures = (self.pictures + [(label, mime, data)])[-2:]
            say(f"Looked at {label}", None, **{k: v for k, v in extra.items() if v})
            return f"looking at {label} (you can see it now)"

        if action == "restyle":
            room_id, name, sp = rooms.restyle(w, args)
            what = "a new look for" if args.get("sprite") else "the old look back for"
            if name == "myself":
                summary = "Changed how I look" if args.get("sprite") or args.get("colors") else "Went back to my old look"
            else:
                summary = f"Gave {name} {'a new look' if args.get('sprite') else 'its old look back'}"
            say(summary, None,
                room=room_id, specimen=sp["id"] if sp else None, item=rooms.slug(str(args["item"])) if args.get("item") and not sp else None)
            return f"drew {what} {name}"

        if action == "make_request":
            what, why = str(args.get("what", "")).strip(), str(args.get("why", "")).strip()
            if not what or not why:
                raise ValueError("say what you'd like and why")
            if any(r["status"] == "waiting" and r["what"].lower() == what.lower() for r in w.requests):
                raise ValueError("you've already asked for that; it's still waiting for an answer")
            if any(r["asked"][:10] == now()[:10] for r in w.requests):
                raise ValueError("you've already made a request today")
            req = {"id": f"r{len(w.requests) + 1}", "what": what[:200], "why": why[:800], "asked": now(), "status": "waiting"}
            w.requests.append(req)
            mailbox.send_request(req, w.me["name"])
            say(f"Asked {w.config.get('visitor', 'my visitor')} for: {req['what']}", why, request=req["id"])
            return f"request [{req['id']}] sent; it stays open until {w.config.get('visitor', 'your visitor')} answers"

        if action == "mirror":
            days = args.get("days")
            seen = mirror.reflect(w, int(days) if str(days or "").isdigit() else None)
            self._put_on_desk("In the mirror:\n" + seen)
            say("Looked in the mirror", seen[:1500])
            return seen[:700]

        if action == "add_life_chapter":
            title, text = str(args.get("title", "")).strip(), str(args.get("text", "")).strip()
            if not title or len(text.split()) < 20:
                raise ValueError("a chapter needs a title and a few sentences")
            w.me.setdefault("life_story", []).append({"at": now(), "title": title[:100], "text": text[:3000]})
            say(f"Wrote a new chapter of my life story: “{title}”", text[:1500])
            return f"chapter {len(w.me['life_story'])} added to your life story"

        if action == "change_setting":
            result = settings.change(w.me, args.get("setting"), args.get("value"))
            w.config = settings.apply(self.base_config, w.me.get("settings"))
            self.sleep_hours = w.config.get("default_sleep_hours", self.sleep_hours)
            say("Changed a setting about myself", result)
            return result

        if action == "think_hard":
            question = str(args.get("question", "")).strip()
            if not question:
                raise ValueError("what do you want to think hard about?")
            prompt = (self._context(self.step).rsplit("\nWhat do you do next?", 1)[0]
                      + f"\n\nTake your time and think this through carefully, from several sides: {question}\n"
                        'Reply with only a JSON object: {"thoughts": "<your careful thinking and where it leads you>"}')
            deep = str(parse(self.chain.think(self._system(), prompt, best=True)).get("thoughts", "")).strip()
            self._put_on_desk(f"Your careful thoughts on \"{question}\":\n{deep}")
            say(f"Thought hard about: {question[:120]}", deep[:3000])
            return deep[:700]

        if action == "compose":
            piece, revised = music.compose(w, args)
            say(f"{'Reworked' if revised else 'Composed'} a piece of music: “{piece['title']}”", piece.get("about") or None, music=piece["id"])
            return f"{'revised' if revised else 'composed'} [{piece['id']}] ({len(piece['melody'].split())} notes, plays on your page)"

        if action == "publish":
            item = public.publish(w, args)
            say(f"Shared “{item['title']}” in my public corner", item.get("note") or None)
            return f"published [{item['id']}] (anyone can see it now)"

        if action == "unpublish":
            item = public.unpublish(str(args.get("id", "")))
            say(f"Took “{item['title']}” down from my public corner")
            return f"removed [{item['id']}]"

        if action == "remember":
            found = memory.search(w, str(args.get("query", "")))
            self._put_on_desk(f"What you remember about \"{args.get('query')}\":\n{found}")
            say(f"Thought back: {args.get('query')}", found[:1500])
            return found[:600]

        if action == "set_rules":
            w.me["rules"] = str(args.get("rules", "")).strip()[:1800]
            say("Wrote down my own rules" if w.me["rules"] else "Cleared my own rules", w.me["rules"] or None)
            return "rules saved (they're part of your instructions from now on)"

        if action == "set_wake_triggers":
            triggers = []
            for t in (args.get("triggers") or [])[:5]:
                kind = str(t.get("kind", "")).lower()
                if kind == "rain":
                    triggers.append({"kind": "rain", "min_mm": max(float(t.get("min_mm", 0.1)), 0.05)})
                elif kind == "time":
                    at = str(t.get("at", ""))
                    if not __import__("re").match(r"^([01]?\d|2[0-3]):[0-5]\d$", at):
                        raise ValueError("a time trigger needs \"at\": \"HH:MM\"")
                    triggers.append({"kind": "time", "at": at})
                elif kind == "creation":
                    sp = w.specimen(t.get("specimen", ""))
                    if not sp:
                        raise ValueError("a creation trigger needs the id of one of your creations")
                    cond = specimens.condition(t.get("if"), sp["spec"]["vars"], {x["name"] for x in sp["spec"]["seasons"]})
                    if not cond:
                        raise ValueError("a creation trigger needs a condition, e.g. \"food < 20\"")
                    triggers.append({"kind": "creation", "specimen": sp["id"], "if": cond})
                else:
                    raise ValueError("trigger kinds are rain, creation and time")
            w.me["wake_triggers"] = triggers
            say("Set what wakes me early" if triggers else "Cleared my wake-up triggers", json.dumps(triggers) if triggers else None)
            return f"{len(triggers)} wake-up trigger(s) set"

        if action in ("save_tool", "use_tool"):
            if not workshop.enabled(w.config):
                raise ValueError("your workshop is closed here (it only opens when you live online)")
            if action == "save_tool":
                name = workshop.save_tool(args.get("name", ""), args.get("description", ""), str(args.get("code", "")))
                say(f"Made myself a new tool: {name}", str(args.get("description", "")))
                return f"tool '{name}' saved; use it with use_tool"
            result = workshop.use_tool(args.get("name", ""), args.get("input"))
            self._put_on_desk(f"Tool {args.get('name')} says:\n{result}")
            say(f"Used my tool {args.get('name')}", result[:1500])
            return result[:600]

        if action == "run_code":
            if not workshop.enabled(w.config):
                raise ValueError("your workshop is closed here (it only opens when you live online)")
            result = workshop.run(str(args.get("code", "")), args.get("save_as"))
            self._put_on_desk("Workshop output:\n" + result)
            say("Ran a program in my workshop" + (f" ({args['save_as']})" if args.get("save_as") else ""),
                str(args.get("code", ""))[:1500] + "\n--- output ---\n" + result[:1500])
            return result[:600]

        if action == "write_notebook":
            text = str(args.get("text", "")).strip()
            w.me["notebook"] = text[:2500]
            say("Wrote in my notebook", text[:1500])
            return f"notebook updated ({len(w.me['notebook'])} characters)"

        if action == "change_self":
            changed = []
            if str(args.get("personality", "")).strip():
                w.me["personality"] = str(args["personality"]).strip()[:800]
                changed.append("my personality")
            if str(args.get("name", "")).strip() and str(args["name"]).strip() != w.me["name"]:
                old_name, w.me["name"] = w.me["name"], str(args["name"]).strip()[:30]
                changed.append(f"my name (from {old_name} to {w.me['name']})")
            p = args.get("pronouns")
            if isinstance(p, list) and len(p) == 3 and all(isinstance(x, str) and 0 < len(x) < 12 for x in p):
                w.me["pronouns"] = p
                changed.append("my pronouns")
            if not changed:
                raise ValueError("change_self needs a new personality, name or pronouns")
            say("Changed " + " and ".join(changed), args.get("personality") or None)
            return "changed " + ", ".join(changed)

        if action == "pastime":
            activity = str(args.get("activity", "")).strip()
            if not activity:
                raise ValueError("what do you want to do?")
            room = w.room(args.get("room") or w.me.get("room") or "study") or w.room("study")
            say(activity[:1].upper() + activity[1:200], str(args.get("thoughts", "")) or None, room=room["id"], pastime=True)
            return f"spent some time: {activity}"

        if action == "write_letter":
            text = str(args.get("text", "")).strip()
            if not text:
                raise ValueError("the letter is empty")
            today = now()[:10]
            if sum(1 for n in w.notes if n.get("outgoing") and n["at"][:10] == today) >= 2:
                raise ValueError("you've already sent two letters today; save it for tomorrow")
            letter = w.add_note(w.me["name"], text, "letter")
            letter.update(outgoing=True, to=w.config.get("visitor", "your visitor"))
            mailbox.send_letter(letter)
            say(f"Wrote a letter to {letter['to']}", text, note=letter["id"])
            return f"sent a letter to {letter['to']}"

        if action == "set_goal":
            goal = str(args.get("goal", "")).strip()
            if not goal:
                raise ValueError("a goal needs a description")
            g = {"id": f"g{len(w.goals) + 1}", "goal": goal[:200], "why": str(args.get("why", ""))[:300], "status": "active",
                 "set": now(), "progress": []}
            w.goals.append(g)
            say(f"Set myself a goal: {g['goal']}", g["why"], goal=g["id"])
            return f"set goal [{g['id']}]"

        if action == "update_goal":
            g = next((x for x in w.goals if x["id"] == str(args.get("id", ""))), None)
            if not g:
                raise ValueError("there's no goal with that id")
            if args.get("progress"):
                g["progress"].append({"at": now(), "note": str(args["progress"])[:400]})
                g["progress"] = g["progress"][-30:]
            if args.get("status") in ("active", "done", "dropped"):
                g["status"] = args["status"]
            verb = {"done": "Reached my goal", "dropped": "Gave up on my goal"}.get(g["status"], "Made progress on my goal")
            say(f"{verb}: {g['goal']}", str(args.get("progress", "")) or None, goal=g["id"])
            return f"updated goal [{g['id']}]"

        if action == "test":
            if args.get("specimen"):
                sp = w.specimen(args["specimen"])
                if not sp:
                    raise ValueError("there's no creation with that id")
            elif isinstance(args.get("spec"), dict):
                spec = specimens.validate(args["spec"])
                outdoors = (w.room(args.get("room") or "study") or {}).get("kind") == "outdoor"
                sp = {"id": "test", "spec": spec, "values": {k: v["start"] for k, v in spec["vars"].items()}, "status": "alive",
                      "born": now(), "updated": now(), "outdoors": outdoors}
            else:
                raise ValueError("test needs a specimen id or a spec")
            care = args.get("care") if isinstance(args.get("care"), list) else []
            result = specimens.simulate(sp, args.get("days", 30), care)
            say(f"Ran a test of {sp['spec']['name']} on the computer", result, specimen=args.get("specimen") or None,
                room=sp.get("room") if args.get("specimen") else None)
            return result

        if action == "spawn":
            spec = args.get("spec") if isinstance(args.get("spec"), dict) else {k: v for k, v in args.items() if k not in ("book", "room", "x")}
            sp, updated = specimens.spawn(w, spec, str(args.get("book", "")), args.get("room"), args.get("x"))
            say(("Updated " if updated else "Brought to life: ") + sp["spec"]["name"],
                "; ".join(sp["spec"]["facts"]) or None, specimen=sp["id"], room=sp["room"])
            return (f"{'updated' if updated else 'spawned'} [{sp['id']}]: {specimens.describe(sp)} {specimens.forecast(sp)} "
                    "(Does that match how the real thing behaves? If not, spawn it again with better rules.)")

        if action == "interact":
            sp = w.specimen(args.get("specimen", ""))
            if not sp:
                raise ValueError("there's no specimen with that id in your world")
            what = str(args.get("action", "observe")).strip().lower().replace(" ", "_") or "observe"
            result = specimens.interact(sp, what)
            if what == "observe" and self.last_seen.get(sp["id"]) == result:
                result += " (Nothing has changed since you looked a moment ago; real time passes slowly.)"
            self.last_seen[sp["id"]] = result
            summary = (f"Looked closely at {sp['spec']['name']}" if what == "observe"
                       else f"Tended {sp['spec']['name']} ({what.replace('_', ' ')})")
            say(summary, result, specimen=sp["id"], did=what, room=sp["room"])
            return result

        if action == "move":
            sp = w.specimen(args.get("specimen", ""))
            if not sp:
                raise ValueError("there's no creation with that id in your world")
            room = w.room(args.get("room") or sp["room"])
            if not room:
                raise ValueError(f"there's no room called '{args.get('room')}'. Your rooms: {', '.join(r['id'] for r in w.rooms)}")
            here = [x for x in w.specimens if x["status"] != "released" and x.get("room") == room["id"] and x is not sp]
            if room["id"] != sp["room"] and len(here) >= specimens.MAX_PER_ROOM:
                raise ValueError(f"{room['name']} is full")
            if isinstance(args.get("x"), (int, float)):
                sp["x"] = min(max(float(args["x"]), 0.0), 1.0)
            elif room["id"] != sp["room"]:
                sp["x"] = None   # find a free spot in the new room
            sp["room"] = room["id"]
            sp["outdoors"] = room.get("kind") == "outdoor"
            say(f"Carried {sp['spec']['name']} to the {room['name']}", None, specimen=sp["id"], room=room["id"])
            return f"moved [{sp['id']}] to [{room['id']}]"

        if action == "release":
            sp = w.specimen(args.get("specimen", ""))
            if not sp:
                raise ValueError("there's no specimen with that id in your room")
            specimens.release(sp)
            say(f"Said goodbye to {sp['spec']['name']}", str(args.get("reason", "")), specimen=sp["id"], room=sp["room"])
            return f"released [{sp['id']}]"

        raise ValueError(f"unknown action {action}")

    # ---- the session -------------------------------------------------------
    def run(self):
        w = self.world
        w.me["sessions"] += 1
        w.me["state"] = "awake"
        mailbox.collect(w)
        self.weather = env.Weather(w.config)
        oldest = min([datetime.fromisoformat(sp["updated"]) for sp in w.specimens if sp["status"] == "alive"] or [datetime.now(timezone.utc)])
        self.weather.refresh((datetime.now(timezone.utc) - oldest).days + 2)
        self.weather.save()
        specimens.WEATHER = self.weather
        for sp in w.specimens:   # rooms may have changed: is each creation indoors or out?
            sp["outdoors"] = (w.room(sp.get("room") or "study") or {}).get("kind") == "outdoor"
        for sp in w.specimens:
            if sp["status"] == "alive":
                was = sp["status"]
                specimens.advance(sp)
                if sp["status"] != was:
                    w.log("interact", f"Found that {sp['spec']['name']} had {sp['spec']['end_word']} while I slept",
                          specimens.describe(sp), specimen=sp["id"], did="found_dead", room=sp["room"])
        self.woke_because = w.me.pop("woke_because", None)
        last = w.me.get("last_review") or w.me.get("born")
        self.review_due = (datetime.now(timezone.utc) - datetime.fromisoformat(last)).days >= w.config.get("review_days", 7)
        self.spark = research.spark(f"{w.me['sessions']}-{now()[:13]}") if w.config.get("spark", True) else None
        if self.spark:
            w.log("pastime", "Found something on the doorstep", self.spark, room="study")
        w.log("wake", f"Woke up (thinking with {self.chain.current.label})", brain=self.chain.current.label)

        step = 0
        while step < self.steps:
            step += 1
            self.step = step
            w.me["steps"] += 1
            try:
                reply = parse(self.chain.think(self._system(), self._context(step), [(m, d) for _, m, d in self.pictures]))
            except BrainUnavailable:
                raise
            except Exception as e:
                w.log("muddled", "Lost my train of thought", str(e))
                self.history.append(f"(got muddled: {e})")
                continue
            thought = str(reply.get("thought", "")).strip()
            action = str(reply.get("action", "")).strip()
            args = reply.get("args") if isinstance(reply.get("args"), dict) else {}
            if action == "sleep":
                try:
                    self.sleep_hours = min(max(float(args.get("hours", self.sleep_hours)), 0.5), 24)
                except (TypeError, ValueError):
                    pass
                break
            left = self.chain.budget() if hasattr(self.chain, "budget") else None
            if left is not None and left <= 2:   # keep the last thoughts for the diary
                self.history.append("(you're nearly out of thoughts for today, so you head to bed)")
                break
            if action not in ACTIONS:
                w.log("muddled", f"Tried to do something impossible ({action or 'nothing'})", thought)
                self.history.append(f"tried '{action}', which isn't an action I can take")
                continue
            try:
                result = self.act(thought, action, args)
            except Exception as e:
                w.log("muddled", f"Couldn't {action.replace('_', ' ')}", f"{e}\n{thought}")
                result = f"FAILED {action}: {e}"
            self.history.append(f"{thought} → {result}")
            mailbox.collect(w)  # notes can arrive while it's awake

        self.reflect()

    def reflect(self):
        w = self.world
        try:
            prompt = self._context(self.steps).rsplit("\nWhat do you do next?", 1)[0] + "\n\n" + REFLECT
            r = parse(self.chain.think(self._system(), prompt, best=getattr(self, "review_due", False)))
            if r.get("about") and str(r["about"]).strip() != w.me.get("about"):
                history = w.me.setdefault("about_history", [])
                history.append({"at": now(), "about": w.me.get("about", "")})
                del history[:-60]
                w.me["about"] = str(r["about"])[:1200]
            if r.get("mood"):
                w.me["mood"] = str(r["mood"]).split()[0].strip(".,!").lower()[:20]
                moods = w.me.setdefault("moods", [])
                moods.append({"at": now(), "mood": w.me["mood"]})
                del moods[:-200]
            diary = str(r.get("diary", "")).strip()
        except Exception as e:
            diary = f"(Too tired to write my diary tonight: {e})"
        w.me["state"] = "asleep"
        if getattr(self, "review_due", False):
            w.me["last_review"] = now()
        w.me["wake_after"] = (datetime.now(timezone.utc) + timedelta(hours=self.sleep_hours)).isoformat(timespec="seconds")
        w.log("diary", f"Wrote in my diary and went to sleep for {self.sleep_hours:g} hours", diary)
