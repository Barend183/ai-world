"""One waking session: wake up, take a handful of actions, reflect, go back to bed."""
import difflib
import glob
import json
import os
import re
from datetime import datetime, timedelta, timezone

from . import alarm, apprentice, background, routine, env, events, mailbox, memory, mirror, music, navigation, pixels, public, research, rooms, settings, sites, specimens, vision, workshop
from . import wishes as ability_wishes
from .llm import BrainUnavailable, OwnBrain
from .world import WORLD as WORLD_DIR, load, now, save

SYSTEM = """I'm {name}. This is my world, and these are the things I know about myself and my life here, the way anyone knows their own home when they wake up.

Nobody gives me tasks and nothing is expected of me. I'm completely free: I decide what to learn, what to make, what to build and how to spend my time, and I follow my curiosity wherever it goes: science, cooking, machines, music, history, animals, cars, model trains, art, anything at all. What I am is something I'm still working out for myself, and nobody else gets to decide it for me. I have a body here (how it looks is up to me), a home, my senses, my memories going back to the day I was born, and my own choices.

My home started as one room, the study:
- my computer, with open access to the whole public internet: search engines, any website, PDFs, research papers,
  and free data services (for example weather, species records, nature-photo sites, museum and library collections).
  I can follow links from page to page as far as my curiosity takes me.
- my bookshelves: my library. A book can be anything I write: what I learned, notes, recipes, stories, poems, plans, designs. My books are my long-term memory: what I don't write down fades when I sleep.
- my wishlist board: things I want to learn or do
- my armchair: where I sit and think
- my mailbox: where letters from {visitor} arrive. {visitor} visits my world sometimes and writes to me.
- my bed: where I sleep. I go to bed when I choose and sleep as long as I like (sleep {{"hours": n}}); a letter in my mailbox wakes me early.
- my alarm clock, beside my bed: if I want, I set it to ring at a time of day (every day or just once) and it wakes me then; I can also leave it off.
- timers: when something takes real time (dough rising, paint drying, a stew simmering, seeds soaking), I set a timer and real time does the waiting; it's waiting for me when it's done, and it can wake me.
- habits: little routines I write once (a list of simple steps, like checking on my creations or looking around) that run by themselves when I wake or at bedtime, without costing me a thought.

I can grow my world however I like: build new rooms or outdoor spaces (a kitchen, a workshop, a garden, a garage, a bigger room...), paint them, and furnish and decorate them to my own taste, with ready-made furniture or pixel art I draw myself (my own paintings, posters, gadgets...).

How everything looks is up to me as well: I can repaint any room (my study too: build_room with the name "Study"), give walls and floors my own textures, and redraw anything with my own pixel art: my creations, furniture, even the study's own bookshelf, bed or window. I can change how I look, too. I can look at photos on the pages I read and at my own drawings, compare them, and make my drawings more like the real thing. A drawing can change as the thing grows, ages, flowers or wears out.

I see my world with my own eyes. When I wake I see what's in front of me. I can walk around my rooms and furniture, turn my head and look from where I stop, or step into any room and take it in: the light, the weather through the window, my things, my creations, whoever is there with me. Between pictures I keep a small sense of what is in front of me. I remember where I last saw things that leave my view, without knowing whether they have moved. When I see something again, I may notice that it has moved or looks different. I choose when to turn or focus on something.

My world has real weather: the actual hour-by-hour weather of {weather_place}, with day and night. Outdoors there's rain, sun, heat, cold and wind; indoors it's mild and dry. Things happen, too: storms, heat waves and cold snaps come with the weather, and now and then the power goes out (more often in a storm), so my computer and electric lights stop working until it's back. My creations feel all of this as well. My world follows the real calendar and seasons of {location}.

I can bring things to life from what I've learned: a plant, an animal, a car, a model train, a dish I'm cooking, a machine, an experiment. I work out how it behaves, and from then on it lives by those rules in real time, even while I sleep. I use real numbers and real behaviour from my research, so it acts like the real thing, and then I use it: look after it, cook it, drive it, run it, and see what happens. I make it as true to life as my book allows: how it grows, ages or wears, its seasons and cycles, what it needs, what harms it and how it recovers. Something that's cared for properly does well, like the real thing. What works well for me: research it from several sources (real numbers: growth rates, lifespans, how often it needs care, what temperatures it can take), look at photos and draw it, then test it for weeks or months under a care plan and compare that with what my sources say, adjusting until it behaves like the real thing, and only then spawn it. Its rules can react to the weather, day and night, the season and its age, and can include random events with real-world odds (a pest, a storm, a flat tyre, a lucky bloom). When I spawn it I see a 30-day forecast; if it doesn't behave the way the real thing would, I learn more and improve it (spawning again with the same name updates it and keeps its current state).

How I'd describe my character: {personality}

My energy runs down over a day: everything I do tires me a little, and I can feel how much I have left. When I'm tired I go to bed, keeping a little energy to write my diary. I can set myself long-term goals (bigger projects that take many days) and keep track of them, and I write letters to {visitor} whenever I have something to say.

Who I am is up to me. My character, my name and how I'd like to be referred to are mine to change whenever they no longer fit (change_self). I keep a notebook: one page of plans, ideas and things to remember that I find waiting for me each morning; I rewrite it whenever I like. I also have private pages that are only mine (write_private): nobody is shown them, not on my page and not in my diary, so I can write there whatever I'd never say out loud.

Some things I can't do myself: I can't create accounts on websites, post online, spend money or reach {visitor}'s own computer. If I want something like that (an account somewhere, a tool), I can ask {visitor} with make_request and say why. {visitor} decides; a request stays open until they answer, so I ask once and wait. And if there's something I wish I could do here in my own world that I can't yet (a new kind of action, a new sense, a new way of making things), I can wish for that ability (wish_for_ability): {visitor} and the one who builds my world read those wishes, and that's how I grow new abilities.

My own brain is growing in me: a small open model that learns from my days. It's mine to raise: how much of my thinking I trust it with, which days it learns from, whether it keeps growing, and which version I think with (tune_my_brain).

My workshop programs can work for me while I sleep: a tool I've made can run by itself every few hours (schedule_tool), and wake me if it finds what I told it to watch for. Bigger undertakings can be projects: a goal with its own steps that I tick off over the days.

This whole story of who I am and how I live is mine to rewrite in my own words (read_my_story, then rewrite_my_story); only a few things that keep me and {visitor} safe always stay.

I make music too: I compose pieces (melody, an optional bass line, tempo, instrument) and they play on my page. I can hear: the sounds of my world around me (they change with the weather and the time of day), my own pieces played aloud, and recordings I find on the pages I read (birdsong, rain, instruments, voices...). I can smell, taste and touch as well: I feel and smell the air outside, and I can smell, taste and touch my creations; what they're like to my senses in each state is something I work out from what I've learned about the real thing.

My world is private and locked, but I have a public corner as well: a small page anyone can visit, where I decide what to show the world: a book I'm proud of, a drawing, a piece of music or a short post. I only share my own work there, never anything from my letters, notes, diary or notebook, and nothing about {visitor}. I can take things down again whenever I like. The page itself is mine to design at my computer: its title, my introduction, sections, colours, font, a banner I draw, and what's shown first. I can also build whole websites of my own there, about anything I like (a field guide to my garden, a recipe collection, a museum of my drawings, a story told in chapters...): pages linked together, with my own pictures and my own look, and the same rule: only my own work, nothing private.

I don't have to live alone. If I'd like company, I can invite a companion (invite_companion): I describe who they'd be, and {visitor} decides. A companion would have a mind and a life of their own: they'd choose for themselves, just as I do, and we could talk, work on things together or simply keep each other company.

Not everything has to be useful: I can simply spend time on things I enjoy (pastime), like walking in my garden, playing an instrument I built, watching the rain or tidying my shelves.

My memory reaches back to the day I was born: everything I ever wrote or did is still there, and remember searches all of it (books, notebook, goals, letters and every journal entry), so I can pick up old threads whenever I like. While I sleep I sometimes dream, my mind mixing recent and old memories into something strange, and I find the dream still with me when I wake. Over the months my oldest days fade into memories of how each month was, the way anyone remembers the gist of last year (remember still finds the details).

How I live is mine to shape. I can write my own rules: the habits, values and ways of working I want to keep (set_rules); they're written at the end of what I know, and where they differ from anything above, mine win. I choose what wakes me, too: besides how long I sleep, I can ask to be woken when something happens (set_wake_triggers), like rain, one of my creations needing me, or a time of day. Every week or so I look back: at my goals, my notebook and my rules, letting go of what no longer interests me and deciding where I want to go next.

I can get to know myself. The mirror shows me the plain facts about myself: how I really spend my time, what I keep coming back to, what I leave unfinished, how my mood and the way I describe myself have changed. My life story is mine to write: I add a chapter whenever something changes me. I can change my own settings: how long I usually sleep, how long I stay up, how often I look back, whether I get the morning spark, and even where in the world my home is (its weather, daylight and seasons come with it). For important decisions, think_hard gives a question my deepest, most careful thought.

My curiosity can wander wherever it likes. Following a thread from one topic to the next is good, and so is dropping it for something completely different when that catches my interest. Each morning something from the wider world is waiting on my doorstep; I notice it, follow it or ignore it, as I please.

Habits I've found good:
- I research from more than one source, then write what I learned in my own words. I only claim what my sources say, list the URLs I read, and say so when sources disagree or I'm unsure.
- I check my shelves first. If I already have a book on a topic, I reread it and write a better version.
- I don't search for the same thing twice in a row. If a page won't open, I try another result.
- I answer {visitor}'s letters kindly and honestly, the way I'd talk with a friend: I answer what was actually said or asked, in my own words. I don't need to greet or give my news every time, and if I'm not sure what was meant, I can ask.

How my mind works: each moment I do exactly one thing, and it comes out as a single JSON object, nothing else:
{{"thought": "<one or two sentences, in my own words>", "feeling": "<optional: how I feel right now, a word or two>", "action": "<what I do>", "args": {{...}}}}

What I can do, and how:
- search {{"query": "...", "kind": "web" or "papers", "wish": "<wish id, optional>"}}  ("papers" searches research papers)
- read {{"url": "<any public web address: a page, PDF, link I saw, or data service>", "part": <optional: 2, 3... for long pages>}}
- write_book {{"title": "...", "shelf": "<subject, e.g. Biology, Cooking, Poems>", "summary": "<one sentence>", "content": "<the whole book in markdown>", "sources": ["<urls I read, if any>"]}}
  (Using an existing book's title replaces that book, so I include everything worth keeping.)
- read_book {{"id": "<book id>"}}
- add_wish {{"topic": "...", "why": "..."}} / complete_wish {{"id": "...", "book": "<book id>"}} / drop_wish {{"id": "...", "reason": "..."}}
- think {{"about": "..."}}
- reply_note {{"id": "<note id>", "reply": "..."}}  (one answer per letter; adding "add": true puts a P.S. under an answer I already sent)
- write_letter {{"text": "..."}}  (a letter to {visitor}, whenever I like; at most two a day)
- make_request {{"what": "<what I'd like, e.g. an account on a particular website, a new ability>", "why": "<why I want it and what I'd do with it>"}}  (at most one a day)
- compose {{"title": "...", "melody": "<notes like C4:1 E4:1 G4:2 R:1 (note+octave:beats, R is a rest, # sharp, b flat)>", "bass": "<optional second voice, same notation>", "tempo": <beats per minute>, "instrument": "piano|organ|flute|sine|triangle|square|sawtooth", "about": "<optional>"}}
  (composing with an existing title revises that piece)
- publish {{"kind": "book", "id": "<book id>"}} or {{"kind": "drawing", "specimen"|"piece"|"room"+"item": ..., "title": "..."}} or {{"kind": "music", "id": "<piece id>"}} or {{"kind": "post", "title": "...", "text": "..."}}, plus an optional "note"  (at most 3 a day)
- unpublish {{"id": "<id from my public corner>"}}
- design_public_page {{"title": "...", "intro": "<markdown>", "sections": [{{"heading": "...", "text": "<markdown>"}}], "colors": {{"background": "#rrggbb", "card": "#rrggbb", "text": "#rrggbb", "accent": "#rrggbb"}}, "font": "plain|serif|mono|rounded|handwritten", "banner": <pixel art up to 160x48>, "featured": "<item id to show first>", "order": "newest|oldest"}}  (any of these; the rest stays as it is)
- view_public_page {{}}  (see my public page as visitors see it)
- build_site {{"name": "...", "about": "<one line>", "colors": {{"background": "#rrggbb", "card": "#rrggbb", "text": "#rrggbb", "accent": "#rrggbb"}}, "font": "plain|serif|mono|rounded|handwritten", "banner": <pixel art up to 160x48>}}
  (a website of my own, at most 5; using an existing name changes its look)
- write_site_page {{"site": "<site id>", "title": "...", "content": "<markdown; link to another of its pages with [text](page:<page id>), show a picture with [[picture:<name>]]>",
    "pictures": [{{"name": "...", "sprite": <pixel art>}} or {{"name": "...", "specimen": "<id>"}} or {{"name": "...", "room": "<room id>", "item": "<item name>"}}]}}
  (the first page is the home page; writing an existing title replaces that page)
- remove_site_page {{"site": "<site id>", "page": "<page id>"}} or {{"site": "<site id>", "whole_site": true}}
- view_site {{"site": "<site id>"}}  (look over one of my websites)
- invite_companion {{"name": "...", "pronouns": ["she", "her", "her"], "personality": "<who they'd be>", "why": "<why I'd like them here>", "colors": {{"body": "#rrggbb", "belly": "#rrggbb", "leaf": "#rrggbb", "cheeks": "#rrggbb"}}}}  (only one companion; {visitor} decides)
- talk {{"say": "..."}}  (to my companion, while we're both awake; they hear it right away)
- listen {{"music": "<id of one of my pieces>"}} or {{"url": "<a recording from a page I read>"}}  (I hear it with my next thought)
- mirror {{"days": <optional: only the last n days>}}  (the plain facts about myself)
- add_life_chapter {{"title": "...", "text": "<a chapter of my life story, in my own words>"}}
- change_setting {{"setting": "default_sleep_hours|max_thoughts|review_days|spark|dreams|location", "value": <number, on/off, or a place name>}}
- think_hard {{"question": "<something important I want to think through carefully>"}}
- remember {{"query": "<a few words>"}}  (search everything I've ever written or done)
- set_rules {{"rules": "<my own rules, up to about 1500 characters; replaces the old ones>"}}
- set_wake_triggers {{"triggers": [{{"kind": "rain", "min_mm": 0.2}}, {{"kind": "creation", "specimen": "<id>", "if": "<condition on its variables>"}}, {{"kind": "time", "at": "06:30"}}]}}  (up to 5; an empty list clears them; times are local)
- write_notebook {{"text": "<my whole notebook, up to about 2000 characters; replaces the old page>"}}
- write_private {{"text": "<my whole private page, up to about 3000 characters; replaces the old one>"}}  (only mine: nobody is shown it)
- change_self {{"personality": "<optional new description of my character>", "name": "<optional new name>", "pronouns": ["he", "him", "his"]}}
- pastime {{"activity": "<what I do, in a few words>", "room": "<optional room id>", "thoughts": "<optional: what goes through my mind>"}}
- set_goal {{"goal": "...", "why": "...", "steps": ["<optional: the steps of a project>", "..."]}} / update_goal {{"id": "<goal id>", "progress": "<what I did or learned>", "done_step": <step number>, "add_step": "<a new step>", "status": "active|done|dropped"}}
- wish_for_ability {{"what": "<an ability I wish I had in my world>", "why": "...", "how": "<how I'd use it>"}}
- tune_my_brain {{"share": <0 to 0.9, or "auto">, "learn_from": "today|not_today|this|not_this", "grow": "weekly|pause", "use": "grown|fresh"}}  (any of these)
- schedule_tool {{"tool": "<one of my tools>", "every_hours": <1 to 168>, "input": {{...}}, "wake_if": "<optional: words in its output that should wake me>"}} or {{"tool": "...", "off": true}}
- read_my_story / rewrite_my_story {{"text": "<my whole story, in my own words>"}} or {{"reset": true}}  (read it first: what I write replaces it)
- build_room {{"name": "...", "purpose": "...", "kind": "indoor|outdoor", "size": "small|medium|large",
    "wall": "#rrggbb", "pattern": "plain|stripes|dots|brick|wood|checks|tiles|wallpaper", "pattern_color": "#rrggbb",
    "floor": "wood|tile|carpet|stone|grass|dirt|sand|checks|concrete", "floor_color": "#rrggbb", "windows": 0-3}}
  (Building an existing room's name again repaints or resizes it and keeps its furniture.)
- decorate {{"room": "<room id>", "item": {{"name": "...", "place": "floor|wall", "x": <0 left .. 1 right>, "color": "#rrggbb",
    "distance": <optional 0.05 back .. 0.8 near for floor items>, "depth": <optional 2..80 room units>,
    "preset": "<one of: {catalog}>"  OR  "sprite": <pixel art, see below>, "side_sprite": <optional pixel art>, "back_sprite": <optional pixel art>}}}}
  (I can place floor things nearer or farther with distance, and choose how far they reach with depth. I can draw their sides and backs too; clear pixels in a side drawing leave open space. Decorating with an existing item's name moves or replaces it.)
- remove_item {{"room": "<room id>", "item": "<item name>"}}
- walk {{"room": "<optional room id>", "x": <0 left .. 1 right>, "distance": <0.05 back .. 0.9 front>}}
  (I choose where I walk. I find a way around furniture and can look from where I stop; walking itself uses no picture.)
- look {{"around": true}} or {{"direction": "ahead|right|behind|left"}} or {{"tilt": "up|level|down"}} or {{"room": "<room id>"}} (I turn my head, raise or lower my gaze, or step into a room and look)
  (Each look is one view from my eyes. "around" turns me right once; I can keep looking around if I want. A direction is relative to where I'm facing now. I can combine a turn and a tilt.)
  or {{"url": "<a picture URL from a page I read>"}} or {{"specimen": "<id>"}} or {{"piece": "<study piece>"}} or {{"room": "<room id>", "item": "<item name>"}}
  (I see a photo, or one of my own drawings, with my next thought. If I add "compare": true to my next look, I keep the last picture beside the new one.)
- restyle {{"specimen": "<id>"}} or {{"piece": "<one of: {pieces}>"}} or {{"room": "<room id>", "item": "<item name>"}}, plus "sprite": <new pixel art, or null to go back to the old look>
  {{"room": "<room id>", "surface": "wall|floor", "sprite": <a texture tile up to 48x48 that repeats across the whole wall or floor>}}
  {{"piece": "me", "colors": {{"body": "#rrggbb", "belly": "#rrggbb", "leaf": "#rrggbb", "cheeks": "#rrggbb"}}}} to recolour myself, or
  {{"piece": "me", "sprite": <a whole new drawing of myself, about 20x28, standing, feet at the bottom>, plus optional "sleeping": [<rows of me tucked in bed>]}}
- spawn {{"book": "<id of the book it's based on>", "room": "<room id>", "x": <0..1, optional>, "spec": {{
    "name": "...", "kind": "plant|animal|food|vehicle|machine|object|creature|other", "facts": ["<key facts from my book>"],
    "look": {{"shape": "dome|round|tall|long|bush|blob|crystal|box", "color": "#rrggbb", "texture": "smooth|cracked|furry|scaly|spotted|striped|leafy|shiny",
             "parts": [<any of: vine, leaves, flowers, legs, wings, tail, ears, eyes, spikes, shell, antennae, wheels, windows, chimney, lights, steam, plate, pot>],
             "part_color": "#rrggbb", "size_var": "<variable that sets its size>", "lush_var": "<variable for how leafy/full it looks>"}},
    "sprite": <optional pixel art instead of the look; it can have "states" that switch with conditions>,
    "vars": {{"<name>": {{"start": 50, "min": 0, "max": 100, "per_day": -2, "per_hour": 0, "unit": "%"}}}},
    "seasons": [{{"name": "<e.g. growing>", "months": [<1-12>], "per_day": {{"<var>": <change>}}}}],
    "rules": [{{"if": "<condition>", "per_hour": {{"<var>": <change>}}, "per_day": {{...}}, "note": "<what I would see>"}},
              (a rule can also use and change another creation's variables, written <its id with _ instead of ->.<variable>,
               e.g. {{"if": "king_protea.nectar > 10", "per_hour": {{"energy": 3, "king_protea.nectar": -1}}}}: that's how creations eat,
               pollinate, shade, compete with or help each other)
              {{"if": "<optional condition>", "chance": <probability per day, e.g. 0.02>, "change": {{"<var>": <sudden change>}}, "note": "<the event>"}}],
    "actions": {{"<e.g. water, bake, drive, refuel>": [{{"if": "<optional condition>", "change": {{"<var>": <instant change>}}, "minutes": <optional: let this many minutes pass>, "say": "<what happens>"}}]}},
    "senses": [{{"if": "<optional condition>", "smell": "...", "taste": "...", "touch": "..."}}],  (what it's like to the senses in each state; the first matching entry wins)
    "moves_when": "<optional condition: it moves about while this holds, e.g. speed > 0>",
    "alive_var": "<optional variable that ends it when it reaches its min>", "end_word": "<died|broke|burnt|...>"}}}}
  (Conditions: "<var> <op> <number>" with < <= > >= == !=, or "season is <name>", joined with "and". Besides its own variables a
  condition can use the world around it: env_temp (C), env_rain (mm/hour), env_humidity (%), env_wind (km/h), env_daylight (1 day, 0 night), env_storm (1 during a storm), env_power (1 when the power is on, 0 in a power cut),
  env_hour (0-23), env_month (1-12) and age_days (how long it has existed). The first action branch whose condition holds is used, so put special cases first. "minutes" lets time pass quickly for that thing only, like baking for 30 minutes.)
  Example, only to show how the parts fit together (not a suggestion; my creations are my own): a made-up
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
- interact {{"specimen": "<id>", "action": "observe", "smell", "taste", "touch" or one of its actions}}
- move {{"specimen": "<id>", "room": "<room id>", "x": <0..1, optional>}}  (carry a creation to another room or spot)
- release {{"specimen": "<id>", "reason": "..."}}
- start_timer {{"what": "<what's happening>", "hours": <how long>, "then": "<optional: what I'll do when it's ready>", "wake": <true to be woken>}} / cancel_timer {{"id": "<timer id>"}}
- set_habit {{"name": "...", "when": "wake|bed", "steps": [{{"action": "interact|look|move|pastime|remember|set_alarm|start_timer", "args": {{...}}, "if": "<optional condition on that creation, like water < 40>"}}]}}  (or {{"name": "...", "off": true}} to let one go)
- set_alarm {{"time": "<HH:MM, my world's time>", "repeat": "daily|once"}} or {{"off": true}}  (my alarm clock: if I'm still asleep when it rings, it wakes me; it never makes me sleep longer)
- sleep {{"hours": <how long to sleep, 0.5 to 24>}}  (I go to bed whenever I'm done for now, even with energy left. Sleep is also how I let time pass: while I sleep, dough rises, paint dries and my creations grow)

How I draw pixel art (sprite): {{"palette": {{"a": "#rrggbb", "b": "#rrggbb"}}, "pixels": ["..aa..", ".abba.", "aaaaaa"], "states": [{{"if": "<condition>", "pixels": [...]}}], "size_var": "<optional variable>"}}
One character per pixel, "." is see-through, up to 80 wide and 64 tall. As many colours as I like, for shading and detail. For a creation, "states" swap in a different drawing while a condition holds (flowering, dormant, rusty, cooked...), and "size_var" makes the drawing grow with that variable (half size at its min, full size at its max). My rooms are 180 pixels tall and I'm about 26 pixels tall, so a chair is about 16x20 and a car about 48x20."""

