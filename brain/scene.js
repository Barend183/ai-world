// What he sees, through his own eyes: his world drawn exactly as the web page draws it (the light, the weather,
// his furniture and creations, his companion), from where he stands, without himself in the picture.
// Usage: node scene.js <world folder> [room id] [home|companion] > view.png
"use strict";
const fs = require("fs"), path = require("path"), vm = require("vm");
const { Canvas, png } = require("./canvas.js");

const [dir, roomArg, who = "home"] = process.argv.slice(2);
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
  return { width: canvas.width, x: ex, room: view };
};`, sandbox);

const me = read("self.json", {});
const companions = read("companions.json", []);
const seen = sandbox.__see({
  who, room: roomArg || null, companions,
  state: { cfg: read("config.json", {}), me, shelves: read("shelves.json", []), wishes: read("wishlist.json", []),
           notes: read("notes.json", []), recent: read("recent.json", []).slice(-40), specimens: read("specimens.json", []),
           rooms: read("rooms.json", null), weather: read("weather_now.json", null), goals: read("goals.json", []), music: read("music.json", []) },
});

// His field of view: about 240 pixels wide, centred where he stands (the whole room if it's small).
const FOV = Math.min(240, seen.width), left = Math.max(0, Math.min(seen.width - FOV, Math.round(seen.x - FOV / 2)));
const out = new Canvas(FOV, room.height);
out.px = new Float32Array(FOV * room.height * 4);
for (let y = 0; y < room.height; y++) for (let x = 0; x < FOV; x++)
  for (let c = 0; c < 4; c++) out.px[(y * FOV + x) * 4 + c] = room.px[(y * room.width + x + left) * 4 + c];
process.stdout.write(png(out, 3, "#000000"));
