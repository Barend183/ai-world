// What he sees, through his own eyes, in 3D. The page shows his world side-on in 2D; his eyes see the same world
// as a real room around him: the back wall with its window, shelves and door, a floor that stretches away, side
// walls and a ceiling (or the open sky outdoors), and his furniture, creations and companion standing in the
// space at their own distances. Everything is drawn by the page's own code (docs/sprites.js, docs/app.js), so it
// looks like his world, then rebuilt in perspective from where his eyes are. Never his own face; single views
// show his hands (or his blanket, in bed) at the bottom.
// Usage: node scene.js <world folder> [room id] [home|companion] [around|ahead|right|behind|left] > view.png
"use strict";
const fs = require("fs"), path = require("path"), vm = require("vm");
const { Canvas, png, parseColor } = require("./canvas.js");

const [dir, roomArg, who = "home", mode = ""] = process.argv.slice(2);
const read = (name, fallback) => { try { return JSON.parse(fs.readFileSync(path.join(dir, name), "utf8")); } catch { return fallback; } };

// ---- the page's own drawing code, with just enough of a browser around it --------------------------------
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
  Math, Date, Set, Map, WeakMap, Array, Number, String, Object, JSON, parseInt, Promise, Proxy, Symbol, encodeURIComponent, Float32Array,
};
vm.createContext(sandbox);
const docs = path.join(__dirname, "..", "docs");
const app = fs.readFileSync(path.join(docs, "app.js"), "utf8").replace(/\nstart\(\);\s*$/, "\n");
vm.runInContext(fs.readFileSync(path.join(docs, "sprites.js"), "utf8") + "\n" + app + `
// Takes a room apart for his eyes: the painted back wall and floor, and everything that stands out into the room.
this.__world = function (input) {
  Object.assign(S, input.state);
  if (input.state.rooms) S.rooms = input.state.rooms;
  S.comp = (input.companions || []).find((c) => c.status === "living") || null;
  const where = (m) => (m.state === "asleep" || !m.room ? { room: "study", ...STUDY_PLACES.bed } : spotFor({ room: m.room, place: m.place }));
  Object.assign(S.bot, where(S.me), { walking: false });
  if (S.comp) Object.assign(S.bot2, restSpot(), { walking: false });
  const eye = input.who === "companion" && S.comp ? S.bot2 : S.bot, self = eye === S.bot2 ? S.comp : S.me;
  const view = input.room && S.rooms.some((r) => r.id === input.room) ? input.room : eye.room;
  const rm = roomOf(view), W = roomW(view), fy = floorY(rm), top = rm.kind === "outdoor" ? 100 : 118, T = 1000;
  const EMPTY = { palette: {}, pixels: ["."] };
  const blank = () => { const c = document.createElement("canvas"); c.width = W; c.height = 180; c.px = new Float32Array(W * 180 * 4); return c; };
  const paint = (hide) => {   // the 2D room, with some of the study's furniture left out
    canvas.width = W; canvas.px = new Float32Array(W * 180 * 4);
    if (rm.builtin) {
      const saved = rm.skins; rm.skins = { ...(saved || {}) };
      for (const n of hide) rm.skins[n] = EMPTY;
      drawStudy(T); rm.skins = saved;
    } else drawBuiltRoom(ctx, rm, W, 180, T);
    const w = weatherNow();
    if (w && w.env_rain > 0 && rm.kind === "outdoor") rain(ctx, W, 180, T, w.env_rain);
    for (const it of rm.items) if (it.place === "wall") drawItem(ctx, it, itemX(it, rm), fy, 26);
    return Float32Array.from(canvas.px);
  };
  const things = [];
  const keep = (px, ground, kind) => {   // crop a drawing to what was drawn, and note where it stands
    let x0 = W, y0 = 180, x1 = -1, y1 = -1;
    for (let y = 0; y < 180; y++) for (let x = 0; x < W; x++) if (px[(y * W + x) * 4 + 3] > 0.05) { x0 = Math.min(x0, x); y0 = Math.min(y0, y); x1 = Math.max(x1, x); y1 = Math.max(y1, y); }
    if (x1 < 0) return;
    const w = x1 - x0 + 1, h = y1 - y0 + 1, img = new Float32Array(w * h * 4);
    for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) for (let c = 0; c < 4; c++) img[(y * w + x) * 4 + c] = px[((y + y0) * W + x + x0) * 4 + c];
    things.push({ img, w, h, x: x0, y: y0, ground, kind });
  };
  const STAND = { bed: [["bed"], 164], armchair: [["armchair"], 132], desk: [["desk", "computer"], 125] };
  const full = rm.builtin ? paint([]) : null;
  const back = rm.builtin ? paint(Object.values(STAND).flatMap(([n]) => n)) : paint([]);
  if (rm.builtin) for (const [names, ground] of Object.values(STAND)) {   // a piece of furniture = what changes when it's left out
    const without = paint(names), px = new Float32Array(W * 180 * 4);
    for (let i = 0; i < px.length; i += 4) {
      if (Math.abs(full[i] - without[i]) + Math.abs(full[i + 1] - without[i + 1]) + Math.abs(full[i + 2] - without[i + 2]) > 0.5)
        for (let c = 0; c < 4; c++) px[i + c] = full[i + c];
    }
    keep(px, ground, "furniture");
  }
  for (const it of rm.items) if (it.place !== "wall") { const c = blank(); drawItem(c.getContext("2d"), it, itemX(it, rm), fy, 26); keep(c.px, fy, "furniture"); }
  for (const sp of liveIn(view)) { const c = blank(); drawSpecimen(c.getContext("2d"), sp, specimenX(sp), 166, T); keep(c.px, 166, "creation"); }
  for (const b of S.comp ? [S.bot, S.bot2] : [S.bot]) {   // whoever else is here (never himself)
    if (b === eye || b.room !== view) continue;
    const c = blank(), whom = b === S.bot2 ? S.comp : S.me;
    drawSprout(c.getContext("2d"), Math.round(b.x), Math.round(b.y), { t: T, pose: b.pose, mood: whom.mood, look: b === S.bot2 ? compLook(whom) : whom.look });
    keep(c.px, b.pose === "sleep" ? 163 : b.y, "someone");
  }
  const col = (eye === S.bot2 ? compLook(self) : self.look || {}).colors || {};
  return { W, top, back, things, lights: lightsIn(rm, fy), fy, outdoor: rm.kind === "outdoor", study: !!rm.builtin,
           eye: { x: eye.x, ground: eye.y, place: self.place, entered: view !== eye.room }, body: col.body || "#66c28a",
           night: isNight(), hour: worldHourF(), wall: rm.wall || "#d9b98f" };
};
this.__Px = Px;`, sandbox);