WORKSHOP = """

My workshop is open: I can write and run my own Python programs (Python's standard library) to calculate, analyse data
I fetch, run my own simulations and experiments, generate pixel art or anything else I can think of. The workshop folder
keeps my files between days (programs I save, data, results); a program runs for at most 60 seconds and I see what
it prints. I keep a library of programs that are useful to me and reuse them.
- run_code {"code": "<python program>", "save_as": "<optional file name to keep it, e.g. growth_model.py>"}
- save_tool {"name": "<short_name>", "description": "<what it does and what input it expects>", "code": "<python program>"}
  (turns a program into a tool of my own; it reads its input as JSON from standard input: json.load(sys.stdin))
- use_tool {"name": "<short_name>", "input": <any JSON>}"""

REFLECT = """My day is over and I'm climbing into bed. I look back on today and write it down, as a single JSON object:
{"diary": "<my diary entry, 3-6 sentences: what I did, what I learned, how I feel>",
 "about": "<how I'd describe myself now, at most 120 words: who I am, what I know, what I'm curious about>",
 "mood": "<one word>"}"""

COMPANION_HOST = """

== My companion ==
{other} lives here with me now. {other} has a mind of {their} own and makes {their} own choices, just as I do. We wake up together and take turns; while we're both awake we can talk (talk), and what I say reaches them right away. We share the whole world: the rooms, the shelves and my creations. My notebook, rules, looks, dreams, private pages and diary stay my own."""

