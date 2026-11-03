"use strict";
// The AI's world. Reads the plain files in world/ and replays what it did. Drawing lives in sprites.js.

const H = 180;
const STUDY_PLACES = {    // where he stands in the study for each activity (feet position)
  shelves:  { x: 46,  y: 134, pose: "stand" },
  board:    { x: 90,  y: 128, pose: "stand" },
  armchair: { x: 132, y: 128, pose: "sit" },
  computer: { x: 199, y: 130, pose: "type" },
  mailbox:  { x: 266, y: 124, pose: "stand" },
  bed:      { x: 270, y: 146, pose: "sleep" },
};
const STUDY_HOTSPOTS = [  // clickable study furniture -> tab
  { x: 6,   y: 22,  w: 62, h: 100, tab: "shelves",  label: "Bookshelves" },
  { x: 72,  y: 26,  w: 36, h: 40,  tab: "wishes",   label: "Wishlist board" },
  { x: 168, y: 70,  w: 66, h: 54,  tab: "journal",  label: "Computer", filter: "computer" },
  { x: 240, y: 44,  w: 46, h: 68,  tab: "mail",     label: "Mailbox" },
  { x: 232, y: 128, w: 84, h: 44,  tab: "journal",  label: "Bed (diary)", filter: "diary" },
  { x: 112, y: 100, w: 40, h: 40,  tab: "now",      label: "Armchair" },
];
const STUDY_SLOTS = [124, 166, 208, 86, 60, 300];
const PROPS = { read_book: "book", write_book: "book", build_room: "tool", decorate: "tool", remove_item: "tool", spawn: "tool" };

const $ = (id) => document.getElementById(id);
const canvas = $("room"), ctx = canvas.getContext("2d");
const S = {
  cfg: {}, me: {}, shelves: [], wishes: [], notes: [], recent: [], specimens: [], rooms: [{ id: "study", name: "Study", builtin: true, width: 320, items: [] }],
  view: "study", boxes: [],
  bot: { room: "study", x: STUDY_PLACES.bed.x, y: STUDY_PLACES.bed.y, tx: STUDY_PLACES.bed.x, ty: STUDY_PLACES.bed.y, pose: "sleep", walking: false, prop: null },
  bot2: { room: "study", x: 256, y: 146, tx: 256, ty: 146, pose: "sleep", walking: false, prop: null },   // a companion, if one lives here
  comp: null,
  queue: [], current: null, holdUntil: 0, replaying: false, lastKey: null, journalFilter: null,
};
// A companion who never chose colours of their own still shouldn't look like him.
const COMP_COLORS = { body: "#e3a35c", belly: "#f5d6a6", leaf: "#c75b3f", cheeks: "#f08f80" };
const compLook = (c) => ({ ...(c.look || {}), colors: { ...COMP_COLORS, ...((c.look || {}).colors || {}) } });
const actorOf = (e) => (e && e.who && S.comp ? S.bot2 : S.bot);
const whoName = (e) => (e.who && S.comp ? S.comp.name : S.me.name);
let P = { he: "it", him: "it", his: "its" };
const cap = (s) => s.charAt(0).toUpperCase() + s.slice(1);

// ---------- loading -------------------------------------------------------
async function getJSON(name, fallback) {
  if (S.locked) {   // online: read from the world unlocked in this browser
    const t = Vault.text(name);
    try { return t == null ? fallback : JSON.parse(t); } catch { return fallback; }
  }
  try {
    const r = await fetch(`world/${name}?t=${Date.now()}`, { cache: "no-store" });
    return r.ok ? await r.json() : fallback;
  } catch { return fallback; }
}
const key = (e) => e.t + "|" + e.summary;

async function load(first) {
  if (S.locked && !first && !(await Vault.refresh())) return showLock("Your password changed; please unlock again.");
  if (S.locked) { try { await Vault.refreshLive(JSON.parse(Vault.files["config.json"] || "{}").repo); } catch {} }
  S.goals = await getJSON("goals.json", []);
  S.requests = await getJSON("requests.json", []);
  S.music = await getJSON("music.json", []);
  const [cfg, me, shelves, wishes, notes, recent, specimens, rooms] = await Promise.all([
    getJSON("config.json", {}), getJSON("self.json", null), getJSON("shelves.json", []), getJSON("wishlist.json", []),
    getJSON("notes.json", []), getJSON("recent.json", []), getJSON("specimens.json", []), getJSON("rooms.json", null),
  ]);
  S.weather = await getJSON("weather_now.json", null);
  const companions = await getJSON("companions.json", []);
  const comp = companions.find((c) => c.status === "living") || null;
  const sig = JSON.stringify([cfg, me, comp, shelves, wishes, notes, specimens, rooms, recent.length && recent[recent.length - 1]]);
  if (!first && sig === S.sig) { renderStatus(); return; }   // nothing new: keep the panels as the visitor left them
  S.sig = sig;
  Object.assign(S, { cfg, shelves, wishes, notes, specimens });
  if (rooms) S.rooms = rooms;
  if (cfg.pronouns) P = { he: cfg.pronouns[0], him: cfg.pronouns[1], his: cfg.pronouns[2] };
  if (!me) {
    $("status").textContent = "Nobody lives here yet. Wake the AI up for the first time to move it in.";
    $("tab-now").innerHTML = '<p class="muted">The room is ready and waiting. Once the AI wakes up for the first time, it moves in.</p>';
    renderRoomBar();
    return;
  }
  S.me = me;
  const newcomer = comp && !S.comp;
  S.comp = comp;
  if (comp && (first || newcomer)) { const c = restSpot(); Object.assign(S.bot2, { room: c.room, x: c.x, y: c.y, tx: c.x, ty: c.y, pose: c.pose }); }
  const prevKey = S.lastKey;
  S.recent = recent;
  S.lastKey = recent.length ? key(recent[recent.length - 1]) : null;

  if (first) {
    const asleep = me.state === "asleep";
    const spot = asleep ? { ...STUDY_PLACES.bed, room: "study" } : spotFor({ room: me.room, place: me.place, specimen: null });
    Object.assign(S.bot, { room: spot.room, x: spot.x, y: spot.y, tx: spot.x, ty: spot.y, pose: spot.pose });
    S.view = S.bot.room;
  } else if (prevKey && prevKey !== S.lastKey && !S.replaying) {
    const i = recent.findIndex((e) => key(e) === prevKey);
    recent.slice(i + 1).forEach((e) => S.queue.push(e));   // watch him live
  }
  document.title = `${me.name}'s World`;
  $("title").textContent = `${me.name}'s World`;
  renderStatus(); renderTabs(); renderRoomBar();
}

// ---------- rooms & positions ------------------------------------------------
const roomOf = (id) => S.rooms.find((r) => r.id === id) || S.rooms[0];
const roomW = (id) => roomOf(id).width || 320;
const liveIn = (roomId) => S.specimens.filter((s) => s.status !== "released" && (s.room || "study") === roomId);
const floorY = (room) => room.builtin ? 152 : room.kind === "outdoor" ? 146 : 140;