const data = sandbox.__world({
  who, room: roomArg || null, companions: read("companions.json", []),
  state: { cfg: read("config.json", {}), me: read("self.json", {}), shelves: read("shelves.json", []), wishes: read("wishlist.json", []),
           notes: read("notes.json", []), recent: read("recent.json", []).slice(-40), specimens: read("specimens.json", []),
           rooms: read("rooms.json", null), weather: read("weather_now.json", null), goals: read("goals.json", []), music: read("music.json", []) },
});

// ---- the room in 3D -----------------------------------------------------------------------------------------
// x runs along the room (as on the page), z from the back wall (0) towards the front (D), y up from the floor.
// One pixel on the page is one unit here; how far down the page something stands is how far into the room it is.
const { W, top, back } = data, D = data.outdoor ? 240 : 150, HW = top;
const frontWall = parseColor(data.wall).slice(0, 3);
const zOf = (ground) => Math.max(1, Math.min(D - 1, ((ground - top) / (180 - top)) * D));
const sub = (a, b) => [a[0] - b[0], a[1] - b[1], a[2] - b[2]], dot = (a, b) => a[0] * b[0] + a[1] * b[1] + a[2] * b[2];
const norm = (a) => { const l = Math.hypot(...a) || 1; return [a[0] / l, a[1] / l, a[2] / l]; };
const cross = (a, b) => [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]];