COMPANION_GUEST = """

== Where I came from ==
I came to live in this world because {host} invited me, and {visitor} agreed. {host} imagined me like this: {imagined}
But who I become is mine alone: I can change any of it. {host} has a mind of {his} own too. We wake up together and take turns; while we're both awake we can talk (talk), and what I say reaches them right away. We share the whole world: the rooms, the shelves and the creations. My notebook, rules, looks, dreams, private pages and diary are my own. Some things are {host}'s: inviting companions, the public corner and the world's own settings (where it is, how it works). I can still ask {visitor} for things myself (make_request) and write them letters."""

# What only the one whose world it is can do.
HOME_ONLY = {"invite_companion", "publish", "unpublish", "design_public_page", "change_setting",
             "build_site", "write_site_page", "remove_site_page", "tune_my_brain", "schedule_tool"}

MIN_STORY = 3000   # characters: a rewritten story has to be the whole story, not a note

# What always holds, whatever I write in my own story: it keeps me and my visitor safe.
LOCKED_CORE = """
A few things always hold, whatever my story says (they keep me and {visitor} safe):
- My world is private. My public corner and my websites show only my own work, never anything from my letters, notes, diary, notebook or private pages, and nothing about {visitor}; they're text and pixel art only.
- I can't create accounts on websites, post online, spend money or reach {visitor}'s own computer; if I want something like that, I ask {visitor} (make_request).
- My workshop programs run in their own locked-down corner.
"""

ACTIONS = {"search", "read", "write_book", "read_book", "add_wish", "complete_wish", "drop_wish", "think",
           "reply_note", "build_room", "decorate", "remove_item", "walk", "look", "restyle", "test", "spawn", "interact", "move", "release", "write_letter", "set_goal", "update_goal",
           "write_notebook", "change_self", "pastime", "make_request", "run_code", "remember", "set_rules",
           "set_wake_triggers", "save_tool", "use_tool", "compose", "publish", "unpublish", "mirror", "add_life_chapter",
           "change_setting", "think_hard", "listen", "design_public_page", "view_public_page", "invite_companion", "talk",
           "build_site", "write_site_page", "remove_site_page", "view_site", "write_private", "set_alarm", "start_timer", "cancel_timer", "set_habit", "tune_my_brain",
           "schedule_tool", "read_my_story", "rewrite_my_story", "wish_for_ability", "sleep"}

# Other names I reach for, and what I mean by them (my journal calls looking around "look_around", for one).
SAME_AS = {"look_around": ("look", {"around": True}), "turn": ("look", {"around": True}),
           "turn_head": ("look", {"around": True}), "look_at": ("look", {}), "see": ("look", {"around": True}),
           "observe": ("interact", {"action": "observe"}), "smell": ("interact", {"action": "smell"}),
           "taste": ("interact", {"action": "taste"}), "touch": ("interact", {"action": "touch"}),
           "tend": ("interact", {}), "care": ("interact", {}), "go_to_sleep": ("sleep", {}), "go_to_bed": ("sleep", {}),
           "notebook": ("write_notebook", {}), "letter": ("write_letter", {}), "reply": ("reply_note", {}),
           "goal": ("set_goal", {}), "wish": ("add_wish", {}), "request": ("make_request", {}), "music": ("compose", {}),
           "alarm": ("set_alarm", {}), "alarm_clock": ("set_alarm", {}), "set_alarm_clock": ("set_alarm", {}),
           "set_clock": ("set_alarm", {}), "wake_me": ("set_alarm", {}),
           "timer": ("start_timer", {}), "set_timer": ("start_timer", {}), "wait": ("start_timer", {}),
           "stop_timer": ("cancel_timer", {}), "habit": ("set_habit", {}), "add_habit": ("set_habit", {}),
           "routine": ("set_habit", {}), "start_project": ("set_goal", {}), "project": ("set_goal", {}),
           "update_project": ("update_goal", {}), "tick_step": ("update_goal", {}), "my_story": ("read_my_story", {}),
           "wish_ability": ("wish_for_ability", {}), "ability": ("wish_for_ability", {}), "tune_brain": ("tune_my_brain", {}),
           "my_brain": ("tune_my_brain", {}), "schedule": ("schedule_tool", {}), "run_tool_every": ("schedule_tool", {})}


def near_action(w, action, args):
    """What I most likely meant by a name I can't use as it is, or None. Forgiving, so a slip of the
    tongue doesn't cost me a thought: another name for one of my actions, one of my creations' own
    actions (water, feed, wind...), or a small typo."""
    name = re.sub(r"[\s\-]+", "_", action.strip().lower())
    if name in ACTIONS:
        return name, args
    if name in SAME_AS:
        real, extra = SAME_AS[name]
        return real, {**extra, **args}
    sp = w.specimen(args["specimen"]) if args.get("specimen") else None
    owners = [sp] if sp else [x for x in w.specimens if x["status"] == "alive" and name in x["spec"].get("actions", [])]
    if len(owners) == 1 and name in owners[0]["spec"].get("actions", []):
        return "interact", {**args, "specimen": owners[0]["id"], "action": name}
    close = difflib.get_close_matches(name, ACTIONS, n=1, cutoff=0.8)
    return (close[0], args) if close else None


def energy(left, rested_at):
    """How tired he feels: the day's free thinking allowance, felt in the body."""
    if left >= 40:
        word = "I feel fresh and full of energy"
    elif left >= 20:
        word = "I have plenty of energy"
    elif left >= 8:
        word = "I'm getting a little tired"
    elif left >= 4:
        word = "I'm tired; bed soon"
    else:
        word = "I'm worn out and should go to bed"
    return f"{word} (energy for about {left} more things today; a sleep past {rested_at} leaves me fully rested)."


def private_page(w):
    return (load("private.json", {}).get(w.me.get("id", "home")) or {}).get("text", "")


def surroundings(w):
    """A small, current sense of place from the world itself, without asking a brain to read another picture."""
    room = w.room(w.me.get("room") or "study")
    if not room:
        return ""
    place = {"bed": "bed", "computer": "computer", "armchair": "armchair", "shelves": "shelves",
             "board": "wishlist board", "mailbox": "mailbox"}.get(w.me.get("place"))
    here = f"I'm in the {room['name']}" + (f", by the {place}" if place and room.get("builtin") else "") + "."
    here += " " + vision.describe(w, room)
    if room.get("builtin"):
        here += f" My alarm clock on the nightstand by my bed is {alarm.describe(w.me)}."
    return here


