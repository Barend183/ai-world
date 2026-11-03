// What he sees, through his own eyes: his world drawn exactly as the web page draws it (the light, the weather,
// his furniture and creations, his companion), then seen from his eye height, close up on whatever he's facing,
// with his own hands (or his blanket, in bed) at the bottom of the view. Never his own face.
// Usage: node scene.js <world folder> [room id] [home|companion] [around] > view.png
"use strict";
const fs = require("fs"), path = require("path"), vm = require("vm");
const { Canvas, png } = require("./canvas.js");

const [dir, roomArg, who = "home", mode = ""] = process.argv.slice(2);
const read = (name, fallback) => { try { return JSON.parse(fs.readFileSync(path.join(dir, name), "utf8")); } catch { return fallback; } };

// The page's code expects a browser; this is just enough of one for it to draw.
const fake = () => new Proxy(function () {}, {
  get: (t, k) => k === Symbol.toPrimitive ? () => "" : k === "value" ? "3.5" : k === "querySelectorAll" ? () => [] : fake(),
  set: () => true, apply: () => fake(),
});
const room = Object.assign(new Canvas(320, 180), { style: {}, addEventListener() {}, classList: { toggle() {} }, clientWidth: 320 });
const sandbox = {
  document: { getElementById: (id) => (id === "room" ? room : fake()), createElement: () => new Canvas(), querySelector: () => fake(),
              querySelectorAll: () => [], addEventListener() {} },
  window: { addEventListener() {} }, performance: { now: () => 0 }, localStorage: { getItem: () => null, setItem() {}, removeItem() {} },
  location: {}, requestAnimationFrame() {}, setInterval() {}, setTimeout() {}, console,
  Math, Date, Set, Map, WeakMap, Array, Number, String, Object, JSON, parseInt, Promise, Proxy, Symbol, encodeURIComponent,
};
vm.createContext(sandbox);
const docs = path.join(__dirname, "..", "docs");
const app = fs.readFileSync(path.join(docs, "app.js"), "utf8").replace(/\nstart\(\);\s*$/, "\n");
vm.runInContext(fs.readFileSync(path.join(docs, "sprites.js"), "utf8") + "\n" + app + `
this.__see = function (input) {
  Object.assign(S, input.state);
  if (input.state.rooms) S.rooms = input.state.rooms;
  S.comp = (input.companions || []).find((c) => c.status === "living") || null;
  const where = (m) => (m.state === "asleep" || !m.room ? { room: "study", ...STUDY_PLACES.bed } : spotFor({ room: m.room, place: m.place }));
  Object.assign(S.bot, where(S.me), { walking: false });
  if (S.comp) Object.assign(S.bot2, restSpot(), { walking: false });
  const eye = input.who === "companion" && S.comp ? S.bot2 : S.bot;
  const view = input.room && S.rooms.some((r) => r.id === input.room) ? input.room : eye.room;
  // looking into another room means stepping into its doorway
  const ex = view === eye.room ? eye.x : 20;
  const plain = drawBot;
  drawBot = (t, b = S.bot) => { if (b !== eye) plain(t, b); };   // nobody sees their own face
  S.view = view;
  canvas.width = roomW(view);
  drawView(1000);
  const self = eye === S.bot2 ? S.comp : S.me, col = (eye === S.bot2 ? compLook(self) : self.look || {}).colors || {};
  return { width: canvas.width, x: ex, feet: view === eye.room ? eye.y : 160, room: view, place: view === eye.room ? self.place : "",
           study: !!roomOf(view).builtin, body: col.body || "#66c28a", night: isNight() };
};
this.__Px = Px;`, sandbox);

const me = read("self.json", {});
const companions = read("companions.json", []);
const seen = sandbox.__see({
  who, room: roomArg || null, companions,
  state: { cfg: read("config.json", {}), me, shelves: read("shelves.json", []), wishes: read("wishlist.json", []),
           notes: read("notes.json", []), recent: read("recent.json", []).slice(-40), specimens: read("specimens.json", []),
           rooms: read("rooms.json", null), weather: read("weather_now.json", null), goals: read("goals.json", []), music: read("music.json", []) },
});

// Where his eyes are and what he's facing. In the study he faces the thing he's using, up close.
const FACING = { computer: [202, 88, 2.6], shelves: [37, 72, 2.2], board: [90, 48, 2.6], mailbox: [280, 84, 2.6] };
let cx = seen.x, cy = seen.feet - 22, zoom = 1.7;
if (mode === "around") zoom = 1.25;
else if (seen.place === "bed") { cx = seen.x - 100; cy = 108; zoom = 1.3; }   // lying in bed, looking out across the room
else if (seen.study && FACING[seen.place]) [cx, cy, zoom] = FACING[seen.place];
const W = seen.width, H = room.height, w = 320 / zoom, h = 180 / zoom;
const left = Math.max(0, Math.min(W - w, cx - w / 2)), top = Math.max(0, Math.min(H - h, cy - h / 2));
const out = new Canvas(320, 180);
out.px = new Float32Array(320 * 180 * 4);
for (let y = 0; y < 180; y++) for (let x = 0; x < 320; x++) {
  const sx = Math.min(W - 1, Math.floor(left + x / zoom)), sy = Math.min(H - 1, Math.floor(top + y / zoom));
  for (let c = 0; c < 4; c++) out.px[(y * 320 + x) * 4 + c] = room.px[(sy * W + sx) * 4 + c];
}

// What's always in front of his eyes: his hands, or the edge of his blanket when he's lying in bed.
const Px = sandbox.__Px, g = out.getContext(), dim = (c) => (seen.night ? Px.shade(c, 0.55) : c);
if (seen.place === "bed" && mode !== "around") {
  Px.rect(g, 0, 150, 320, 30, dim("#5b7fa6")); Px.rect(g, 0, 150, 320, 3, dim("#7097c4"));
  for (let x = 8; x < 320; x += 26) Px.rect(g, x, 158, 12, 1, dim("#4f6e8f"));
} else {
  const typing = seen.study && seen.place === "computer" && mode !== "around";
  const hands = typing ? [[128, 176], [192, 176]] : [[54, 182], [266, 182]];
  for (const [hx, hy] of hands) {
    Px.ellipse(g, hx, hy, 19, 14, dim(Px.shade(seen.body, 0.7)));
    Px.ellipse(g, hx, hy + 1, 17, 12, dim(seen.body));
    Px.ellipse(g, hx - 5, hy - 6, 5, 3, dim(Px.shade(seen.body, 1.3)));
  }
}
process.stdout.write(png(out, 3, "#000000"));