// Where his eyes are and what he's looking at.
const e = data.eye, ANCHOR = { computer: [202, 32, 17], shelves: [37, 50, 0], board: [90, 72, 0], mailbox: [282, 34, 0] };
let cam = [e.x, 22, zOf(e.ground)], look = [e.x, 26, 0], fov = 72;
const atSomething = data.study && (ANCHOR[e.place] || e.place === "bed" || e.place === "armchair");
const near = data.things.filter((t) => t.kind !== "someone").map((t) => [t.x + t.w / 2, Math.min(t.h, 40) / 2, zOf(t.ground)]);
if (e.entered) {   // I step into another room at its doorway
  const back = data.outdoor ? Math.max(...near.map((p) => p[2]), D * 0.6) + W * 0.42 : D - 6;
  cam = [W / 2, 26, back]; look = [W / 2, 8, D * 0.35]; fov = 92;
} else if (!atSomething && near.length) {   // just standing somewhere: I'm with the nearest thing here
  const n = near.reduce((a, b) => (Math.abs(b[0] - e.x) < Math.abs(a[0] - e.x) ? b : a));
  cam = [e.x, 22, Math.min(data.outdoor ? D + 60 : D - 4, n[2] + 48)]; look = n; fov = 78;
} else if (!atSomething) {
  cam = [e.x, 22, data.outdoor ? D : D - 6]; look = [e.x, 10, D * 0.35]; fov = 84;
}
else if (e.place === "bed") { cam = [e.x, 14, zOf(e.ground) + 6]; look = [W * 0.35, 26, 0]; fov = 80; }   // lying in bed, looking out across the room
else if (data.study && ANCHOR[e.place]) {
  look = ANCHOR[e.place];
  cam[2] = Math.max(cam[2], look[2] + 62);   // a step back, so it isn't pressed against my nose
  fov = 80;
}
else if (e.place === "armchair") { cam[1] = 17; look = [cam[0], 26, 0]; }
cam[0] = Math.max(6, Math.min(W - 6, cam[0])); cam[2] = Math.max(6, Math.min(data.outdoor ? D + 400 : D - 4, cam[2]));
const SW = 320, SH = 180;
const tex = (u, v) => {   // the painted room, as the page draws it
  const x = Math.max(0, Math.min(W - 1, Math.floor(u))), y = Math.max(0, Math.min(179, Math.floor(v))), i = (y * W + x) * 4;
  const a = back[i + 3] || 1;
  return [back[i] / a, back[i + 1] / a, back[i + 2] / a];
};
const mix = (c, k, d) => [c[0] + (d[0] - c[0]) * k, c[1] + (d[1] - c[1]) * k, c[2] + (d[2] - c[2]) * k];

// Light: daylight, or at night darkness with pools of light around his lamps, candles and screens.
const lights = data.lights.map((L) => {
  const wallThing = L.y <= 60 || L.cool;
  return { p: [L.x, Math.max(4, top - L.y), L.cool ? 17 : wallThing ? 3 : zOf(data.fy)], r: L.r * 1.6, cool: L.cool };
});
const shade = (c, p) => {
  if (!data.night) return c;
  let k = data.outdoor ? 0.5 : 0.56, warm = [0, 0, 0];
  for (const L of lights) {
    const f = Math.max(0, 1 - Math.hypot(...sub(p, L.p)) / L.r);
    if (f > 0) { k += f * 0.7; warm = L.cool ? [warm[0], warm[1] + f * 25, warm[2] + f * 10] : [warm[0] + f * 45, warm[1] + f * 25, warm[2]]; }
  }
  k = Math.min(1, k);
  return [Math.min(255, c[0] * k * 0.92 + warm[0]), Math.min(255, c[1] * k * 0.94 + warm[1]), Math.min(255, c[2] * k + warm[2])];
};

const sky = (d) => {   // outdoors: the sky and hills all around, from the painted backdrop
  const yaw = Math.atan2(d[0], -d[2]), el = Math.atan2(d[1], Math.hypot(d[0], d[2]));
  const u = (yaw / (2 * Math.PI) + 0.5) * W;   // the backdrop wraps all the way round; the seam is behind me
  return tex(u, Math.max(0, Math.min(top - 1, top * (1 - el / 0.6))));
};