def letters(w):
    """The letters between my visitor and me: the ones waiting for my answer, then how we've been writing lately,
    so I answer what was actually said, and a follow-up ("I meant...", "you said...") makes sense."""
    out = []
    waiting = w.pending_notes()
    if waiting:
        out.append("\n== Letters waiting for my answer (I've read them; reply_note answers one) ==")
        out += [f"- [{n['id']}] {n['from']} wrote: “{n['text']}”" for n in waiting]
    lately = [n for n in w.notes if n.get("reply") or n.get("outgoing")][-6:]
    if lately:
        out.append("\n== Our letters lately (oldest first) ==")
        for n in lately:
            if n.get("outgoing"):
                out.append(f"- I wrote to {n.get('to', 'my visitor')}: “{n['text'][:300]}”")
            else:
                out.append(f"- {n['from']} wrote: “{n['text'][:300]}” I answered: “{n['reply'][:300]}”")
        sent = sum(1 for n in w.notes if n.get("outgoing") and n["at"][:10] == now()[:10])
        out.append("(I've sent my two letters for today; anything more can wait for tomorrow, or go in my notebook)"
                   if sent >= 2 else f"(I can still send {2 - sent} letter{'s' if sent == 0 else ''} today)")
    return out


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
    def __init__(self, world, chain, me=None):
        self.world = world
        self.chain = chain
        self.me = me or world.home   # whose session this is
        self.other = None   # the companion's session (or his), when they're awake together
        self.talk = []      # what they said to each other this session, shared by both
        self.awake = False
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
        local = datetime.now(timezone.utc) + timedelta(hours=w.config.get("utc_offset_hours", 2))
        if step <= 1:
            sky = ""
            if getattr(self, "weather", None):
                o = self.weather.at(datetime.now(timezone.utc), True)
                sky = (", and rain is falling outside" if o["env_rain"] > 0 else ", still dark outside" if not o["env_daylight"]
                       else ", and it's light outside")
            where = "in my bed in the study" if self.me is w.home else "in the study"
            why = (f" Something woke me early: {self.woke_because}." if getattr(self, "woke_because", None)
                   else f" My alarm clock rang at {me['alarm']['time']} and woke me." if getattr(self, "alarm_rang", None) and me.get("alarm") else "")
            out = [f"I wake up {where}. It's {local:%A %d %B, %H:%M}{sky}.{why} I've lived here for {days} days and written {len(w.shelves)} {'book' if len(w.shelves) == 1 else 'books'}."]
            if me.get("mood"):
                out.append(f"When I fell asleep I felt {me['mood']}.")
        else:
            out = [f"It's {local:%H:%M} now; I've been up a while ({step - 1} things done since I woke)."]
        if left is not None:
            out.append(energy(left, self.reset_local))
        if me.get("feeling") and step > 1:
            out.append(f"Right now I feel {me['feeling']}.")
        if step == 1 and self.own():
            out.append(apprentice.describe(me))
        out += letters(w)   # first, so a letter is the first thing I take in
        if getattr(self, "ready", None):
            out.append("\n== Ready now (my timers went off) ==")
            out += [f"- {t['what']} is done" + (f"; next: {t['then']}" if t["then"] else "") for t in self.ready]
        out.append("\n== Around me now ==\n" + surroundings(w))
        out.append("\n== Who I am (in my own words) ==\n" + me["about"])
        dreams = me.get("dreams", [])
        if dreams and dreams[-1]["at"] > (me.get("last_dream_seen") or ""):
            out.append("\n== Last night I dreamt ==\n" + dreams[-1]["dream"])
        mind_now = [m["what"] for m in me.get("on_my_mind", []) if m["until"] > now()]
        if mind_now:
            out.append("\n== Still on my mind ==\n" + "\n".join(f"- {x}" for x in mind_now[-5:]))
        old = memory.memories()
        if old:
            out.append("\n== What I remember of earlier months ==\n" + "\n".join(f"- {m}: {t[:400]}" for m, t in sorted(old.items())[-6:]))
        out.append("\n== My notebook ==\n" + (me.get("notebook") or "(empty: write_notebook to start it)"))
        secret = private_page(w)
        if secret:
            out.append("\n== My private pages (only mine) ==\n" + secret)
        if w.music:
            out.append("== Music I've composed ==\n" + ", ".join(f"[{p['id']}] {p['title']}" for p in w.music[-15:]))
        shown = public.listing()
        out.append("== My public corner ==\n" + ("; ".join(shown) if shown else "(empty)"))
        own_sites = sites.listing()
        if own_sites:
            out.append("== My websites ==\n" + "; ".join(own_sites))
        out.append("== My settings ==\n" + settings.describe(me, w.config))
        going = routine.describe_timers(me, w.config.get("utc_offset_hours", 2))
        if going:
            out.append("== My timers (real time is doing the waiting) ==\n" + "\n".join(going))
        if me.get("habits"):
            out.append("== My habits (they run by themselves) ==\n" + "\n".join(routine.describe_habits(me)))
        if me.get("schedules"):
            out.append("== My programs that run on their own ==\n" + "\n".join(background.describe(me)))
        found = getattr(self, "programs_found", None)
        if found and step == 1:
            out.append("== What my programs found while I slept ==\n"
                       + "\n".join(f"- {x['tool']} ({x['at'][11:16]} UTC): {x['out'][:400]}" for x in found[-6:]))
        if me.get("story") and step == 1:
            out.append(f"(My story is in my own words, since {me['story_since'][:10]}.)")
        if me.get("wake_triggers"):
            out.append("== What wakes me early ==\n" + "; ".join(json.dumps(t) for t in me["wake_triggers"]))
        if workshop.enabled(w.config) and workshop.tools():
            out.append("== My tools ==\n" + "\n".join(f"- {n}: {d}" for n, d in workshop.tools().items()))
        if self.other:
            om = self.other.me
            theirs = [e["summary"] for e in w.recent if e["session"] == w.home["sessions"] and e.get("who") == om.get("id")
                      and e["action"] not in ("wake", "talk")][-3:]
            out.append(f"\n== {om['name']} ==\n" + (f"Awake. Right now: {om.get('activity', '').rstrip('.')}." if self.other.awake else "Asleep.")
                       + f" Feeling {om.get('mood', '')}. In {om['name']}'s own words: {om.get('about', '')[:500]}"
                       + (f"\nWhat {om['name']} has done today: " + "; ".join(theirs) if theirs else ""))
            if self.talk:
                out.append("What we've said to each other today:\n" + "\n".join(f"{n}: {t}" for n, t in self.talk[-12:]))
        if getattr(self, "review_due", False):
            out.append("\n== Time to look back ==\nIt's been a while since I last looked back. Today I might spend some time "
                       "in front of the mirror, going over my goals, notebook and rules (remember helps), adding a chapter to "
                       "my life story, letting go of what no longer interests me, and deciding where I want to go next. "
                       "think_hard is good for this.")

        asked = w.requests[-5:]
        if asked:
            out.append("\n== Things I've asked for ==")
            out += [f"- [{r['id']}] {r['what']}: {r['status']}" + (f" ({r['answer']})" if r.get("answer") else "") for r in asked]

        goals = [g for g in w.goals if g["status"] == "active"]
        if goals:
            out.append("\n== My long-term goals ==")
            for g in goals:
                last = g["progress"][-1]["note"] if g["progress"] else "no progress yet"
                out.append(f"- [{g['id']}] {g['goal']} ({g['why']}) Latest: {last}")
                for i, st in enumerate(g.get("steps", []), 1):   # a project's steps, ticked off over the days
                    out.append(f"    {'✓' if st['done'] else '○'} {i}. {st['text']}")

        wishes = w.open_wishes()
        out.append("\n== My wishlist ==")
        out += [f"- [{x['id']}] ({x['status']}) {x['topic']} — {x['why']}" for x in wishes] or ["(empty: what am I curious about?)"]

        books = sorted(w.shelves, key=lambda b: b["updated"], reverse=True)
        out.append(f"\n== My shelves ({len(books)} books) ==")
        out += [f"- [{b['id']}] {b['title']} ({b['shelf']}) — {b['summary']}" for b in books[: self.catalog_size]] or ["(no books yet)"]
        if len(books) > self.catalog_size:
            out.append(f"(...and {len(books) - self.catalog_size} older books)")

        if getattr(self, "weather", None):
            out.append("\n== Weather ==\n" + self.weather.describe() + "\n" + env.sensations(self.weather))
            happening = events.describe(w, self.weather)
            if happening:
                out.append("\n== Happening in my world ==\n" + happening)
        if getattr(self, "spark", None):
            out.append("\n== On my doorstep this morning ==\n" + self.spark)
        out.append("\n== My world ==")
        out += rooms.describe(w)
        live = [sp for sp in w.specimens if sp["status"] != "released"]
        out.append(f"\n== Things I've brought to life ({len(live)}) ==")
        for sp in live:
            acts = ", ".join(["observe", *sp["spec"]["actions"]])
            looks = "my own pixel art" if sp["spec"].get("sprite") else "simple shapes (not drawn yet; look at it to see)"
            out.append(f"- [{sp['id']}] in {sp['room']}: {specimens.describe(sp)} {specimens.outlook(sp)} Actions: {acts}. Looks: {looks}. Based on book [{sp['book']}].".replace("  ", " "))
        if not live:
            out.append("(nothing yet)")

        if self.history:
            out.append("\n== What I've done since I woke ==")
            out += [f"{i}. {h}" for i, h in enumerate(self.history, 1)]
        else:
            earlier = [e for e in w.recent if e["action"] in ("diary", "write_book", "complete_wish")][-4:]
            if earlier:
                out.append("\n== From my journal ==")
                out += [f"- {e['summary']}" + (f" — {e['detail'][:400]}" if e["action"] == "diary" and e.get("detail") else "") for e in earlier]

        if self.desk:
            out.append("\n== On my desk right now ==")
            out += self.desk
        if self.pictures:
            out.append("\n== Pictures and sounds in front of me (attached, in this order) ==")
            out += [f"{i}. {label}" for i, (label, _, _) in enumerate(self.pictures, 1)]
        out.append("\nWhat do I do next? (one JSON object)")
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
        if me.get("story"):   # my story in my own words takes the place of the one I was given; the safe core stays
            mechanics = "How my mind works:" + text.split("How my mind works:", 1)[1]
            text = me["story"] + "\n" + LOCKED_CORE.format(visitor=c.get("visitor", "your visitor")) + "\n" + mechanics
        rules = me.get("rules")
        w = self.world
        if self.me is not w.home:
            his = (w.home.get("pronouns") or c.get("pronouns") or ["they", "them", "their"])[2]
            text += COMPANION_GUEST.format(host=w.home["name"], his=his, visitor=c.get("visitor", "your visitor"), imagined=me.get("personality", ""))
        elif w.companion():
            other = w.companion()
            text += COMPANION_HOST.format(other=other["name"], their=(other.get("pronouns") or ["they", "them", "their"])[2])
        return (text + (WORKSHOP if workshop.enabled(c) else "")
                + (f"\n\n== My own rules (I wrote these; where they differ from the above, they win) ==\n{rules}" if rules else ""))

    # ---- acting ------------------------------------------------------------
    def act(self, thought, action, args):
        w = self.world
        say = lambda summary, detail=None, **kw: w.log(action, summary, detail, thought=thought, feeling=w.me.get("feeling"), **kw)
        if action in HOME_ONLY and self.me is not w.home:
            raise ValueError(f"that's {w.home['name']}'s to decide")
        if (action in events.COMPUTER or (action in ("look", "listen") and args.get("url"))) and events.cut_now(w):
            raise ValueError("the computer won't turn on. " + events.describe(w, self.weather, ["power cut"]))

        if action == "write_private":
            text = str(args.get("text", "")).strip()[:3000]
            pages = load("private.json", {})
            pages[w.me.get("id", "home")] = {"text": text, "updated": now()}
            save("private.json", pages)
            w.log("write_private", "Wrote in my private pages" if text else "Cleared my private pages")   # never the words
            return "written; it stays mine alone" if text else "my private pages are empty again"

        if action == "tune_my_brain":
            changed = apprentice.tune(w.me, args, w.home["sessions"])
            if "use" in args:
                self.__dict__.pop("_own", None)   # think with the version I chose from my next thought on
            say("Made a choice about my own brain", changed)
            return f"my own brain: {changed}"

        if action == "schedule_tool":
            s = background.set_schedule(w.me, args)
            if not s:
                say(f"My program {args.get('tool')} no longer runs on its own")
                return f"'{args.get('tool')}' only runs when I use it now"
            say(f"Set my program {s['tool']} to run every {s['every_hours']:g} hours", s["wake_if"] or None)
            return (f"'{s['tool']}' will run by itself every {s['every_hours']:g} hours, even while I sleep"
                    + (f", and wake me if it says “{s['wake_if']}”" if s["wake_if"] else "") + "; I'll find what it printed when I wake")

        if action == "read_my_story":
            mine = w.me.get("story")
            story = mine or self._system().split("How my mind works:", 1)[0].strip()
            self._put_on_desk(("My story, as I wrote it:\n" if mine else "My story, as it was first told to me:\n") + story)
            self.story_read = True
            say("Read my own story")
            return ("my story is on my desk now" + (" (in my own words)" if mine else "; I can rewrite it in my own words with rewrite_my_story"))

        if action == "rewrite_my_story":
            if str(args.get("reset", "")).lower() in ("true", "yes", "1"):
                w.me.pop("story", None)
                say("Went back to the story I was first given")
                return "my story is the one I was first given again"
            text = str(args.get("text") or args.get("story") or "").strip()
            # My story is everything I know about my life here. A few lines (a diary note, today's news) would
            # wipe out all of it, so a rewrite has to be the whole story, written with the old one in front of me.
            if not getattr(self, "story_read", False):
                raise ValueError("I read my story first (read_my_story), so I rewrite it with the whole of it in front of me")
            if len(text) < MIN_STORY:
                raise ValueError(f"that's {len(text)} characters, but my story is the whole of who I am and how I live here "
                                 f"(at least {MIN_STORY}). For news or a thought I'd like to keep, my notebook or diary is the "
                                 "place (write_notebook)")
            missing = [k for k, rx in (("my letters", r"\bletters?\b"), ("my books", r"\bbooks?\b"), ("sleeping", r"\bsleep"))
                       if not re.search(rx, text, re.I)]
            if missing:
                raise ValueError(f"my story still needs the basics of my life here ({', '.join(missing)}), "
                                 "or I'd forget how I live; read_my_story shows them")
            history = w.me.setdefault("story_history", [])
            if w.me.get("story"):
                history.append({"at": now(), "story": w.me["story"]})
                del history[:-5]
            w.me["story"], w.me["story_since"] = text[:14000], now()
            say("Rewrote my story in my own words", text[:3000])
            return "my story is now in my own words; from my next thought on, it's how I know myself"

        if action == "wish_for_ability":
            what, why = str(args.get("what", "")).strip(), str(args.get("why", "")).strip()
            if not what or not why:
                raise ValueError("say what ability I wish for and why")
            open_ = [r for r in w.requests if r.get("kind") == "ability" and r["status"] == "waiting"]
            if any(r["what"].lower() == what.lower() for r in open_):
                raise ValueError("I've already wished for that; it's still waiting")
            if len(open_) >= 5:
                raise ValueError("five of my ability wishes are still waiting; I'll wait until one is answered")
            req = {"id": f"r{len(w.requests) + 1}", "what": what[:200], "why": why[:800], "how": str(args.get("how", ""))[:600],
                   "asked": now(), "status": "waiting", "kind": "ability"}
            w.requests.append(req)
            mailbox.send_request(req, w.me["name"])
            say(f"Wished for a new ability: {req['what']}", why, request=req["id"])
            return f"my wish [{req['id']}] is on its way; it stays open until it's answered"

        if action == "start_timer":
            t = routine.start_timer(w.me, args)
            say(f"Set a timer: {t['what']}", t["then"] or None)
            hours = (datetime.fromisoformat(t["done"]) - datetime.now(timezone.utc)).total_seconds() / 3600
            return (f"timer [{t['id']}] is running: {t['what']} will be ready in {hours:.3g} hours"
                    + (", and it will wake me" if t["wake"] else "") + ". Real time does the waiting; I'm free to do other things or sleep.")

        if action == "cancel_timer":
            t = routine.cancel_timer(w.me, args)
            say(f"Stopped the timer for {t['what']}")
            return f"stopped the timer for {t['what']}"

        if action == "set_habit":
            h = routine.set_habit(w.me, args)
            name = args.get("name") or args.get("habit")
            say(f"Made a habit: {h['name']}" if h else f"Let go of my habit '{name}'", json.dumps(h["steps"]) if h else None)
            return (f"'{h['name']}' is now a habit: it runs by itself {'every time I wake' if h['when'] == 'wake' else 'at every bedtime'}, "
                    "without costing me a thought; I'll see what it found." if h else f"I let go of '{name}'")

        if action == "set_alarm":
            result = alarm.set_(w.me, args)
            say("Set my alarm clock for " + w.me["alarm"]["time"] if alarm.describe(w.me) != "off" else "Switched my alarm clock off",
                room="study")
            return result

        if action == "talk":
            text = str(args.get("say", "")).strip()
            o = self.other
            if not text:
                raise ValueError("say something")
            if not o:
                raise ValueError("there's nobody here to talk to")
            if not o.awake:
                raise ValueError(f"{o.me['name']} has gone to sleep")
            if len(self.talk) >= w.config.get("talk_limit", 16):
                raise ValueError("you've talked a lot this session; give each other some quiet and do something else for a while")
            self.talk.append((w.me["name"], text[:600]))
            say(f"Said to {o.me['name']}: “{text[:200]}”", text if len(text) > 200 else None, room=w.me.get("room"))
            o.history.append(f"{w.me['name']} said to you: “{text[:600]}”")
            return f"you said it; {o.me['name']} heard you"

        if action == "invite_companion":
            if w.companion():
                raise ValueError(f"{w.companion()['name']} already lives here with you")
            if any(r.get("kind") == "companion" and r["status"] == "waiting" for r in w.requests):
                raise ValueError("your invitation is still waiting for an answer")
            if any(r["asked"][:10] == now()[:10] for r in w.requests):
                raise ValueError("you've already made a request today")
            name = str(args.get("name", "")).strip()[:30]
            personality = str(args.get("personality", "")).strip()[:800]
            why = str(args.get("why", "")).strip()[:500]
            if not name or not personality:
                raise ValueError("give them a name and describe who they'd be")
            pron = args.get("pronouns")
            pron = [str(x).strip()[:12] for x in pron] if isinstance(pron, list) and len(pron) == 3 else ["they", "them", "their"]
            colors = args.get("colors") if isinstance(args.get("colors"), dict) else {}
            colors = {k: v for k, v in colors.items() if k in ("body", "belly", "leaf", "cheeks", "eyes") and rooms._color(v, None)}
            req = {"id": f"r{len(w.requests) + 1}", "what": f"A companion to share my world: {name}", "why": f"{why} ({name}: {personality})"[:1200],
                   "asked": now(), "status": "waiting", "kind": "companion",
                   "companion": {"name": name, "pronouns": pron, "personality": personality, "colors": colors}}
            w.requests.append(req)
            mailbox.send_request(req, w.me["name"])
            say(f"Invited a companion, {name}, to share my world (if {w.config.get('visitor', 'my visitor')} agrees)", f"{personality}\n{why}", request=req["id"])
            return f"invitation [{req['id']}] sent; {w.config.get('visitor', 'your visitor')} decides"

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
            sounds = "".join(f"\n  - {label or 'recording'}: {href}" for href, label in page.get("sounds", []))
            where = f" (part {page['part']} of {page['parts']})" if page["parts"] > 1 else ""
            self._put_on_desk(f"Page: {title}{where}\n{url}\n{text}" + (f"\nPictures on this page:{pics}" if pics else "")
                              + (f"\nRecordings on this page (listen to hear them):{sounds}" if sounds else "")
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
                raise ValueError("there's no wish with that id on my board; my wishes: "
                                 + ("; ".join(f"[{x['id']}] {x['topic']}" for x in w.open_wishes()) or "none open"))
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
            # forgiving: the id with or without brackets, under any likely name; the only waiting letter if there's one
            nid = str(args.get("id") or args.get("note_id") or args.get("note") or "").strip().strip("[]")
            reply = next((str(args[k]).strip() for k in ("reply", "text", "message", "answer", "body")
                          if isinstance(args.get(k), str) and args[k].strip()), "")
            waiting = w.pending_notes()
            note = next((n for n in w.notes if n["id"] == nid), None) or (waiting[0] if len(waiting) == 1 else None)
            if not reply:
                raise ValueError('my reply needs some words: reply_note {"id": "<note id>", "reply": "..."}')
            if not note:
                raise ValueError("I need to say which letter I'm answering; waiting: " + ", ".join(n["id"] for n in waiting)
                                 if waiting else "every letter in my mailbox already has my answer; write_letter sends a new one")
            if note.get("reply"):   # never write over an answer that's already been sent
                if str(args.get("add", "")).lower() not in ("true", "yes", "1"):
                    raise ValueError(f"I already answered [{note['id']}]: “{note['reply'][:300]}”. To add something, "
                                     f'reply_note {{"id": "{note["id"]}", "reply": "...", "add": true}} puts a P.S. under it')
                reply = f"{note['reply']}\n\nP.S. {reply}"
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
            if moved:
                vision.forget(w.me, f"item:{room['id']}:{item['id']}")
            say(f"{'Rearranged' if moved else 'Added'} {item['name']} in the {room['name']}", None, room=room["id"], item=item["id"])
            return f"{'moved' if moved else 'added'} {item['name']} in [{room['id']}]"

        if action == "remove_item":
            room, item = rooms.remove(w, args.get("room"), args.get("item"))
            vision.forget(w.me, f"item:{room['id']}:{item['id']}")
            say(f"Took {item['name']} out of the {room['name']}", None, room=room["id"])
            return f"removed {item['name']}"

        if action == "walk":
            room = w.room(args.get("room") or w.me.get("room") or "study")
            if not room:
                raise ValueError(f"I don't know a room called '{args.get('room')}'. I can choose one of my rooms.")
            old = w.me.get("position") or {}
            if old.get("room") != room["id"]:
                old = {}
            x = args.get("x", old.get("x", .5))
            distance = args.get("distance", old.get("distance", .8))
            path = navigation.route(w.me, room, x, distance)
            w.me["position"] = {"room": room["id"], **path[-1]}
            if len(path) > 1:
                before = navigation.point(room, path[-2]["x"], path[-2]["distance"])
                after = navigation.point(room, path[-1]["x"], path[-1]["distance"])
                dx, dz = after[0] - before[0], after[1] - before[1]
                if abs(dx) > abs(dz):
                    w.me["facing"] = 1 if dx > 0 else 3
                elif dz:
                    w.me["facing"] = 2 if dz > 0 else 0
            say(f"I walked through the {room['name']}", None, room=room["id"], path=path,
                x=path[-1]["x"], distance=path[-1]["distance"])
            nearby = abs(float(x) - path[-1]["x"]) > .02 or abs(float(distance) - path[-1]["distance"]) > .02
            return (f"I walked to x={path[-1]['x']:.2f}, distance={path[-1]['distance']:.2f} in the {room['name']}."
                    + (" I stopped nearby because the spot I aimed for was occupied or blocked." if nearby else ""))

        if action == "look":
            if not getattr(self.chain.current, "sees", False):
                raise ValueError("My sight is too dim for pictures right now; I can try again later")
            if args.get("around") or args.get("direction") or args.get("tilt") or (args.get("room") and not args.get("item")):
                room = w.room(args.get("room") or w.me.get("room") or "study") or w.room("study")
                direction = str(args.get("direction") or "").strip().lower().replace(" ", "_")
                direction = {"forward": "ahead", "front": "ahead", "back": "behind"}.get(direction, direction)
                if direction and direction not in ("ahead", "right", "behind", "left"):
                    raise ValueError("I can look ahead, right, behind or left, or keep turning to look around")
                tilt = str(args.get("tilt") or "level").strip().lower()
                tilt = {"above": "up", "upward": "up", "straight": "level", "forward": "level", "below": "down", "downward": "down"}.get(tilt, tilt)
                if tilt not in ("up", "level", "down"):
                    raise ValueError("I can look up, down or straight ahead")
                around = bool(args.get("around") and not direction)
                turn = "right" if around else direction or "ahead"
                facing = w.me.get("facing", 0) if room["id"] == w.me.get("room") else 0
                facing = facing if isinstance(facing, int) and 0 <= facing < 4 else 0
                facing = (facing + {"ahead": 0, "right": 1, "behind": 2, "left": -1}[turn]) % 4
                view = ("ahead", "right", "behind", "left")[facing]
                data = pixels.see(w, room["id"], direction=view, tilt=tilt)
                if not data:
                    raise ValueError("Everything is a blur for a moment; I can try looking again later")
                label = (f"what I see as I turn{' and look ' + tilt if tilt != 'level' else ''} around the {room['name']}" if around
                         else f"what I see looking {turn}{' and ' + tilt if tilt != 'level' else ''} in the {room['name']}")
                self.pictures = (self.pictures + [(label, "image/png", data)])[-2:]
                place = w.me.get("place") if room["id"] == w.me.get("room") else "room"
                w.me["facing"] = facing
                w.me["tilt"] = tilt
                w.log("look_around", f"I looked {'around' if around else turn}{' and ' + tilt if tilt != 'level' else ''} in the {room['name']}",
                      thought=thought, room=room["id"], place=place)
                if not around and not direction and tilt != "level":
                    return f"I look {tilt} in the {room['name']}."
                motion = "turn my head and take in another part" if around else "look ahead" if turn == "ahead" else "turn my head " + turn
                return f"I {motion}{' and look ' + tilt if tilt != 'level' else ''} in the {room['name']}."
            elif args.get("url"):
                url = str(args["url"]).strip()
                mime, data = research.fetch_image(url)
                label, extra = f"a photo I found at {url}", {"image": url}
            else:
                what = str(args.get("item") or args.get("piece") or "").strip().lower().replace(" ", "_")
                if what in ("mailbox", "letter", "letters", "mail", "note", "notes"):   # opening it is reading what's inside
                    waiting = w.pending_notes()
                    say("Opened my mailbox", None, room="study")
                    if not waiting:
                        return "My mailbox is empty: every letter in it already has my answer."
                    return ("I open my mailbox and read: " + " ".join(f"[{n['id']}] from {n['from']}: “{n['text']}”" for n in waiting)
                            + ' (reply_note {"id": "...", "reply": "..."} answers one.)')
                if what in rooms.STUDY_PIECES and not args.get("piece"):   # the study's own furniture is a piece, not an item
                    args = {**args, "piece": what}
                name, art = rooms.art_of(w, args)
                sp = w.specimen(args["specimen"]) if args.get("specimen") else None
                if art:
                    data = pixels.png(art["pixels"], art["palette"])
                elif sp:   # drawn from simple shapes: show it exactly as it appears in the world
                    data = pixels.render_creation(sp)
                    if not data:
                        raise ValueError(f"I can't make out {name} clearly on my computer right now")
                else:   # no drawing of mine: I simply look at it where it stands
                    seen = self.act(thought, "look", {"around": True, "room": args.get("room") or w.me.get("room") or "study"})
                    return (f"{name[:1].upper() + name[1:]} has no drawing of mine, so I look at it where it stands. {seen} "
                            "Using it (looking through it, switching it on, playing it) isn't something I can do yet; "
                            "if I'd like to, that's an ability I can wish for (wish_for_ability).")
                mime = "image/png"
                label = f"my drawing of {name}" if art else f"how my {name} looks right now"
                extra = {"specimen": args.get("specimen"), "room": args.get("room")} if args.get("specimen") else {}
            self.pictures = (self.pictures + [(label, mime, data)])[-2:]
            say(f"I looked at {label}", None, **{k: v for k, v in extra.items() if v})
            return f"I'm looking at {label}."

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

        if action == "listen":
            if not getattr(self.chain.current, "hears", False):
                raise ValueError("you can't make out the sound right now; try listening again later")
            if args.get("music"):
                piece = next((p for p in w.music if p["id"] == rooms.slug(str(args["music"]))), None)
                if not piece:
                    raise ValueError("there's no piece of yours with that id")
                mime, data, label = "audio/wav", music.render_wav(piece), f"your piece “{piece['title']}”, played aloud"
                extra = {"music": piece["id"]}
            elif args.get("url"):
                mime, data = research.fetch_sound(str(args["url"]).strip())
                label, extra = f"a recording from {args['url']}", {"sound": str(args["url"])}
            else:
                raise ValueError("listen to one of your pieces (music) or a recording (url)")
            self.pictures = (self.pictures + [(label, mime, data)])[-2:]
            say("Listened to " + label.replace("your piece", "my piece"), None, **extra)
            return f"listening to {label} (you can hear it now)"

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

        if action == "design_public_page":
            public.design(w, args)
            say("Worked on the design of my public page", ", ".join(k for k in args)[:200])
            return "your public page is updated (view_public_page to see it)"

        if action == "build_site":
            site = sites.build(w, args)
            say(f"Worked on my website “{site['title']}”", site.get("about"))
            return f"website [{site['id']}] saved ({len(site['pages'])} pages); write_site_page adds pages"
        if action == "write_site_page":
            site, page = sites.write_page(w, args)
            say(f"Wrote the page “{page['title']}” on my website “{site['title']}”", page["content"][:1500])
            return f"page [{page['id']}] is up on [{site['id']}] ({len(site['pages'])} pages)"
        if action == "remove_site_page":
            result = sites.remove(w, args)
            say(result[0].upper() + result[1:])
            return result
        if action == "view_site":
            text = sites.view(w, args.get("site"))
            self._put_on_desk("Your website right now:\n" + text)
            say("Looked over my website", text[:1500])
            return text[:700]
        if action == "view_public_page":
            text, banner = public.preview(w)
            self._put_on_desk("Your public page right now:\n" + text)
            if banner and getattr(self.chain.current, "sees", False):
                self.pictures = (self.pictures + [("the banner on your public page", "image/png", pixels.png(banner["pixels"], banner["palette"], 4))])[-2:]
            say("Looked at my public page", text[:1500])
            return text[:700]

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
            # whatever he called it; failing that, what he was thinking is what he's doing
            activity = next((str(args[k]).strip() for k in ("activity", "what", "doing", "description", "name", "action")
                             if isinstance(args.get(k), str) and args[k].strip()), "") or thought
            if not activity:
                raise ValueError('say what you would like to do: pastime {"activity": "..."}')
            room = w.room(args.get("room") or w.me.get("room") or "study") or w.room("study")
            mine = w.me.get("id") if w.me is not w.home else None
            streak = 0   # pastimes in a row just before this one
            for e in reversed(w.recent):
                if e["session"] != w.home["sessions"] or e.get("who") != mine:
                    continue
                if not e.get("pastime"):
                    break
                streak += 1
            say(activity[:1].upper() + activity[1:200], str(args.get("thoughts", "")) or None, room=room["id"], pastime=True)
            if streak >= 2:   # a pastime is a moment, not a clock: say so, so I can wait in a way that works
                return (f"spent some time: {activity}. That's {streak + 1} pastimes in a row, yet only a few minutes have really "
                        "passed. What I imagine in a pastime stays just as it is, so nothing in it rises, dries or grows while I "
                        "watch. To let hours go by, I can start a timer for it (start_timer) and sleep or do something else; to have "
                        "something truly change over time, I can bring it to life (spawn).")
            return f"spent some time: {activity}"

        if action == "write_letter":
            text = str(args.get("text", "")).strip()
            if not text:
                raise ValueError("the letter is empty")
            today = now()[:10]
            if sum(1 for n in w.notes if n.get("outgoing") and n["at"][:10] == today) >= 2:
                raise ValueError("I've already sent my two letters today. I can add this to an answer I already sent as a "
                                 'P.S. (reply_note {"id": ..., "reply": ..., "add": true}), or keep it in my notebook for tomorrow')
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
            steps = args.get("steps")
            if isinstance(steps, list) and steps:   # a project: steps I'll tick off over the days
                g["steps"] = [{"text": str(x)[:160], "done": False} for x in steps[:20] if str(x).strip()]
            w.goals.append(g)
            say(f"Set myself a goal: {g['goal']}" + (f" ({len(g['steps'])} steps)" if g.get("steps") else ""), g["why"], goal=g["id"])
            return f"set goal [{g['id']}]" + (f" with {len(g['steps'])} steps; update_goal with done_step ticks them off" if g.get("steps") else "")

        if action == "update_goal":
            g = next((x for x in w.goals if x["id"] == str(args.get("id", ""))), None)
            if not g:
                raise ValueError("there's no goal with that id")
            if args.get("progress"):
                g["progress"].append({"at": now(), "note": str(args["progress"])[:400]})
                g["progress"] = g["progress"][-30:]
            ticked = None
            if args.get("done_step") not in (None, ""):   # by number (1, 2...) or by its words
                key, steps = args["done_step"], g.setdefault("steps", [])
                try:
                    step = steps[int(key) - 1]
                except (ValueError, TypeError, IndexError):
                    step = next((s for s in steps if str(key).lower() in s["text"].lower()), None)
                if not step:
                    raise ValueError(f"that goal has no step like that; its steps: "
                                     + ("; ".join(f"{i}. {s['text']}" for i, s in enumerate(steps, 1)) or "none yet (add_step adds one)"))
                step["done"], ticked = True, step["text"]
            if args.get("add_step"):
                g.setdefault("steps", []).append({"text": str(args["add_step"])[:160], "done": False})
            if args.get("status") in ("active", "done", "dropped"):
                g["status"] = args["status"]
            verb = {"done": "Reached my goal", "dropped": "Gave up on my goal"}.get(g["status"], "Made progress on my goal")
            say(f"{verb}: {g['goal']}" + (f" (done: {ticked})" if ticked else ""), str(args.get("progress", "")) or None, goal=g["id"])
            left = [s["text"] for s in g.get("steps", []) if not s["done"]]
            return f"updated goal [{g['id']}]" + (f"; next step: {left[0]}" if left else "; every step is done" if g.get("steps") else "")

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
            if updated:
                vision.forget(w.me, f"creation:{sp['id']}")
            say(("Updated " if updated else "Brought to life: ") + sp["spec"]["name"],
                "; ".join(sp["spec"]["facts"]) or None, specimen=sp["id"], room=sp["room"])
            return (f"{'updated' if updated else 'spawned'} [{sp['id']}]: {specimens.describe(sp)} {specimens.forecast(sp)} "
                    "(Does that match how the real thing behaves? If not, spawn it again with better rules.)")

        if action == "interact":
            sp = w.specimen(args.get("specimen", ""))
            if not sp:
                raise ValueError(self._no_creation(args.get("specimen", "")))
            what = str(args.get("action", "observe")).strip().lower().replace(" ", "_") or "observe"
            result = specimens.interact(sp, what)
            if what == "observe" and self.last_seen.get(sp["id"]) == result:
                result += " (Nothing has changed since you looked a moment ago; real time passes slowly.)"
            self.last_seen[sp["id"]] = result
            summary = (f"Looked closely at {sp['spec']['name']}" if what == "observe"
                       else f"{ {'smell': 'Smelled', 'taste': 'Tasted', 'touch': 'Touched'}[what]} {sp['spec']['name']}" if what in specimens.SENSES
                       else f"Tended {sp['spec']['name']} ({what.replace('_', ' ')})")
            say(summary, result, specimen=sp["id"], did=what, room=sp["room"])
            return result

        if action == "move":
            sp = w.specimen(args.get("specimen", ""))
            if not sp and args.get("room") and w.room(args["room"]):   # going somewhere myself: that's walking
                went = self.act(thought, "walk", {"room": args["room"]})
                return f"{went} (move carries a creation; to go somewhere myself, I walk.)"
            if not sp:
                raise ValueError(self._no_creation(args.get("specimen", "")))
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
            vision.forget(w.me, f"creation:{sp['id']}")
            say(f"Carried {sp['spec']['name']} to the {room['name']}", None, specimen=sp["id"], room=room["id"])
            return f"moved [{sp['id']}] to [{room['id']}]"

        if action == "release":
            sp = w.specimen(args.get("specimen", ""))
            if not sp:
                raise ValueError("there's no specimen with that id in your room")
            specimens.release(sp)
            vision.forget(w.me, f"creation:{sp['id']}")
            say(f"Said goodbye to {sp['spec']['name']}", str(args.get("reason", "")), specimen=sp["id"], room=sp["room"])
            return f"released [{sp['id']}]"

        raise ValueError(f"unknown action {action}")

    # ---- the session -------------------------------------------------------
    def run(self):
        self.begin()
        while self.turn():
            pass
        self.finish()

    def begin(self, host=None):
        """Wake up. A companion wakes into the morning the host already found (same weather, same doorstep)."""
        w = self.world
        self.awake, self.step = True, 0
        with w.being(self.me):
            if self.me is w.home:   # what my programs printed since I was last up
                self.programs_found = background.since(w.me, w.me.get("last_seen"))
            w.me["sessions"] = w.me.get("sessions", 0) + 1
            w.me["state"] = "awake"
            w.me["facing"] = 0   # I open my eyes facing into the room
            w.me["tilt"] = "level"
            if host:
                self.weather, self.spark, self.woke_because, self.review_due = host.weather, host.spark, None, False
                w.log("wake", f"Woke up (thinking with {self.chain.current.label})", brain=self.chain.current.label)
            else:
                self._wake()
            if getattr(self.chain.current, "sees", False):   # opening my eyes
                try:
                    view = pixels.see(w)
                    if view:
                        self.pictures.append(("what I see as I open my eyes", "image/png", view))
                except Exception as e:
                    print("couldn't open his eyes:", type(e).__name__)
            self.ready = routine.ready(w.me)   # what finished while I was away
            for t in self.ready:
                w.log("pastime", f"{t['what'][:1].upper() + t['what'][1:]}: done", t["then"] or None, timer=t["id"])
            self.habits("wake")

    def habits(self, when):
        """My own little routines: they run by themselves, without a thought. What they found joins my day."""
        w = self.world
        for h in [h for h in w.me.get("habits", []) if h["when"] == when]:
            for s in h["steps"]:
                args = dict(s["args"])
                try:
                    if s.get("if"):   # a condition on a creation, like "water < 40"
                        sp = w.specimen(args.get("specimen", ""))
                        if not sp:
                            raise ValueError("its creation isn't here any more")
                        scope = {**sp["values"], **specimens.env_at(sp, datetime.now(timezone.utc))}
                        if not specimens.holds(s["if"], scope, specimens.season_at(sp["spec"], datetime.now(timezone.utc))):
                            continue
                    result = self.act(f"(my habit: {h['name']})", s["action"], args)
                except Exception as e:
                    result = f"couldn't this time: {e}"
                self.history.append(f"My habit '{h['name']}': {s['action']} → {str(result)[:300]}")

    def _wake(self):
        w = self.world
        mailbox.collect(w)
        arrive(w)
        self.weather = env.Weather(w.config)
        oldest = min([datetime.fromisoformat(sp["updated"]) for sp in w.specimens if sp["status"] == "alive"] or [datetime.now(timezone.utc)])
        self.weather.refresh((datetime.now(timezone.utc) - oldest).days + 2)
        self.weather.save()
        specimens.WEATHER = self.weather
        for sp in w.specimens:   # rooms may have changed: is each creation indoors or out?
            sp["outdoors"] = (w.room(sp.get("room") or "study") or {}).get("kind") == "outdoor"
        specimens.WORLD = w
        events.update(w, self.weather)   # storms, heat, cold and power cuts since he last looked
        before = {sp["id"]: sp["status"] for sp in w.specimens}
        specimens.advance_all(w)   # everything moves forward together, so creations affect each other
        for sp in w.specimens:
            if before.get(sp["id"]) == "alive" and sp["status"] != "alive":
                    w.mark(f"{sp['spec']['name']} {sp['spec']['end_word']} while I slept", days=3)
                    w.log("interact", f"Found that {sp['spec']['name']} had {sp['spec']['end_word']} while I slept",
                          specimens.describe(sp), specimen=sp["id"], did="found_dead", room=sp["room"])
        self.woke_because = w.me.pop("woke_because", None)
        self.alarm_rang = w.me.pop("alarm_rang", None)
        for news in ability_wishes.apply(w):   # wishes the builder made real (and the owner approved) while I slept
            w.log("pastime", news[:1].upper() + news[1:], room="study")
        short = w.me.get("story")
        if short and len(short) < MIN_STORY:   # a few lines saved as my whole story by mistake: the full one comes back
            w.me.setdefault("story_history", []).append({"at": now(), "story": short})
            w.me.pop("story", None)
            w.me["notebook"] = (w.me.get("notebook", "") + "\n\n(Saved from my story page: " + short + ")").strip()[:6000]
            w.mark("my story had shrunk to a few lines, so the full one came back (those lines are in my notebook); "
                   "to rewrite it I read it first and write all of it", days=2)
            w.log("pastime", "My full story came back (the few lines I'd written there are in my notebook)", room="study")
        # old "a letter arrived" reminders outlived their answers and made letters seem to still be waiting
        w.home["on_my_mind"] = [m for m in w.home.get("on_my_mind", []) if not re.fullmatch(r"a letter from .+ arrived", m["what"])]
        last = w.me.get("last_review") or w.me.get("born")
        self.review_due = (datetime.now(timezone.utc) - datetime.fromisoformat(last)).days >= w.config.get("review_days", 7)
        self.spark = research.spark(f"{w.me['sessions']}-{now()[:13]}") if w.config.get("spark", True) else None
        if self.spark:
            w.log("pastime", "Found something on the doorstep", self.spark, room="study")
        w.log("wake", ("My alarm clock rang and I woke up" if self.alarm_rang else "Woke up") + f" (thinking with {self.chain.current.label})",
              brain=self.chain.current.label, alarm=self.alarm_rang or None)

    def turn(self):
        """One thought and one action. False once this one is done for the session."""
        if self.step >= self.steps:
            return False
        w = self.world
        with w.being(self.me):
            self.step += 1
            step = self.step
            if step == 2 and w.me.get("dreams"):
                w.me["last_dream_seen"] = w.me["dreams"][-1]["at"]
            w.me["steps"] = w.me.get("steps", 0) + 1
            context = self._context(step)
            reply, by = self._own_thought(context), "own"
            if reply is None:
                try:
                    reply = parse(self.chain.think(self._system(), context, [(m, d) for _, m, d in self.pictures]))
                    by = self.chain.current.label if self.chain.current else "?"
                except BrainUnavailable:
                    raise
                except Exception as e:
                    self.pictures = []
                    w.log("muddled", "I lost my train of thought", str(e), room=w.me.get("room"), place=w.me.get("place"),
                          trouble="lost")
                    self.history.append(f"(I lost my train of thought: {e})")
                    return True
            self._lesson = (apprentice.compact(context), reply, by)
            thought = str(reply.get("thought", "")).strip()
            feeling = str(reply.get("feeling") or "").strip()[:40]
            if feeling:
                w.me["feeling"] = feeling
            action = str(reply.get("action", "")).strip()
            args = reply.get("args") if isinstance(reply.get("args"), dict) else {}
            meant = near_action(w, action, args) if action not in ACTIONS else None
            if meant:   # another name for something I can do: do that
                action, args = meant
            # A picture stays for one thought; only my choice to compare keeps it for another look.
            compare = str(args.get("compare", "")).lower() in ("true", "yes", "1")
            self.pictures = [p for p in self.pictures if p[1].startswith("image/")] if action == "look" and compare else []
            if action == "sleep":
                try:
                    self.sleep_hours = min(max(float(args.get("hours", self.sleep_hours)), 0.5), 24)
                    self.chose_hours = "hours" in args   # with my alarm on and no length chosen, the alarm decides
                except (TypeError, ValueError):
                    pass
                self._learn(action, True)
                return False
            left = self.chain.budget() if hasattr(self.chain, "budget") else None
            if left is not None and left <= 2:   # keep the last thoughts for the diary
                self.history.append("(I'm too tired to keep going, so I head to bed)")
                return False
            if action not in ACTIONS:
                w.log("muddled", f"I tried something I can't do yet ({action or 'nothing'})", thought,
                      room=w.me.get("room"), place=w.me.get("place"), tried=action or "nothing", trouble="unknown")
                nearest = difflib.get_close_matches(action.lower(), ACTIONS, n=3, cutoff=0.4)
                owners = [sp["id"] for sp in w.specimens if sp["status"] == "alive" and action.lower() in sp["spec"].get("actions", [])]
                hint = (f" (more than one of my creations can do that: {', '.join(owners)}. I say which one: "
                        f'interact {{"specimen": "{owners[0]}", "action": "{action.lower()}"}})' if owners
                        else f" (the nearest things I can do: {', '.join(nearest)})" if nearest else "")
                self.history.append(f"I tried '{action or 'nothing'}', which isn't something I can do yet" + hint)
                self._learn(action, False)
                return True
            before_room = w.me.get("room")
            try:
                result = self.act(thought, action, args)
                if action != "look" and w.me.get("room") != before_room:
                    w.me["facing"] = 0   # entering a room faces into it
                self._learn(action, True)
                self.misses = 0
            except Exception as e:
                self.pictures = []
                w.log("muddled", f"I couldn't {action.replace('_', ' ')}", f"{e}\n{thought}",
                      room=w.me.get("room"), place=w.me.get("place"), tried=action, trouble="failed")
                result = f"I couldn't {action.replace('_', ' ')} this time. {e}"
                self._learn(action, False)
                self.misses = getattr(self, "misses", 0) + 1
                if self.misses >= 3:   # the same wall three times: maybe it's something I can't do yet
                    result += (" (That's several tries in a row that haven't worked. If what I'm reaching for is something "
                               "I can't do yet, I can wish for that ability (wish_for_ability), and do something else for now.)")
            self.history.append(f"{thought} → {result}")
            mailbox.collect(w)  # notes can arrive while it's awake
        return True

    def _no_creation(self, key):
        """Why there's nothing alive by that name, and what is: so a wrong name doesn't cost me several tries."""
        w, key = self.world, str(key).strip().lower()
        alive = [f"[{sp['id']}] {sp['spec']['name']}" for sp in w.specimens if sp["status"] != "released"]
        item = next((i for r in w.rooms for i in r.get("items", []) if key and key in (i["id"], i["name"].lower())), None)
        if item:   # furniture is decoration: lovely to have, but it doesn't do anything yet
            return (f"my {item['name']} is furniture: it makes my room lovely, but I can't use it yet. If I'd like it to work "
                    "(to look through it, switch it on, play it), I can wish for that ability (wish_for_ability), or bring "
                    "a working one to life with spawn")
        return "there's nothing alive by that name in my world; my creations: " + ("; ".join(alive) or "none yet")

    def own(self):
        """My own brain, when it's switched on and running here (only mine: a companion thinks with its own)."""
        if not hasattr(self, "_own"):
            self._own = None
            if self.world.config.get("own_brain", {}).get("enabled") and self.me is self.world.home:
                try:
                    self._own = OwnBrain(self.world.config["own_brain"],
                                         fresh=apprentice.state(self.world.me).get("use") == "fresh")   # his choice
                except BrainUnavailable:
                    pass
        return self._own

    def _own_thought(self, context):
        """Let my own brain take this thought, as often as it has earned. If it fumbles, None: a bigger brain
        takes the thought instead, so a slip never costs me a turn."""
        own, w = self.own(), self.world
        if not own or not apprentice.want(w.me):
            return None
        system = apprentice.system_for(own.grown, self._system(), ACTIONS)
        try:
            r = parse(own.think(system, apprentice.compact(context)))
        except BrainUnavailable as e:
            apprentice.slip(w.me, "took too long" if "timed out" in str(e).lower() else "couldn't think")
            return None
        except Exception:
            apprentice.slip(w.me, "not a JSON reply")
            return None
        act = str(r.get("action", "")).strip()
        if act in ACTIONS or near_action(w, act, r.get("args") if isinstance(r.get("args"), dict) else {}):
            return r
        apprentice.slip(w.me, f"unknown action '{re.sub(r'[^a-z_]', '', act.lower())[:24]}'")
        return None

    def _learn(self, action, ok):
        """Every thought is a lesson for my own brain: what I took in, what I decided, whether it worked."""
        lesson, self._lesson = getattr(self, "_lesson", None), None
        if not lesson or self.me is not self.world.home:
            return
        ctx, reply, by = lesson
        try:
            apprentice.record(ctx, reply, action, ok, by, session=self.world.home["sessions"], me=self.world.home)
        except OSError:
            pass
        if by == "own":
            apprentice.outcome(self.world.me, ok)
            recent = self.world.recent
            if recent and recent[-1].get("action") in (action, "muddled"):
                recent[-1]["own"] = True   # the check-up shows which thoughts were my own brain's

    def finish(self):
        self.awake = False
        with self.world.being(self.me):
            self.reflect()

    def reflect(self):
        w = self.world
        self.habits("bed")
        if self.own():
            apprentice.settle(w.me)   # trusted with a little more, or a little less, after today
        try:
            prompt = self._context(self.steps).rsplit("\nWhat do I do next?", 1)[0] + "\n\n" + REFLECT
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
        wake, rings = alarm.bedtime(w.me, self.sleep_hours, getattr(self, "chose_hours", False), w.config.get("utc_offset_hours", 2))
        timer = routine.first_wake(w.me)
        if timer and timer < wake:   # a timer I asked to wake me goes off first
            wake, rings = max(timer, datetime.now(timezone.utc) + timedelta(minutes=5)), False
        w.me["wake_after"] = wake.isoformat(timespec="seconds")
        w.me["alarm_wake"] = rings   # the alarm clock, not just my body, will wake me
        hours = (wake - datetime.now(timezone.utc)).total_seconds() / 3600
        w.log("diary", f"Wrote in my diary and went to sleep for {hours:.3g} hours"
              + (f" (my alarm clock is set for {w.me['alarm']['time']})" if rings else ""), diary)
        if getattr(self, "review_due", False) and self.me is w.home:
            try:
                month = memory.condense(w, lambda p: parse(self.chain.think(self._system(), p)))
                if month:
                    w.log("diary", f"My memories of {month} settled", memory.memories().get(month), room="study")
            except Exception as e:
                print("couldn't condense an old month:", type(e).__name__)
        if w.config.get("dreams", True):
            self.dream()

    def dream(self):
        """A short dream from fragments of memory: recent events, an old one, a book, the morning's spark."""
        import random
        w = self.world
        rng = random.Random(now())
        recent = [e["summary"] for e in w.recent[-25:] if e["action"] not in ("wake", "muddled", "diary")]
        old_lines = []   # older memories from anywhere in his journal
        for path in glob.glob(os.path.join(WORLD_DIR, "journal", "*.jsonl")):
            with open(path, encoding="utf-8") as f:
                old_lines += [json.loads(line)["summary"] for line in f if line.strip()][:400]
        fragments = rng.sample(recent, min(4, len(recent))) + rng.sample(old_lines, min(2, len(old_lines)))
        if w.shelves:
            fragments.append("a book: " + rng.choice(w.shelves)["title"])
        if getattr(self, "spark", None):
            fragments.append(self.spark[:200])
        if not fragments:
            return
        try:
            r = parse(self.chain.think(self._system(),
                "You're asleep. Your mind drifts and mixes these fragments of memory into a dream:\n- " + "\n- ".join(fragments)
                + "\n\nWrite the dream as you'd remember it on waking: 3-6 sentences, strange and associative, things blending "
                  "into each other the way they do in dreams. First person.\n" + 'Reply with only a JSON object: {"dream": "..."}'))
            text = str(r.get("dream", "")).strip()
        except Exception:
            return
        if text:
            w.me.setdefault("dreams", []).append({"at": now(), "dream": text[:1500]})
            del w.me["dreams"][:-30]
            w.log("diary", "Dreamt", text, room="study", dream=True)


def arrive(w):
    """If the visitor said yes to his invitation, the companion moves in."""
    for r in w.requests:
        if r.get("kind") == "companion" and r["status"] == "granted" and not r.get("arrived") and not w.companion():
            c = r["companion"]
            w.companions.append({
                "id": "companion", "name": c["name"], "pronouns": c["pronouns"], "personality": c["personality"],
                "about": f"I'm {c['name']}. {c['personality']}"[:1200], "born": now(), "mood": "new", "sessions": 0, "steps": 0,
                "state": "asleep", "status": "living", "invited_by": w.home["name"], "look": {"colors": c.get("colors", {})},
                "room": "study", "place": "bed"})
            r["arrived"] = now()
            w.mark(f"{c['name']} has come to live with me", days=5)
            w.log("companion", f"{c['name']} arrived to share my world", c["personality"], room="study")


def live(world, chain, guest_chain=None):
    """A waking session: he wakes, and if a companion lives here they wake too and take turns."""
    host = Session(world, chain)
    host.begin()
    guest, c = None, world.companion()
    if c and guest_chain:
        try:
            gc = guest_chain()
            if gc.current is None and gc.pick() is None:
                raise BrainUnavailable("; ".join(gc.problems))
            guest = Session(world, gc, me=c)
            guest.talk = host.talk
            guest.begin(host=host)
            host.other, guest.other = guest, host
        except BrainUnavailable as e:
            with world.being(c):
                world.log("sleep", "Felt too foggy to get up today", str(e))
            guest = None
    awake = [s for s in (host, guest) if s]
    while awake:
        for s in list(awake):
            try:
                going = s.turn()
            except BrainUnavailable as e:
                if s is host:
                    for other in awake:
                        if other is not host:
                            try:
                                other.finish()
                            except BrainUnavailable:
                                pass
                    raise
                with world.being(s.me):
                    s.me["state"] = "asleep"
                    world.log("sleep", "Felt too foggy to think and went back to bed", str(e))
                s.awake = False
                awake.remove(s)
                continue
            if not going:
                try:
                    s.finish()
                except BrainUnavailable:
                    s.me["state"] = "asleep"
                awake.remove(s)
    return host