function specimenX(sp) {
  const room = roomOf(sp.room || "study"), W = room.width || 320, here = liveIn(room.id);
  const placed = (s) => Math.round(20 + s.x * (W - 40));
  if (sp.x != null) return placed(sp);
  // Things without a chosen spot take the free slots, steering clear of the ones he placed himself.
  const taken = here.filter((s) => s.x != null).map(placed);
  const slots = (room.builtin ? STUDY_SLOTS : Array.from({ length: 8 }, (_, k) => Math.round((W * (k + 1)) / 9)))
    .filter((x) => taken.every((t) => Math.abs(t - x) > 22));
  const i = here.filter((s) => s.x == null).indexOf(sp);
  return slots.length ? slots[i % slots.length] : Math.round((W * (i + 1)) / (here.length + 1));
}
const itemX = (item, room) => Math.round(16 + item.x * ((room.width || 320) - 32));

function spotFor(e) {   // where he stands for an event: {room, x, y, pose}
  const room = roomOf(e.room || "study"), W = room.width || 320;
  if (e.specimen) {
    const sp = S.specimens.find((s) => s.id === e.specimen);
    if (sp) {
      const sx = specimenX(sp), x = sx - 16 < 10 ? sx + 16 : sx - 16;
      return { room: sp.room || room.id, x, y: 170, pose: "stand" };
    }
  }
  if (e.item) {
    const it = room.items.find((i) => i.id === e.item);
    if (it) return { room: room.id, x: Math.min(W - 12, itemX(it, room) + 20), y: room.builtin ? 160 : floorY(room) + 14, pose: "stand" };
  }
  if (room.builtin && STUDY_PLACES[e.place]) return { room: "study", ...STUDY_PLACES[e.place] };
  return { room: room.id, x: Math.round(W / 2), y: room.builtin ? 150 : 158, pose: "stand" };
}

function restSpot() {
  const c = S.comp;
  if (c.state === "asleep" || !c.room) return { room: "study", x: 256, y: 146, pose: "sleep" };
  const s = spotFor({ room: c.room, place: c.place });
  return (s.room === S.bot.room && Math.abs(s.x - S.bot.x) < 14) ? { ...s, x: s.x > 40 ? s.x - 20 : s.x + 20, pose: s.pose === "type" ? "stand" : s.pose } : s;
}
function talkSpot(e) {   // walk over to whoever they're talking to
  const o = e.who ? S.bot : S.bot2;
  return { room: o.room, x: o.x > 40 ? o.x - 20 : o.x + 20, y: Math.min(o.y, 168), pose: "stand" };
}

function setView(id) {
  S.view = id;
  canvas.width = roomW(id);
  canvas.style.width = (roomW(id) / 320) * 100 + "%";   // bigger rooms keep the same scale and scroll sideways
  renderRoomBar();
}

function followBot() {
  const stage = $("stage"), extra = canvas.clientWidth - stage.clientWidth;
  if (extra <= 0 || S.bot.room !== S.view) return;
  const want = Math.min(extra, Math.max(0, S.bot.x * (canvas.clientWidth / canvas.width) - stage.clientWidth / 2));
  if (Math.abs(stage.scrollLeft - want) > 2 && (S.bot.walking || S.current)) stage.scrollLeft += (want - stage.scrollLeft) * 0.1;
}

function renderRoomBar() {
  const bar = $("rooms");
  if (S.rooms.length < 2) { bar.hidden = true; return; }
  bar.hidden = false;
  bar.innerHTML = S.rooms.map((r) => `<button type="button" data-room="${esc(r.id)}" class="${r.id === S.view ? "on" : ""}"
    title="${esc(r.purpose || r.name)}">${r.id === S.bot.room && S.me.name ? "🌱 " : ""}${S.comp && r.id === S.bot2.room ? "🍂 " : ""}${esc(r.name)}</button>`).join("");
}

// ---------- status & panels ------------------------------------------------
function ago(iso) {
  if (!iso) return "never";
  const s = (Date.now() - new Date(iso)) / 1000;
  if (s < 0) { const m = Math.round(-s / 60); return m < 60 ? `in ${m} min` : `in ${Math.round(m / 60)} h`; }
  if (s < 90) return "just now";
  if (s < 3600) return `${Math.round(s / 60)} min ago`;
  if (s < 86400) return `${Math.round(s / 3600)} h ago`;
  return `${Math.round(s / 86400)} days ago`;
}
const when = (iso) => new Date(iso).toLocaleString(undefined, { weekday: "short", hour: "2-digit", minute: "2-digit", day: "numeric", month: "short" });
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

// The weather in his world right now (from the hourly forecast saved when he last woke).
function weatherNow() {
  if (!S.weather) return null;
  const key = new Date().toISOString().slice(0, 13);
  return S.weather.hours[key] || null;
}

// What's happening in his world right now: storms from the live weather, the rest from his last wake-up.
function happening() {
  const w = weatherNow(), ev = S.me.world_events || {}, now = new Date().toISOString();
  return {
    storm: !!w && (w.env_wind >= 45 || w.env_rain >= 6),
    power: (ev.cuts || []).some((c) => c.since <= now && now < c.until),
    heat: (ev.now || []).includes("heat wave"),
    cold: (ev.now || []).includes("cold snap"),
  };
}
const powerCut = () => !!S.me.name && happening().power;

function renderStatus() {
  const me = S.me;
  if (!me.name) return;   // nobody has moved in yet
  let line = me.state === "asleep" ? `💤 Asleep — last awake ${ago(me.last_seen)}.` : `✨ Awake: ${me.activity}`;
  const w = weatherNow();
  if (w) line = `${w.env_rain > 0 ? "🌧" : w.env_daylight ? "☀️" : "🌙"} ${Math.round(w.env_temp)}°C in ${S.weather.place} · ` + line;
  if (me.state === "asleep" && S.cfg.next_wake) line += ` Next wake-up ${ago(S.cfg.next_wake)}.`;
  if (S.locked && Vault.liveOn && me.state !== "asleep") line = "🔴 Live · " + line;
  const h = happening();
  line = [h.storm && "⛈ Storm", h.power && "⚡ Power cut", h.heat && "🔥 Heat wave", h.cold && "❄ Cold snap"].filter(Boolean).concat(line).join(" · ");
  $("status").textContent = line;
}

function spineColor(shelf) { return `hsl(${Px.hash(shelf) % 360} 45% 45%)`; }