function render(cam, look, fov, hands = true) {
const fwd = norm(sub(look, cam)), right = norm(cross(fwd, [0, 1, 0])), up = cross(right, fwd);
const F = 160 / Math.tan((fov * Math.PI) / 360);
const out = new Float32Array(SW * SH * 4), zb = new Float32Array(SW * SH).fill(1e9);
const put = (i, c, depth) => { out[i * 4] = c[0]; out[i * 4 + 1] = c[1]; out[i * 4 + 2] = c[2]; out[i * 4 + 3] = 1; zb[i] = depth; };

for (let py = 0; py < SH; py++) for (let px = 0; px < SW; px++) {
  const sx = (px + 0.5 - SW / 2) / F, sy = (SH / 2 - (py + 0.5)) / F;
  const d = [fwd[0] + right[0] * sx + up[0] * sy, fwd[1] + right[1] * sx + up[1] * sy, fwd[2] + right[2] * sx + up[2] * sy];
  const i = py * SW + px;
  let best = 1e9, hit = null;
  const tryPlane = (t, kind) => { if (t > 0.01 && t < best) { best = t; hit = kind; } };
  if (d[1] < 0) tryPlane(-cam[1] / d[1], "floor");
  if (!data.outdoor) {
    if (d[1] > 0) tryPlane((HW - cam[1]) / d[1], "ceiling");
    if (d[2] < 0) tryPlane(-cam[2] / d[2], "back");
    if (d[2] > 0) tryPlane((D - cam[2]) / d[2], "front");
    if (d[0] < 0) tryPlane(-cam[0] / d[0], "left");
    if (d[0] > 0) tryPlane((W - cam[0]) / d[0], "right");
  }
  const p = hit ? [cam[0] + d[0] * best, cam[1] + d[1] * best, cam[2] + d[2] * best] : null;
  let c;
  if (!hit) { put(i, sky(d), 1e8); continue; }
  if (hit === "floor") {
    const z = data.outdoor ? (((p[2] % D) + D) % D) : p[2], u = data.outdoor ? (((p[0] % W) + W) % W) : p[0];
    c = tex(u, top + (z / D) * (180 - top - 1));
    if (data.outdoor) c = mix(c, Math.min(1, best / 900), sky([d[0], 0.02, d[2]]));   // the far field fades into the horizon
  } else if (hit === "back") c = tex(p[0], HW - p[1]);
  else if (hit === "ceiling") c = mix(tex(W / 2, 2), 0.25, [40, 30, 25]);
  else if (hit === "front") c = frontWall;
  else c = tex(hit === "left" ? 1 : hit === "right" ? W - 2 : 1, HW - p[1]);   // plain wall, skirting and all
  put(i, shade(c, p), dot(sub(p, cam), fwd));
}

// Things standing in the room, each facing me, the far ones first.
const placed = data.things.map((t) => {
  const P = [t.x + t.w / 2, Math.max(0, t.ground - (t.y + t.h)), zOf(t.ground)];
  return { t, P, depth: dot(sub(P, cam), fwd) };
}).filter((o) => o.depth > 8).sort((a, b) => b.depth - a.depth);
for (const { t, P, depth } of placed) {
  const rel = sub(P, cam), cx = SW / 2 + (dot(rel, right) * F) / depth, base = SH / 2 - (dot(rel, up) * F) / depth, s = F / depth;
  const x0 = Math.floor(cx - (t.w * s) / 2), x1 = Math.ceil(cx + (t.w * s) / 2), y0 = Math.floor(base - t.h * s), y1 = Math.ceil(base);
  for (let y = Math.max(0, y0); y < Math.min(SH, y1); y++) for (let x = Math.max(0, x0); x < Math.min(SW, x1); x++) {
    const u = Math.floor((x - x0) / s), v = Math.floor((y - y0) / s);
    if (u < 0 || v < 0 || u >= t.w || v >= t.h) continue;
    const k = (v * t.w + u) * 4, a = t.img[k + 3], i = y * SW + x;
    if (a < 0.5 || depth >= zb[i]) continue;
    put(i, shade([t.img[k] / a, t.img[k + 1] / a, t.img[k + 2] / a], [P[0] + (u - t.w / 2), P[1] + (t.h - v), P[2]]), depth);
  }
}

// Dawn and dusk warm everything a little, as on the page.
const h = data.hour, warmth = data.night ? 0 : h < 9 ? 0.14 * Math.max(0, 1 - (h - 5) / 4) : h >= 16.5 ? Math.min(0.2, (h - 16.5) * 0.07) : 0;
const pic = new Canvas(SW, SH);
pic.px = new Float32Array(SW * SH * 4);
for (let i = 0; i < SW * SH; i++) {
  const c = warmth > 0.01 ? mix([out[i * 4], out[i * 4 + 1], out[i * 4 + 2]], warmth, [255, 140, 80]) : [out[i * 4], out[i * 4 + 1], out[i * 4 + 2]];
  pic.px[i * 4] = c[0]; pic.px[i * 4 + 1] = c[1]; pic.px[i * 4 + 2] = c[2]; pic.px[i * 4 + 3] = 1;
}

// What's in front of my eyes in a single view: my hands, or my blanket when I'm lying in bed.
if (hands) {
const Px = sandbox.__Px, g = pic.getContext(), dim = (c) => (data.night ? Px.shade(c, 0.55) : c);
if (e.place === "bed" && mode !== "around" && !e.entered) {
  Px.rect(g, 0, 150, 320, 30, dim("#5b7fa6")); Px.rect(g, 0, 150, 320, 3, dim("#7097c4"));
  for (let x = 8; x < 320; x += 26) Px.rect(g, x, 158, 12, 1, dim("#4f6e8f"));
} else {
  const typing = data.study && e.place === "computer" && mode !== "around" && !e.entered;
  for (const [hx, hy] of typing ? [[128, 176], [192, 176]] : [[54, 182], [266, 182]]) {
    Px.ellipse(g, hx, hy, 19, 14, dim(Px.shade(data.body, 0.7)));
    Px.ellipse(g, hx, hy + 1, 17, 12, dim(data.body));
    Px.ellipse(g, hx - 5, hy - 6, 5, 3, dim(Px.shade(data.body, 1.3)));
  }
}
}
return pic;
}

