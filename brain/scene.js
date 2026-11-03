// What he sees, through his own eyes, in 3D. The page shows his world side-on in 2D; his eyes see the same world
// as a real room around him: the back wall with its window, shelves and door, a floor that stretches away, side
// walls and a ceiling (or the open sky outdoors), and his furniture, creations and companion standing in the
// space at their own distances. Everything is drawn by the page's own code (docs/sprites.js, docs/app.js), so it
// looks like his world, then rebuilt in perspective from where his eyes are. Never his own face; single views
// show his hands (or his blanket, in bed) at the bottom.
// Usage: node scene.js <world folder> [room id] [home|companion] [ahead|right|behind|left] [up|level|down] > view.png
"use strict";
const fs = require("fs"), path = require("path"), vm = require("vm");
const { Canvas, png, parseColor } = require("./canvas.js");

const [dir, roomArg, who = "home", mode = "", tiltMode = "level"] = process.argv.slice(2);
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
  const keep = (px, ground, kind, name) => {   // crop a drawing to what was drawn, and note where it stands
    let x0 = W, y0 = 180, x1 = -1, y1 = -1;
    for (let y = 0; y < 180; y++) for (let x = 0; x < W; x++) if (px[(y * W + x) * 4 + 3] > 0.05) { x0 = Math.min(x0, x); y0 = Math.min(y0, y); x1 = Math.max(x1, x); y1 = Math.max(y1, y); }
    if (x1 < 0) return;
    const w = x1 - x0 + 1, h = y1 - y0 + 1, img = new Float32Array(w * h * 4);
    for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) for (let c = 0; c < 4; c++) img[(y * w + x) * 4 + c] = px[((y + y0) * W + x + x0) * 4 + c];
    things.push({ img, w, h, x: x0, y: y0, ground, kind, name });
  };
  const STAND = { bed: [["bed"], 164], armchair: [["armchair"], 132], desk: [["desk"], 125], computer: [["computer"], 125] };
  const chairModel = !!rm.builtin && !rm.skins?.armchair;
  const full = rm.builtin ? paint([]) : null;
  const back = rm.builtin ? paint(Object.values(STAND).flatMap(([n]) => n)) : paint([]);
  if (rm.builtin) for (const [name, [names, ground]] of Object.entries(STAND)) {   // a piece of furniture = what changes when it's left out
    const without = paint(names), px = new Float32Array(W * 180 * 4);
    for (let i = 0; i < px.length; i += 4) {
      if (Math.abs(full[i] - without[i]) + Math.abs(full[i + 1] - without[i + 1]) + Math.abs(full[i + 2] - without[i + 2]) > 0.5)
        for (let c = 0; c < 4; c++) px[i + c] = full[i + c];
    }
    if (name !== "armchair" || !chairModel) keep(px, ground, "furniture", name);
  }
  for (const it of rm.items) if (it.place !== "wall") { const c = blank(); drawItem(c.getContext("2d"), it, itemX(it, rm), fy, 26); keep(c.px, fy, "furniture", it.name); }
  for (const sp of liveIn(view)) { const c = blank(); drawSpecimen(c.getContext("2d"), sp, specimenX(sp), 166, T); keep(c.px, 166, "creation", sp.spec.name); }
  for (const b of S.comp ? [S.bot, S.bot2] : [S.bot]) {   // whoever else is here (never himself)
    if (b === eye || b.room !== view) continue;
    const c = blank(), whom = b === S.bot2 ? S.comp : S.me;
    drawSprout(c.getContext("2d"), Math.round(b.x), Math.round(b.y), { t: T, pose: b.pose, mood: whom.mood, look: b === S.bot2 ? compLook(whom) : whom.look });
    keep(c.px, b.pose === "sleep" ? 163 : b.y, "someone", whom.name);
  }
  const col = (eye === S.bot2 ? compLook(self) : self.look || {}).colors || {};
  const entered = view !== eye.room, whereEyes = entered ? spotFor({ room: view, place: "room" }) : eye;
  return { W, top, back, things, chairModel, lights: lightsIn(rm, fy), fy, outdoor: rm.kind === "outdoor", study: !!rm.builtin,
           eye: { x: whereEyes.x, ground: whereEyes.y, place: self.place, entered }, body: col.body || "#66c28a",
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

// His eyes stay where the page places him after each action.
const e = data.eye;
const atComputer = data.study && !e.entered && e.place === "computer";
const eyeCam = [Math.max(6, Math.min(W - 6, e.x)), e.entered ? 22 : e.place === "bed" ? 14 : e.place === "armchair" ? 17 : atComputer ? 36 : 22,
                zOf(e.ground) + (atComputer ? 28 : 0)];
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

// The page's pixel art has a fixed front and a little depth here, instead of turning to face me.
const solids = data.things.filter((t) => !(data.study && !e.entered && t.kind === "furniture" && t.name === e.place
    && (e.place === "bed" || e.place === "armchair"))).map((t) => {
  const depth = t.kind === "furniture"
    ? ({ bed: 42, armchair: 24, desk: 28, computer: 4 }[t.name] || Math.min(20, Math.max(5, t.w * 0.3)))
    : t.kind === "creation" ? 8 : 6;
  const z = Math.max(depth / 2 + 1, Math.min(D - depth / 2 - 1, zOf(t.ground)));
  const rows = [];
  for (let y = 0; y < t.h; y++) {
    let run = 0, widest = 0, count = 0;
    const back = [0, 0, 0];
    for (let x = 0; x < t.w; x++) {
      const k = (y * t.w + x) * 4, a = t.img[k + 3];
      run = a >= 0.5 ? run + 1 : 0;
      widest = Math.max(widest, run);
      if (a >= 0.5) { for (let c = 0; c < 3; c++) back[c] += t.img[k + c] / a; count++; }
    }
    const thick = Math.max(2, depth * Math.sqrt(widest / t.w));
    rows.push({ z0: Math.max(1, z - thick / 2), z1: Math.min(D - 1, z + thick / 2),
                back: t.name === "computer" ? [42, 42, 48] : back.map((c) => c / (count || 1)) });
  }
  const y0 = Math.max(0, t.ground - t.y - t.h);
  return { t, x0: t.x, x1: t.x + t.w, y0, y1: y0 + t.h,
           z0: Math.max(1, z - depth / 2), z1: Math.min(D - 1, z + depth / 2), rows };
});
// The study chair has a back, seat, arms and feet at different depths; a single extruded sprite hides them.
const chairZ = zOf(132);
const chairBoxes = data.chairModel && (e.entered || e.place !== "armchair") ? [
  [116, 148, 13, 27, -13, -7, "#4f6e8f"], [118, 146, 27, 29, -12, -7, "#4f6e8f"],
  [115, 149, 7, 11, -9, 14, "#456687"], [117, 147, 11, 15, -8, 15, "#5b7fa6"],
  [112, 118, 8, 20, -8, 16, "#4f6e8f"], [146, 152, 8, 20, -8, 16, "#4f6e8f"],
  [113, 118, 20, 22, -6, 16, "#5b7fa6"], [146, 151, 20, 22, -6, 16, "#5b7fa6"],
  [116, 120, 0, 7, -8, -4, "#3a2a1c"], [144, 148, 0, 7, -8, -4, "#3a2a1c"],
  [116, 120, 0, 7, 12, 16, "#3a2a1c"], [144, 148, 0, 7, 12, 16, "#3a2a1c"],
].map(([x0, x1, y0, y1, z0, z1, color]) => ({ x0, x1, y0, y1, z0: chairZ + z0, z1: chairZ + z1,
                                                       c: parseColor(color).slice(0, 3) })) : [];
const traceBox = (o, cam, d, limit) => {
  let enter = 0.01, leave = limit, face = "front";
  for (let axis = 0; axis < 3; axis++) {
    const lo = axis === 0 ? o.x0 : axis === 1 ? o.y0 : o.z0;
    const hi = axis === 0 ? o.x1 : axis === 1 ? o.y1 : o.z1;
    if (Math.abs(d[axis]) < 1e-8) { if (cam[axis] < lo || cam[axis] > hi) return null; continue; }
    const a = (lo - cam[axis]) / d[axis], b = (hi - cam[axis]) / d[axis];
    const near = Math.min(a, b), far = Math.max(a, b);
    if (near > enter) {
      enter = near;
      face = axis === 0 ? (d[0] > 0 ? "left" : "right") : axis === 1 ? (d[1] > 0 ? "bottom" : "top") : d[2] > 0 ? "back" : "front";
    }
    leave = Math.min(leave, far);
    if (leave <= enter) return null;
  }
  return { t: enter, p: [cam[0] + d[0] * enter, cam[1] + d[1] * enter, cam[2] + d[2] * enter], face, c: o.c };
};
const traceSolid = (o, cam, d, limit) => {
  let enter = 0.01, leave = limit, face = "front";
  for (let axis = 0; axis < 3; axis++) {
    const lo = axis === 0 ? o.x0 : axis === 1 ? o.y0 : o.z0;
    const hi = axis === 0 ? o.x1 : axis === 1 ? o.y1 : o.z1;
    if (Math.abs(d[axis]) < 1e-8) { if (cam[axis] < lo || cam[axis] > hi) return null; continue; }
    const a = (lo - cam[axis]) / d[axis], b = (hi - cam[axis]) / d[axis];
    const near = Math.min(a, b), far = Math.max(a, b);
    if (near > enter) {
      enter = near;
      face = axis === 0 ? (d[0] > 0 ? "left" : "right") : axis === 1 ? (d[1] > 0 ? "bottom" : "top") : d[2] > 0 ? "back" : "front";
    }
    leave = Math.min(leave, far);
    if (leave <= enter) return null;
  }
  let t = enter;
  for (let step = 0; step < 2 * (o.t.w + o.t.h) + 8 && t < leave; step++) {
    const p = [cam[0] + d[0] * (t + 1e-5), cam[1] + d[1] * (t + 1e-5), cam[2] + d[2] * (t + 1e-5)];
    const u = Math.floor(p[0] - o.x0), v = Math.floor(o.y1 - p[1]);
    if (u < 0 || u >= o.t.w || v < 0 || v >= o.t.h) break;
    const k = (v * o.t.w + u) * 4, a = o.t.img[k + 3], row = o.rows[v];
    if (a >= 0.5 && p[2] >= row.z0 && p[2] <= row.z1)
      return { t, p, face, c: face === "back" ? row.back : [o.t.img[k] / a, o.t.img[k + 1] / a, o.t.img[k + 2] / a] };
    const xEdge = o.x0 + u + (d[0] > 0 ? 1 : 0);
    const yEdge = o.y1 - v - (d[1] < 0 ? 1 : 0);
    const tx = Math.abs(d[0]) < 1e-8 ? Infinity : (xEdge - cam[0]) / d[0];
    const ty = Math.abs(d[1]) < 1e-8 ? Infinity : (yEdge - cam[1]) / d[1];
    const zEdge = a < 0.5 ? null : p[2] < row.z0 && d[2] > 0 ? row.z0 : p[2] > row.z1 && d[2] < 0 ? row.z1 : null;
    const tz = zEdge == null ? Infinity : (zEdge - cam[2]) / d[2];
    const prev = t;
    if (tx <= ty && tx <= tz) { t = tx; face = d[0] > 0 ? "left" : "right"; }
    else if (ty <= tz) { t = ty; face = d[1] > 0 ? "bottom" : "top"; }
    else { t = tz; face = d[2] > 0 ? "back" : "front"; }
    if (t <= prev + 1e-8) break;
  }
  return null;
};

function render(cam, look, fov) {
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
  if (!hit) put(i, sky(d), 1e8);
  else {
    let c;
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
  for (const o of solids) {
    const h = traceSolid(o, cam, d, zb[i]);
    if (!h) continue;
    const k = { front: 1, back: 0.55, left: 0.72, right: 0.78, top: 1.1, bottom: 0.5 }[h.face];
    put(i, shade(h.c.map((v) => Math.min(255, v * k)), h.p), h.t);
  }
  for (const o of chairBoxes) {
    const h = traceBox(o, cam, d, zb[i]);
    if (!h) continue;
    const k = { front: 1, back: 0.7, left: 0.8, right: 0.85, top: 1.2, bottom: 0.55 }[h.face];
    put(i, shade(h.c.map((v) => Math.min(255, v * k)), h.p), h.t);
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

// What's in front of my eyes: my hands, or my blanket when I'm lying in bed.
const Px = sandbox.__Px, g = pic.getContext(), dim = (c) => (data.night ? Px.shade(c, 0.55) : c);
if (e.place === "bed" && !e.entered) {
  Px.rect(g, 0, 150, 320, 30, dim("#5b7fa6")); Px.rect(g, 0, 150, 320, 3, dim("#7097c4"));
  for (let x = 8; x < 320; x += 26) Px.rect(g, x, 158, 12, 1, dim("#4f6e8f"));
} else {
  const typing = data.study && e.place === "computer" && !e.entered;
  for (const [hx, hy] of typing ? [[128, 176], [192, 176]] : [[54, 182], [266, 182]]) {
    Px.ellipse(g, hx, hy, 19, 14, dim(Px.shade(data.body, 0.7)));
    Px.ellipse(g, hx, hy + 1, 17, 12, dim(data.body));
    Px.ellipse(g, hx - 5, hy - 6, 5, 3, dim(Px.shade(data.body, 1.3)));
  }
}
return pic;
}

// Turning my head or lifting my gaze changes the view, never the place where my eyes are.
const facing = {
  ahead: [0, -1], right: [1, 0], behind: [0, 1], left: [-1, 0],
};
const pitch = { up: 20, level: 0, down: -20 }[tiltMode] || 0;
const sight = (direction) => [eyeCam[0] + facing[direction][0] * 100,
                             eyeCam[1] + Math.tan(pitch * Math.PI / 180) * 100,
                             eyeCam[2] + facing[direction][1] * 100];
const direction = facing[mode] ? mode : "ahead";
process.stdout.write(png(render(eyeCam, sight(direction), 80), 3, "#000000"));