function renderTabs() {
  const me = S.me, open = S.wishes.filter((w) => w.status === "want" || w.status === "learning");
  const days = Math.max(0, Math.floor((Date.now() - new Date(me.born)) / 86400000));
  const lastWake = [...S.recent].reverse().find((e) => e.action === "wake");
  const living = S.specimens.filter((s) => s.status !== "released");
  $("tab-now").innerHTML = `
    <div class="hero"><canvas id="portrait" width="64" height="52" aria-label="${esc(me.name)}"></canvas>
      <div><div class="hero-name">${esc(me.name)}</div>
      <div class="muted">Feeling <b>${esc(me.mood)}</b></div>
      <div>${me.state === "asleep" ? "Sleeping" : "Right now"}: ${esc(me.activity || "—")}</div>
      <div class="muted" style="font-size:12px">Thinks with ${esc(lastWake?.brain || "—")}</div></div></div>
    <div class="stats">
      <div class="stat"><b>${S.shelves.length}</b><span>books</span></div>
      <div class="stat"><b>${living.length}</b><span>creations</span></div>
      <div class="stat"><b>${S.rooms.length}</b><span>${S.rooms.length === 1 ? "room" : "rooms"}</span></div>
      <div class="stat"><b>${days}</b><span>days old</span></div>
    </div>
    <h3>In ${esc(P.his)} own words</h3>
    <p class="about">${esc(me.about)}</p>
    ${S.comp ? `<h3>Living with ${esc(P.him)}</h3><div class="hero"><canvas id="portrait2" width="64" height="52" aria-label="${esc(S.comp.name)}"></canvas>
      <div><div class="hero-name">${esc(S.comp.name)}</div><div class="muted">Feeling <b>${esc(S.comp.mood)}</b> · moved in ${ago(S.comp.born)}</div>
      <div>${S.comp.state === "asleep" ? "Sleeping" : "Right now"}: ${esc(S.comp.activity || "—")}</div></div></div>
      <p class="about">${esc(S.comp.about)}</p>` : ""}
    ${(me.moods || []).length > 1 ? `<h3>${esc(cap(P.his))} mood lately</h3><p class="muted">${me.moods.slice(-10).map((m) => `${esc(m.mood)}`).join(" → ")}</p>` : ""}
    ${(me.life_story || []).length ? `<h3>${esc(cap(P.his))} life story</h3>${me.life_story.map((c, i) => `<details${i === me.life_story.length - 1 ? " open" : ""}>
      <summary><b>${i + 1}. ${esc(c.title)}</b> <span class="muted">${when(c.at)}</span></summary><p class="about" style="white-space:pre-wrap">${esc(c.text)}</p></details>`).join("")}` : ""}
    ${me.rules ? `<h3>${esc(cap(P.his))} own rules</h3><p class="about" style="white-space:pre-wrap">${esc(me.rules)}</p>` : ""}
    ${(me.wake_triggers || []).length ? `<h3>Wakes up early when</h3><ul class="list">${me.wake_triggers.map((t) =>
      `<li>${t.kind === "rain" ? `it rains (at least ${t.min_mm} mm/h)` : t.kind === "time" ? `it's ${esc(t.at)}` :
        `${esc((S.specimens.find((s) => s.id === t.specimen) || { spec: { name: t.specimen } }).spec.name)}: ${esc(t.if)}`}</li>`).join("")}</ul>` : ""}`;

  const groups = {};
  S.shelves.forEach((b) => (groups[b.shelf] ||= []).push(b));
  $("tab-shelves").innerHTML = S.shelves.length ? Object.keys(groups).sort().map((g) => `
    <h3>${esc(g)}</h3><ul class="list">${groups[g].map((b) => `
      <li class="book-item" data-book="${esc(b.id)}"><span class="spine" style="background:${spineColor(b.shelf)}"></span>
      <div><div class="bt">${esc(b.title)}</div><div class="muted">${esc(b.summary)}</div>
      <div class="muted" style="font-size:12px">${b.words} words · ${ago(b.updated)}${b.revisions ? ` · revised ${b.revisions}×` : ""}
      ${!b.sources.length ? "" : b.sources_checked ? '<span class="chip ok" title="Every source listed was actually read">sources checked</span>' : '<span class="chip" title="Some listed sources were not read in the session that wrote it">sources unchecked</span>'}</div></div></li>`).join("")}</ul>`).join("")
    : `<p class="muted">The shelves are empty. Books appear here as ${esc(me.name)} learns and writes.</p>`;

  const sec = (title, list) => list.length ? `<h3>${title}</h3><ul class="list">${list.map((w) => `<li><b>${esc(w.topic)}</b>
      ${w.book ? `<span class="chip ok book-link" data-book="${esc(w.book)}" style="cursor:pointer">📖 read the book</span>` : ""}
      <div class="muted">${esc(w.reason || w.why)}</div></li>`).join("")}</ul>` : "";
  const goals = (S.goals || []).filter((g) => g.status !== "dropped");
  const goalHtml = goals.length ? `<h3>Long-term goals</h3><ul class="list">${goals.map((g) => `<li><b>${g.status === "done" ? "✅ " : "🎯 "}${esc(g.goal)}</b>
      <div class="muted">${esc(g.why)}</div>${g.progress.length ? `<ul class="hist">${g.progress.slice(-3).reverse().map((p) => `<li>${esc(p.note)} <span class="muted">${ago(p.at)}</span></li>`).join("")}</ul>` : ""}</li>`).join("")}</ul>` : "";
  $("tab-wishes").innerHTML = goalHtml + (sec("Learning now", S.wishes.filter((w) => w.status === "learning")) +
    sec("Wants to learn", S.wishes.filter((w) => w.status === "want")) +
    sec("Learned", S.wishes.filter((w) => w.status === "learned").reverse()) +
    sec("Gave up on", S.wishes.filter((w) => w.status === "dropped"))) || `<p class="muted">The board is empty. ${esc(me.name)} decides what goes here.</p>`;

  renderCreations(); renderJournal(); renderMail();
}

function renderCreations() {
  const live = S.specimens.filter((s) => s.status !== "released");
  const gone = S.specimens.filter((s) => s.status === "released");
  const card = (sp) => {
    const spec = sp.spec, living = ["plant", "animal", "creature"].includes(spec.kind);
    const state = sp.status === "dead" ? spec.end_word : living ? "alive" : sp.moving ? "running" : "";
    const bars = Object.entries(spec.vars).map(([k, v]) => {
      const n = Math.max(0, Math.min(1, (sp.values[k] - v.min) / (v.max - v.min)));
      return `<div class="var"><span>${esc(k.replace(/_/g, " "))}</span><span class="bar"><i style="width:${(n * 100).toFixed(0)}%"></i></span><span>${+sp.values[k].toFixed(2)} ${esc(v.unit)}</span></div>`;
    }).join("");
    const history = S.recent.filter((e) => e.specimen === sp.id).slice(-3).reverse().map((e) => `<li>${esc(e.summary)} <span class="muted">${ago(e.t)}</span></li>`).join("");
    const book = S.shelves.find((b) => b.id === sp.book);
    return `<div class="creation" id="card-${esc(sp.id)}">
      <canvas class="mini" data-spec="${esc(sp.id)}" width="64" height="56"></canvas>
      <div class="cbody"><div class="bt">${esc(spec.name)}</div>
      <div class="muted" style="font-size:12px">${esc(spec.kind)}${state ? " · " + esc(state) : ""}${sp.season ? ` · ${esc(sp.season)} season` : ""} · in the ${esc(roomOf(sp.room || "study").name)} · since ${ago(sp.born)}</div>
      ${sp.signs?.length ? `<div class="signs">👀 ${sp.signs.map(esc).join(" · ")}</div>` : ""}
      ${sp.events?.length ? `<div class="signs">⚡ ${sp.events.slice(-3).reverse().map((e) => `${esc(e.note)} <span class="muted">${ago(e.t)}</span>`).join(" · ")}</div>` : ""}
      ${bars}
      ${spec.facts?.length ? `<details><summary>What ${esc(P.he)} based it on</summary><ul>${spec.facts.map((f) => `<li>${esc(f)}</li>`).join("")}</ul>${book ? `<span class="chip ok" data-book="${esc(book.id)}" style="cursor:pointer">📖 ${esc(book.title)}</span>` : ""}</details>` : ""}
      <div class="muted" style="font-size:12px">${esc(cap(P.he))} can: observe${Object.keys(spec.actions).map((a) => ", " + esc(a.replace(/_/g, " "))).join("")}</div>
      ${history ? `<ul class="hist">${history}</ul>` : ""}</div></div>`;
  };
  const rooms = S.rooms.filter((r) => !r.builtin).map((r) => `<li><b>${esc(r.name)}</b> <span class="muted">${esc(r.kind)} · ${r.items.length} things</span><div class="muted">${esc(r.purpose)}</div></li>`).join("");
  const tunes = (S.music || []).slice().reverse().map((p) => `<li class="tune"><button class="btn play" data-play="${esc(p.id)}" type="button">▶</button>
      <div><b>${esc(p.title)}</b> <span class="muted">${esc(p.instrument)} · ${p.tempo} bpm · ${ago(p.composed)}</span>
      ${p.about ? `<div class="muted">${esc(p.about)}</div>` : ""}</div></li>`).join("");
  $("tab-made").innerHTML = (tunes ? `<h3>Music ${esc(P.he)} composed</h3><ul class="list">${tunes}</ul>` : "") + (live.length ? `<h3>Brought to life</h3>${live.map(card).join("")}` :
    `<p class="muted">Nothing here yet. When ${esc(S.me.name)} learns about something (a plant, an animal, a car, a recipe, a machine), ${esc(P.he)} can bring a simulated one into ${esc(P.his)} world and look after it.</p>`) +
    (rooms ? `<h3>Rooms ${esc(P.he)} built</h3><ul class="list">${rooms}</ul>` : "") +
    (gone.length ? `<h3>Said goodbye to</h3><ul class="list">${gone.map((s) => `<li>${esc(s.spec.name)} <span class="muted">${ago(s.released)}</span></li>`).join("")}</ul>` : "");
}

function renderJournal() {
  const f = S.journalFilter;
  const list = [...S.recent].reverse().filter((e) => !f || (f === "diary" ? e.action === "diary" : e.place === f));
  let session = null, html = f ? `<p class="muted">Showing only ${f === "diary" ? "diary entries" : "research at the computer"}. <a href="#" id="clear-filter">Show everything</a></p>` : "";
  html += '<ul class="list">';
  for (const e of list) {
    if (e.session !== session) { session = e.session; html += `<li class="session-head">Session ${session}</li>`; }
    html += `<li class="ev ${e.action === "diary" ? "diary" : ""}" data-key="${esc(key(e))}">
      <div>${S.comp ? `<b>${esc(whoName(e))}:</b> ` : ""}${esc(e.summary)}</div><div class="when">${when(e.t)}${e.thought ? ` · “${esc(e.thought)}”` : ""}</div>
      ${e.image && /^https?:\/\//.test(e.image) ? `<img class="seen" src="${esc(e.image)}" alt="" loading="lazy" referrerpolicy="no-referrer">` : ""}
      ${e.detail ? `<div class="detail">${esc(e.detail)}</div>` : ""}</li>`;
  }
  $("tab-journal").innerHTML = html + "</ul>" + (list.length ? "" : '<p class="muted">Nothing yet.</p>');
}

function renderMail() {
  const name = esc(S.me.name), cfg = S.cfg;
  let form;
  if (S.locked) {
    form = `<form class="note-form" id="note-form"><input name="from" placeholder="Your name" value="${esc(cfg.visitor || "")}">
      <textarea name="text" placeholder="Leave ${name} a note. It's sealed with your password before it leaves this page, and it wakes ${esc(P.him)} up." required></textarea>
      <button class="btn" type="submit">✉ Seal and send</button> <span id="note-msg" class="muted"></span></form>`;
  } else if (cfg.mode === "github" && cfg.repo) {
    form = `<p>Notes are left as GitHub issues, so ${name} can read them when ${esc(P.he)} wakes up. Only notes from the owner of this world are read.</p>
      <a class="btn" target="_blank" rel="noopener" href="https://github.com/${esc(cfg.repo)}/issues/new?title=${encodeURIComponent("Hi " + S.me.name)}&body=">✉ Leave a note</a>`;
  } else {
    form = `<form class="note-form" id="note-form"><input name="from" placeholder="Your name" value="${esc(cfg.visitor || "")}">
      <textarea name="text" placeholder="Leave ${name} a note. ${esc(cap(P.he))} reads ${esc(P.his)} mailbox whenever ${esc(P.he)}'s awake." required></textarea>
      <button class="btn" type="submit">✉ Put it in the mailbox</button> <span id="note-msg" class="muted"></span></form>`;
  }
  const notes = [...S.notes].reverse().map((n) => n.outgoing ? `<div class="note letter"><div>✉ <b>A letter from ${name}</b> <span class="muted">${ago(n.at)}</span></div><div>${esc(n.text)}</div></div>` : `<div class="note"><div><b>${esc(n.from)}</b> <span class="muted">${ago(n.at)}</span></div>
    <div>${esc(n.text)}</div>${n.reply ? `<div class="reply"><b>${name}</b> <span class="muted">${ago(n.replied)}</span><div>${esc(n.reply)}</div></div>` : '<div class="muted">Not read yet</div>'}</div>`).join("");
  // Letters you sent from this device that he hasn't picked up yet (he reads them when he wakes).
  const sent = sentNotes().filter((x) => !S.notes.some((n) => !n.outgoing && n.text.trim() === x.text.trim()));
  saveSent(sent);
  const onTheWay = sent.reverse().map((x) => `<div class="note"><div><b>You</b> <span class="muted">${ago(x.at)}</span></div>
    <div>${esc(x.text)}</div><div class="muted">✉ On its way: ${name} reads it when ${esc(P.he)} wakes, usually within a few minutes.</div></div>`).join("");
  const status = { waiting: "⏳ waiting for your answer", granted: "✅ you said yes", declined: "❌ you said no", answered: "💬 you answered" };
  const reqs = [...(S.requests || [])].reverse().map((r) => `<div class="note request"><div>${r.kind === "companion" ? "🏡" : "🙋"} <b>${name} asks: ${esc(r.what)}</b> <span class="muted">${ago(r.asked)}</span></div>
    <div>${esc(r.why)}</div><div class="muted">${status[r.status] || esc(r.status)}${r.answer ? `: “${esc(r.answer)}”` : ""}</div>
    ${r.status === "waiting" && (cfg.mode !== "github" || S.locked) ? `<div class="answer" data-req="${esc(r.id)}"><input placeholder="Your answer (optional)">
      <button class="btn" data-decision="yes">Yes</button> <button class="btn" data-decision="no">No</button> <button class="btn" data-decision="later">Later</button></div>` : ""}
    ${r.status === "waiting" && cfg.mode === "github" && !S.locked && r.ref ? `<a target="_blank" rel="noopener" href="https://github.com/${esc(cfg.repo)}/issues/${r.ref}">Answer on GitHub</a>` : ""}</div>`).join("");
  $("tab-mail").innerHTML = form + (reqs ? "<h3>Things he's asking for</h3>" + reqs : "") + "<h3>Letters</h3>" + ((onTheWay + notes) || '<p class="muted">No letters yet.</p>');
}

function sentNotes() { try { return JSON.parse(localStorage.getItem("aiworld-sent") || "[]"); } catch { return []; } }
function saveSent(list) { try { localStorage.setItem("aiworld-sent", JSON.stringify(list.slice(-20))); } catch {} }

function showTab(name) {
  document.querySelectorAll(".tabs button").forEach((b) => b.classList.toggle("on", b.dataset.tab === name));
  document.querySelectorAll(".tab-body").forEach((d) => (d.hidden = d.id !== "tab-" + name));
}

// ---------- books -----------------------------------------------------------
function inline(s) {
  return s.replace(/`([^`]+)`/g, "<code>$1</code>")
    .replace(/\*\*([^*]+)\*\*/g, "<b>$1</b>")
    .replace(/(^|[^*])\*([^*\s][^*]*)\*/g, "$1<i>$2</i>")
    .replace(/\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g, '<a href="$2" target="_blank" rel="noopener nofollow">$1</a>');
}
function markdown(md) {   // escape everything first; the AI's text never becomes raw HTML
  const out = []; let list = null, code = null, para = [];
  const flush = () => { if (para.length) { out.push(`<p>${inline(para.join(" "))}</p>`); para = []; } if (list) { out.push(`</${list}>`); list = null; } };
  for (const raw of esc(md).split("\n")) {
    if (raw.startsWith("```")) { if (code === null) { flush(); code = []; } else { out.push(`<pre>${code.join("\n")}</pre>`); code = null; } continue; }
    if (code !== null) { code.push(raw); continue; }
    const line = raw.trim(); let m;
    if (!line) { flush(); continue; }
    if ((m = line.match(/^(#{1,4})\s+(.*)/))) { flush(); out.push(`<h${m[1].length}>${inline(m[2])}</h${m[1].length}>`); continue; }
    if ((m = line.match(/^([-*]|\d+\.)\s+(.*)/))) {
      const want = /\d/.test(m[1]) ? "ol" : "ul";
      if (para.length) { out.push(`<p>${inline(para.join(" "))}</p>`); para = []; }
      if (list !== want) { if (list) out.push(`</${list}>`); out.push(`<${want}>`); list = want; }
      out.push(`<li>${inline(m[2])}</li>`); continue;
    }
    if (list) { out.push(`</${list}>`); list = null; }
    para.push(line);
  }
  flush(); if (code) out.push(`<pre>${code.join("\n")}</pre>`);
  return out.join("\n");
}
async function openBook(id) {
  const b = S.shelves.find((x) => x.id === id); if (!b) return;
  let text;
  if (S.locked) text = Vault.text(`books/${id}.md`) ?? "(This book is missing.)";
  else try { const r = await fetch(`world/books/${encodeURIComponent(id)}.md?t=${Date.now()}`); text = r.ok ? await r.text() : "(This book is missing.)"; } catch { text = "(Couldn't open this book.)"; }
  const hasTitle = /^#\s/.test(text.trim());
  $("book-body").innerHTML = (hasTitle ? "" : `<h1>${esc(b.title)}</h1>`) + markdown(text) +
    `<div class="sources"><b>Sources</b> ${!b.sources.length ? "" : b.sources_checked ? "(all read by " + esc(S.me.name) + ")" : "(not all were read in the session that wrote this)"}<ul>${
      b.sources.map((s) => `<li><a href="${esc(s)}" target="_blank" rel="noopener nofollow">${esc(s)}</a></li>`).join("") || "<li>none listed</li>"}</ul>
      <span class="muted">${esc(b.shelf)} · ${b.words} words · written ${when(b.created)}${b.revisions ? ` · revised ${b.revisions}×` : ""}</span></div>`;
  $("book").showModal();
}

// ---------- replay ------------------------------------------------------------
function lastSession() {
  const s = S.recent.length ? S.recent[S.recent.length - 1].session : null;
  return S.recent.filter((e) => e.session === s);
}
function startReplay() {
  if (S.replaying) return stopReplay();
  S.queue = lastSession(); S.replaying = true; S.current = null; S.holdUntil = 0;
  $("replay").textContent = "■ Stop replay"; $("replay").classList.add("stop");
}
function stopReplay() {
  S.queue = []; S.replaying = false; S.current = null; hideBubble();
  $("replay").textContent = "▶ Replay last session"; $("replay").classList.remove("stop"); $("replay-pos").textContent = "";
  const asleep = S.me.state === "asleep";
  walkTo(asleep ? { room: "study", ...STUDY_PLACES.bed } : spotFor({ room: S.me.room, place: S.me.place }), null);
  if (S.comp) walkTo(restSpot(), null, S.bot2);
}
function walkTo(spot, prop, b = S.bot) {
  if (spot.room !== b.room) {   // he walks in through the door of the other room
    b.room = spot.room;
    const entry = spot.room === "study" ? { x: 256, y: 124 } : { x: 6, y: spot.y };
    b.x = entry.x; b.y = entry.y;
    setView(spot.room);
  } else if (S.view !== b.room && (S.replaying || S.current)) setView(b.room);
  Object.assign(b, { tx: spot.x, ty: spot.y, walking: true, pose: "stand", targetPose: spot.pose, prop });
}
function propFor(e) {
  if (e.action === "interact") return /water|spray|feed|pour|fill/.test(e.did || "") ? "can" : e.did === "observe" ? "lens" : "tool";
  return PROPS[e.action] || null;
}
function playNext() {
  const e = S.queue.shift();
  if (!e) { if (S.replaying) stopReplay(); S.current = null; return; }
  S.current = e; S.holdUntil = 0;
  const spot = e.action === "talk" && S.comp ? talkSpot(e) : e.who && S.comp && e.action === "wake" ? { room: "study", x: 256, y: 146, pose: "stand" } : spotFor(e);
  const other = actorOf(e) === S.bot ? S.bot2 : S.bot;   // two can't stand in the same spot
  if (S.comp && e.action !== "talk" && spot.room === other.room && Math.abs(spot.x - other.x) < 12) spot.x += spot.x > 40 ? -20 : 20;
  walkTo(spot, propFor(e), actorOf(e));
  if (S.replaying) { const all = lastSession(); $("replay-pos").textContent = `${all.length - S.queue.length} / ${all.length} · ${when(e.t)}`; }
}
function showBubble(e) {
  const b = $("bubble");
  const why = e.action === "muddled" && e.detail ? e.detail.split(/\n/)[0] : "";   // what went wrong, in his world's own words
  b.innerHTML = (S.comp ? `<b>${esc(whoName(e))}</b>: ` : "") + esc(e.summary) + (why ? `<span class="t">${esc(why.slice(0, 160))}</span>` : "")
    + (e.thought ? `<span class="t">“${esc(e.thought)}”</span>` : "");
  b.hidden = false; placeBubble();
}
function hideBubble() { $("bubble").hidden = true; }
function placeBubble() {
  const b = $("bubble"); if (b.hidden) return;
  const a = actorOf(S.current);
  if (a.room !== S.view) { b.style.visibility = "hidden"; return; }
  b.style.visibility = "";
  const s = canvas.clientWidth / canvas.width;
  const st = $("stage"), lo = st.scrollLeft + b.offsetWidth / 2 + 4, hi = st.scrollLeft + st.clientWidth - b.offsetWidth / 2 - 4;
  const x = Math.min(Math.max(a.x * s, lo), hi);
  b.style.left = x + "px"; b.style.top = Math.max((a.y - 30) * s, b.offsetHeight + 4) + "px";
}

// ---------- drawing ---------------------------------------------------------------
const r = (x, y, w, h, c) => Px.rect(ctx, x, y, w, h, c);

// The study's own furniture. Each piece stands on its anchor; if he has redrawn it, his drawing is used instead.
const STUDY_ANCHORS = {
  bookshelf: [37, 118], wishboard: [90, 66], window: [137, 72], armchair: [132, 132], desk: [202, 125],
  computer: [202, 101], door: [257, 112], mailbox: [282, 88], bed: [275, 164], plant: [304, 116], rug: [160, 170],
};

function drawStudy(t) {
  const W = 320, night = isNight(), room = roomOf("study"), skins = room.skins || {};
  const piece = (name, draw) => {
    const skin = skins[name];
    if (skin) { const [ax, ay] = STUDY_ANCHORS[name]; const { w, h } = Px.art(ctx, skin, skin.pixels, ax, ay); S.boxes.push({ x: ax - w / 2, y: ay - h, w, h, label: name }); }
    else draw();
  };

  if (room.painted || room.wall_tile) drawWall(ctx, room, W);
  else { r(0, 0, W, 118, "#d9b98f"); for (let x = 0; x < W; x += 16) r(x, 0, 1, 118, "#d1af84"); r(0, 112, W, 6, "#9c6b43"); }
  if (room.painted || room.floor_tile) drawFloor(ctx, room, W, 118, H);
  else {
    r(0, 118, W, 62, "#a0714b"); for (let y = 124; y < H; y += 9) r(0, y, W, 1, "#946644");
    for (let x = 0; x < W; x += 40) for (let y = 118; y < H; y += 18) r(x + ((y / 18) % 2) * 20, y, 1, 9, "#946644");
  }
  piece("rug", () => { r(96, 140, 128, 30, "#7a3b3b"); r(100, 143, 120, 24, "#9b4d4a"); r(104, 146, 112, 18, "#b8665c"); });

  piece("window", () => {
    r(110, 20, 54, 50, "#6e4a2d");
    windowView(ctx, 115, 25, 44, 44, t);
    r(136, 25, 2, 44, "#6e4a2d"); r(115, 46, 44, 2, "#6e4a2d"); r(108, 68, 58, 4, "#8a5d3a");
  });

  piece("bookshelf", () => {
    r(6, 22, 62, 96, "#5b3a22"); r(9, 25, 56, 90, "#3d2716");
    for (let row = 0; row < 4; row++) r(9, 45 + row * 22, 56, 3, "#5b3a22");
    const books = [...S.shelves].sort((a, b) => a.created.localeCompare(b.created));
    books.slice(0, 52).forEach((b, i) => {
      const row = Math.floor(i / 13), col = i % 13, h = 14 + (Px.hash(b.id) % 5);
      r(11 + col * 4, 45 + row * 22 - h, 3, h, spineColor(b.shelf));
      r(11 + col * 4, 45 + row * 22 - h + 3, 3, 1, "rgba(255,255,255,.35)");
    });
    if (books.length > 52) for (let i = 0; i < Math.min(books.length - 52, 12); i++) r(70, 116 - i * 3, 12, 2, spineColor(books[52 + i].shelf));
  });

  piece("wishboard", () => {
    r(72, 26, 36, 40, "#7a5230"); r(74, 28, 32, 36, "#c9a06b");
    S.wishes.filter((w) => w.status === "want" || w.status === "learning").slice(0, 9).forEach((w, i) => {
      const x = 76 + (i % 3) * 10, y = 30 + Math.floor(i / 3) * 11;
      r(x, y, 8, 8, ["#f7e27a", "#f5a3b5", "#9fd3f2"][Px.hash(w.id) % 3]); r(x + 1, y + 2, 6, 1, "#00000030"); r(x + 1, y + 4, 4, 1, "#00000030");
      r(x + 3, y - 1, 2, 2, w.status === "learning" ? "#d33" : "#555");
    });
  });

  piece("armchair", () => { r(116, 104, 32, 10, "#4f6e8f"); r(114, 112, 36, 16, "#5b7fa6"); r(112, 108, 6, 22, "#4f6e8f"); r(146, 108, 6, 22, "#4f6e8f"); r(116, 128, 3, 4, "#3a2a1c"); r(145, 128, 3, 4, "#3a2a1c"); });

  piece("desk", () => { r(170, 100, 64, 5, "#7a5230"); r(172, 105, 3, 20, "#5b3a22"); r(229, 105, 3, 20, "#5b3a22"); r(222, 92, 6, 8, "#e9e2d0"); r(223, 90, 4, 2, "#8b5a2b"); });
  piece("computer", () => {
    const busy = S.bot.room === "study" && Math.abs(S.bot.x - STUDY_PLACES.computer.x) < 2 && !S.bot.walking && !powerCut();
    r(186, 74, 32, 24, "#2a2a30"); r(188, 76, 28, 19, busy ? "#173b2a" : "#1b1c24");
    if (busy) for (let i = 0; i < 6; i++) r(190, 78 + i * 3, 6 + ((i * 7 + Math.floor(t / 200)) % 20), 1, "#7df0a5");
    r(199, 98, 6, 2, "#2a2a30"); r(190, 101, 22, 2, "#444");
  });

  piece("door", () => { r(242, 46, 30, 66, "#6e4a2d"); r(245, 49, 24, 63, "#8a5d3a"); r(264, 80, 3, 3, "#e3c15b"); });
  piece("mailbox", () => {
    r(276, 78, 12, 10, "#3d5a80"); r(277, 79, 10, 3, "#2c4466");
    const waiting = S.notes.some((n) => !n.reply);
    r(288, waiting ? 72 : 80, 2, waiting ? 10 : 8, "#d33"); if (waiting) r(285, 72, 3, 3, "#d33");
  });
  piece("plant", () => { r(298, 104, 12, 12, "#b5653a"); r(301, 92, 2, 12, "#3e7a3a"); r(296, 90, 7, 4, "#4f9a49"); r(303, 95, 7, 4, "#4f9a49"); r(300, 86, 5, 4, "#5fae57"); });
  piece("bed", () => { r(236, 136, 78, 28, "#6e4a2d"); r(238, 132, 74, 16, "#e9e2d0"); r(286, 130, 24, 10, "#fdfbf5"); r(238, 140, 50, 20, "#5b7fa6"); r(238, 140, 50, 2, "#7097c4"); });
}

function drawView(t) {
  const room = roomOf(S.view), W = room.width || 320;
  if (canvas.width !== W) canvas.width = W;
  S.boxes = [];
  if (room.builtin) drawStudy(t); else drawBuiltRoom(ctx, room, W, H, t);
  const w = weatherNow();
  if (w && w.env_rain > 0 && room.kind === "outdoor") rain(ctx, W, H, t, w.env_rain);
  const fy = floorY(room);
  [...room.items].sort((a, b) => (a.place === "wall" ? -1 : 1) - (b.place === "wall" ? -1 : 1)).forEach((it) => {
    const box = drawItem(ctx, it, itemX(it, room), fy, 26);
    if (box) S.boxes.push({ ...box, label: it.name });
  });
  const botFront = S.bot.room === room.id && S.bot.y >= 166;
  const compHere = S.comp && S.bot2.room === room.id, compFront = compHere && S.bot2.y >= 166;
  if (compHere && !compFront) drawBot(t, S.bot2);
  if (S.bot.room === room.id && !botFront) drawBot(t);
  liveIn(room.id).forEach((sp) => {
    const box = drawSpecimen(ctx, sp, specimenX(sp), 166, t);
    S.boxes.push({ ...box, label: sp.spec.name, specimen: sp.id });
  });
  if (compFront) drawBot(t, S.bot2);
  if (botFront) drawBot(t);
  lighting(ctx, room, W, H, t, lightsIn(room, fy));
  const h = happening();
  if (room.kind === "outdoor" && h.heat) { ctx.fillStyle = "rgba(255,170,60,.08)"; ctx.fillRect(0, 0, W, H); }
  if (room.kind === "outdoor" && h.cold) { ctx.fillStyle = "rgba(150,190,255,.08)"; ctx.fillRect(0, 0, W, H); }
  if (h.storm && (room.kind === "outdoor" || room.builtin || room.windows)) {   // lightning, now and then
    const f = (t + Px.hash(room.id) * 37) % 9000;
    if (f < 70 || (f > 160 && f < 210)) { ctx.fillStyle = `rgba(235,240,255,${room.kind === "outdoor" ? 0.5 : 0.22})`; ctx.fillRect(0, 0, W, H); }
  }
}

// What gives light at night: the study's computer, and any lamp, candle, fire or screen he put in a room.
const GLOWS = /lamp|light|candle|lantern|fire|torch|neon|glow|screen|tv|computer|monitor|stove|oven/i;
function lightsIn(room, fy) {
  const out = [], cut = powerCut(), flame = /candle|fire|lantern|torch|stove/i;
  if (room.builtin && !cut) {
    const busy = S.bot.room === "study" && !S.bot.walking && Math.abs(S.bot.x - STUDY_PLACES.computer.x) < 2;
    out.push({ x: 202, y: 86, r: busy ? 70 : 34, cool: true });
  }
  for (const it of room.items) {
    if (!GLOWS.test(`${it.name} ${it.preset || ""}`) || (cut && !flame.test(`${it.name} ${it.preset || ""}`))) continue;
    out.push({ x: itemX(it, room), y: it.place === "wall" ? 50 : fy - 22, r: 70, flicker: /candle|fire|lantern|torch/i.test(`${it.name} ${it.preset || ""}`) });
  }
  return out;
}

function drawBot(t, b = S.bot) {
  if (!S.me.name) return;
  const who = b === S.bot2 ? S.comp : S.me;
  drawSprout(ctx, Math.round(b.x), Math.round(b.y), { t, pose: b.walking ? "stand" : b.pose, walking: b.walking, mood: who.mood, prop: b.walking ? null : b.prop,
    look: b === S.bot2 ? compLook(who) : S.me.look });
}

function drawPanels(t) {
  const p = $("portrait");
  if (p && !p.hidden) {
    const g = p.getContext("2d");
    g.clearRect(0, 0, 64, 52);
    Px.ellipse(g, 32, 28, 26, 24, "#e9dfcb"); Px.ellipse(g, 32, 48, 22, 3, "#d4c6ab");
    const asleep = S.me.state === "asleep";
    drawSprout(g, 32, 46, { t, pose: "stand", mood: S.me.mood, closed: asleep, look: S.me.look });
    if (asleep) { g.fillStyle = "#6b6156"; g.font = "7px monospace"; g.fillText("z", 44 + (Math.floor(t / 700) % 3) * 3, 16); }
  }
  const p2 = $("portrait2");
  if (p2 && S.comp && p2.offsetParent) {
    const g = p2.getContext("2d");
    g.clearRect(0, 0, 64, 52);
    Px.ellipse(g, 32, 28, 26, 24, "#efe0c8"); Px.ellipse(g, 32, 48, 22, 3, "#d9c6a6");
    drawSprout(g, 32, 46, { t, pose: "stand", mood: S.comp.mood, closed: S.comp.state === "asleep", look: compLook(S.comp) });
  }
  document.querySelectorAll("canvas.mini").forEach((c) => {
    if (!c.offsetParent) return;
    const sp = S.specimens.find((s) => s.id === c.dataset.spec); if (!sp) return;
    const g = c.getContext("2d");
    g.clearRect(0, 0, 64, 56); Px.rect(g, 0, 44, 64, 12, "#d9cbb0"); Px.rect(g, 0, 0, 64, 44, "#efe6d6");
    drawSpecimen(g, { ...sp, moving: sp.moving }, 32, 52, t);
  });
}

let lastT = performance.now();
function frame(t) {
  const dt = Math.min(0.05, (t - lastT) / 1000); lastT = t;
  for (const b of S.comp ? [S.bot, S.bot2] : [S.bot]) {
    const dx = b.tx - b.x, dy = b.ty - b.y, d = Math.hypot(dx, dy);
    if (d > 0.5) { const step = Math.min(d, 60 * dt); b.x += (dx / d) * step; b.y += (dy / d) * step; b.walking = true; }
    else if (b.walking) {
      b.x = b.tx; b.y = b.ty; b.walking = false; b.pose = b.targetPose || "stand";
      if (S.current && actorOf(S.current) === b) { showBubble(S.current); S.holdUntil = t + Number($("speed").value) * 1000; }
    }
  }
  const b = actorOf(S.current);
  if (S.current && S.holdUntil && t > S.holdUntil) { hideBubble(); S.current = null; S.holdUntil = 0; }
  if (!S.current && S.queue.length && !b.walking) playNext();
  else if (!S.current && !S.queue.length && S.replaying && !b.walking) stopReplay();
  drawView(t); drawPanels(t); followBot(); placeBubble();
  requestAnimationFrame(frame);
}

// ---------- wiring ------------------------------------------------------------------
function roomPoint(ev) { const rc = canvas.getBoundingClientRect(); return { x: (ev.clientX - rc.left) * canvas.width / rc.width, y: (ev.clientY - rc.top) * H / rc.height }; }
function hit(p) {
  const inside = (h) => p.x >= h.x && p.x <= h.x + h.w && p.y >= h.y && p.y <= h.y + h.h;
  return [...S.boxes].reverse().find(inside) || (roomOf(S.view).builtin ? STUDY_HOTSPOTS.find(inside) : null);
}
canvas.addEventListener("mousemove", (ev) => { const h = hit(roomPoint(ev)); canvas.classList.toggle("pointer", !!(h && (h.tab || h.specimen))); canvas.title = h ? h.label : ""; });
canvas.addEventListener("click", (ev) => {
  const h = hit(roomPoint(ev)); if (!h) return;
  $("hint").hidden = true;
  if (h.specimen) { showTab("made"); document.getElementById("card-" + h.specimen)?.scrollIntoView({ behavior: "smooth", block: "nearest" }); return; }
  if (!h.tab) return;
  S.journalFilter = h.filter || null; renderJournal(); showTab(h.tab);
});
$("rooms").addEventListener("click", (ev) => { const bt = ev.target.closest("[data-room]"); if (bt) setView(bt.dataset.room); });
document.querySelector(".tabs").addEventListener("click", (ev) => {
  const t = ev.target.closest("button"); if (!t) return;
  if (t.dataset.tab === "journal") { S.journalFilter = null; renderJournal(); }
  showTab(t.dataset.tab);
});
document.addEventListener("click", (ev) => {
  const book = ev.target.closest("[data-book]"); if (book) return openBook(book.dataset.book);
  const e = ev.target.closest(".ev"); if (e && !e.classList.contains("diary")) e.classList.toggle("open");
  if (ev.target.id === "clear-filter") { ev.preventDefault(); S.journalFilter = null; renderJournal(); }
});
document.addEventListener("click", async (ev) => {
  const b = ev.target.closest("[data-decision]"); if (!b) return;
  const box = b.closest("[data-req]");
  try {
    if (S.locked) {
      await Vault.send(S.cfg.repo, { answer_for: box.dataset.req, text: box.querySelector("input").value,
        decision: { yes: "granted", no: "declined", later: "waiting" }[b.dataset.decision] });
    } else {
      const res = await fetch("api/answer", { method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ id: box.dataset.req, decision: b.dataset.decision, text: box.querySelector("input").value }) });
      if (!res.ok) throw new Error();
    }
    box.innerHTML = `<span class="muted">Answer delivered; ${esc(S.me.name)} will read it when ${esc(P.he)} wakes.</span>`;
  } catch { box.insertAdjacentHTML("beforeend", ' <span class="muted">Couldn’t deliver it (is serve.py running?)</span>'); }
});

document.addEventListener("click", (ev) => {
  const b = ev.target.closest("[data-play]"); if (!b) return;
  const piece = (S.music || []).find((p) => p.id === b.dataset.play); if (!piece) return;
  if (b.textContent === "■") { Music.stop(); b.textContent = "▶"; return; }
  document.querySelectorAll("[data-play]").forEach((x) => (x.textContent = "▶"));
  b.textContent = "■";
  Music.play(piece, () => (b.textContent = "▶"));
});

document.addEventListener("submit", async (ev) => {
  if (ev.target.id !== "note-form") return;
  ev.preventDefault();
  const f = new FormData(ev.target), msg = $("note-msg");
  try {
    if (S.locked) {
      await Vault.send(S.cfg.repo, { from: f.get("from") || "Visitor", text: f.get("text") });
      saveSent([...sentNotes(), { text: String(f.get("text")).trim().slice(0, 2000), at: new Date().toISOString() }]);
      ev.target.reset(); renderMail();
      $("note-msg").textContent = `Sealed and sent. It wakes ${S.me.name} within a few minutes; ${P.his} reply appears under your letter.`;
      return;
    }
    const res = await fetch("api/note", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ from: f.get("from"), text: f.get("text") }) });
    if (!res.ok) throw new Error(await res.text());
    ev.target.reset(); msg.textContent = `Delivered. ${S.me.name} will read it next time ${P.he}'s awake.`;
  } catch (e) { msg.textContent = S.locked ? `Couldn't send it (${e.message}).` : "Couldn't deliver it (is serve.py running?)"; }
});
$("replay").addEventListener("click", startReplay);
$("hear").addEventListener("click", () => {
  if (Ambience.on) { Ambience.stop(); $("hear").textContent = "🔊 Hear his world"; return; }
  // what he hears: the real weather outside, muffled when you're looking at an indoor room
  Ambience.start(() => ({ ...(weatherNow() || {}), outdoors: roomOf(S.view).kind === "outdoor" }));
  $("hear").textContent = "🔇 Quiet";
});
window.addEventListener("resize", placeBubble);

// ---------- starting up: his plain world (on your PC) or the locked one (online) -------------------------
function showLock(message) {
  $("lock").hidden = false;
  $("lock-msg").textContent = message || "";
  $("lock-pw").focus();
  return new Promise((resolve) => { S.unlocked = resolve; });
}
$("lock-form").addEventListener("submit", async (ev) => {
  ev.preventDefault();
  $("lock-msg").textContent = "Unlocking…";
  if (await Vault.unlock($("lock-pw").value, $("lock-remember").checked)) {
    $("lock").hidden = true; $("lock-pw").value = "";
    S.unlocked && S.unlocked();
  } else $("lock-msg").textContent = "That password doesn't open this world.";
});
$("lock-forget").addEventListener("click", () => { Vault.forget(); location.reload(); });

async function start() {
  const plain = await fetch(`world/self.json?t=${Date.now()}`, { cache: "no-store" }).then((r) => r.ok).catch(() => false);
  if (!plain && await Vault.fetchBlob()) {
    S.locked = true;
    $("lock-forget").hidden = false;
    if (!(await Vault.tryRemembered())) await showLock();
  }
  await load(true);
  setView(S.view);
  requestAnimationFrame(frame);
  // online: every 20 s with your token (he can be watched live), otherwise every minute
  setInterval(() => load(false), !S.locked && S.cfg.mode !== "github" ? 4000 : S.locked && Vault.token() ? 20000 : 60000);
}
start();