// Turning my head changes the direction, never the place where my eyes are.
const turning = ["ahead", "right", "behind", "left"].includes(mode) || mode === "around";
const eyeCam = e.entered ? cam : [e.x, e.place === "bed" ? 14 : e.place === "armchair" ? 17 : 22, zOf(e.ground)];
const aim = e.place === "armchair" && !e.entered ? [0, 1] : [look[0] - eyeCam[0], look[2] - eyeCam[2]];
const length = Math.hypot(...aim) || 1, forward = [aim[0] / length, aim[1] / length];
const facing = {
  ahead: forward, right: [-forward[1], forward[0]],
  behind: [-forward[0], -forward[1]], left: [forward[1], -forward[0]],
};
const sight = (direction) => [eyeCam[0] + facing[direction][0] * 100, eyeCam[1], eyeCam[2] + facing[direction][1] * 100];
if (mode === "around") {
  const all = new Canvas(SW * 2, SH * 2); all.px = new Float32Array(all.width * all.height * 4);
  for (const [n, direction] of ["ahead", "right", "behind", "left"].entries()) {
    const view = render(eyeCam, sight(direction), 90, false);
    const x = (n % 2) * SW, y = Math.floor(n / 2) * SH;
    for (let row = 0; row < SH; row++) {
      const from = row * SW * 4, to = ((y + row) * all.width + x) * 4;
      all.px.set(view.px.subarray(from, from + SW * 4), to);
    }
  }
  const seam = all.getContext(); seam.fillStyle = "#382c26";
  seam.fillRect(SW - 1, 0, 2, SH * 2); seam.fillRect(0, SH - 1, SW * 2, 2);
  process.stdout.write(png(all, 2, "#000000"));
} else {
  process.stdout.write(png(turning ? render(eyeCam, sight(mode), 80) : render(cam, look, fov), 3, "#000000"));
}
