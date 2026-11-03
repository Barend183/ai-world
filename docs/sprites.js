"use strict";
// Pixel drawing for Sprout, the things he brings to life, furniture and the rooms he builds.
// Every function takes the canvas context to draw on, so the same drawings appear in the room,
// on his portrait and on the cards in the side panel.

const Px = {
  rect(g, x, y, w, h, c) { g.fillStyle = c; g.fillRect(Math.round(x), Math.round(y), Math.max(1, Math.round(w)), Math.max(1, Math.round(h))); },
  ellipse(g, cx, cy, rx, ry, c, topOnly) {
    for (let dy = -Math.round(ry); dy <= (topOnly ? 0 : Math.round(ry)); dy++) {
      const hw = rx * Math.sqrt(Math.max(0, 1 - (dy / ry) ** 2));
      if (hw >= 0.5) Px.rect(g, cx - hw, cy + dy, hw * 2, 1, c);
    }
  },
  shade(hex, f) {   // f < 1 darkens, f > 1 lightens
    const n = parseInt(hex.slice(1), 16), ch = [n >> 16, (n >> 8) & 255, n & 255];
    const m = (v) => Math.max(0, Math.min(255, Math.round(f >= 1 ? v + (255 - v) * (f - 1) : v * f)));
    return "#" + ch.map((v) => m(v).toString(16).padStart(2, "0")).join("");
  },
  grey(hex) {
    const n = parseInt(hex.slice(1), 16), l = Math.round(((n >> 16) * 0.3 + ((n >> 8) & 255) * 0.59 + (n & 255) * 0.11) * 0.8);
    return "#" + [l, l, l].map((v) => v.toString(16).padStart(2, "0")).join("");
  },
  hash(text) { let h = 0; for (const c of String(text)) h = (h * 31 + c.charCodeAt(0)) >>> 0; return h; },
  // Pixel art the AI drew: rows of palette letters, anchored bottom-centre on (x, y), optionally scaled.
  // Each drawing is painted once onto a small canvas and reused every frame.
  art(g, sprite, rows, x, y, grey, scale = 1) {
    const c = Px.bake(sprite, rows, grey, scale);
    g.drawImage(c, Math.round(x - c.width / 2), Math.round(y - c.height));
    return { w: c.width, h: c.height };
  },
  bake(sprite, rows, grey, scale = 1) {
    let byRows = Px._cache.get(rows);
    if (!byRows) Px._cache.set(rows, (byRows = new Map()));
    const key = `${grey ? 1 : 0}|${scale.toFixed(2)}`;
    if (byRows.has(key)) return byRows.get(key);
    const w0 = Math.max(...rows.map((r) => r.length)), h0 = rows.length;
    const c = document.createElement("canvas");
    c.width = Math.max(1, Math.round(w0 * scale)); c.height = Math.max(1, Math.round(h0 * scale));
    const cg = c.getContext("2d");
    rows.forEach((row, j) => [...row].forEach((ch, i) => {
      const col = sprite.palette[ch];
      if (!col) return;
      const x0 = Math.floor(i * scale), y0 = Math.floor(j * scale), x1 = Math.floor((i + 1) * scale), y1 = Math.floor((j + 1) * scale);
      if (x1 > x0 && y1 > y0) Px.rect(cg, x0, y0, x1 - x0, y1 - y0, grey ? Px.grey(col) : col);
    }));
    byRows.set(key, c);
    return c;
  },
  _cache: new WeakMap(),
  // A texture tile the AI drew, repeated across a whole surface.
  tile(g, sprite, x0, y0, w, h) {
    const c = Px.bake(sprite, sprite.pixels, false, 1);
    g.save(); g.translate(x0, y0);
    g.fillStyle = g.createPattern(c, "repeat"); g.fillRect(0, 0, w, h);
    g.restore();
  },
};

function sky(hour) {
  if (hour < 5 || hour >= 21) return ["#0f1630", "#1d2850"];
  if (hour < 7) return ["#f0a27a", "#6f7fb8"];
  if (hour < 18) return ["#8fd0f5", "#cfeefc"];
  return ["#f39a63", "#7a5c9e"];
}
// His world runs on its own clock (Cape Town's, UTC+2, unless he has moved it), whatever time it is where you're visiting from.
const worldOffset = () => (typeof S !== "undefined" && S.weather && typeof S.weather.offset === "number" ? S.weather.offset : 2);
const worldTime = () => new Date(Date.now() + worldOffset() * 3600 * 1000);
const worldHour = () => worldTime().getUTCHours();
// The weather there right now, when the page has it (rain makes grey clouds and drops on the glass).
const worldWeather = () => (typeof weatherNow === "function" ? weatherNow() : null);
const isNight = () => {
  const w = worldWeather();
  if (w && "env_daylight" in w) return !w.env_daylight;
  const h = worldHour(); return h < 6 || h >= 20;
};

const worldHourF = () => { const d = worldTime(); return d.getUTCHours() + d.getUTCMinutes() / 60; };
// The season where his world is: the hemisphere comes from where he lives (south unless he moved north).
const worldSeason = () => {
  const k = Math.floor(((worldTime().getUTCMonth() + 1) % 12) / 3);   // 0 Dec-Feb, 1 Mar-May, 2 Jun-Aug, 3 Sep-Nov
  const north = typeof S !== "undefined" && S.weather && S.weather.lat > 0;
  return (north ? ["winter", "spring", "summer", "autumn"] : ["summer", "autumn", "winter", "spring"])[k];
};
const GRASS = { spring: "#74b955", summer: "#93a94a", autumn: "#9c9a52", winter: "#6a9466" };
const SPECKS = { spring: ["#f6d55c", "#f39ac0", "#ffffff"], autumn: ["#c8752f", "#a34f22", "#d9a441"] };

// The light of the hour: warm at dawn and dusk, dark at night except around lamps, screens and fires.
const _dark = typeof document !== "undefined" ? document.createElement("canvas") : null;
function lighting(g, room, W, H, t, lights) {
  const h = worldHourF(), night = isNight(), outdoor = room.kind === "outdoor";
  if (!night) {
    const a = h < 9 ? 0.14 * Math.max(0, 1 - (h - 5) / 4) : h >= 16.5 ? Math.min(0.2, (h - 16.5) * 0.07) : 0;
    if (a > 0.01) { g.fillStyle = `rgba(255,140,80,${a.toFixed(3)})`; g.fillRect(0, 0, W, H); }
    return;
  }
  const c = _dark; c.width = W; c.height = H;
  const s = c.getContext("2d");
  s.fillStyle = `rgba(10,14,40,${outdoor ? 0.5 : 0.42})`; s.fillRect(0, 0, W, H);
  s.globalCompositeOperation = "destination-out";
  for (const L of lights) {
    const gr = s.createRadialGradient(L.x, L.y, 0, L.x, L.y, L.r);
    gr.addColorStop(0, "rgba(0,0,0,.85)"); gr.addColorStop(1, "rgba(0,0,0,0)");
    s.fillStyle = gr; s.fillRect(L.x - L.r, L.y - L.r, L.r * 2, L.r * 2);
  }
  s.globalCompositeOperation = "source-over";
  g.drawImage(c, 0, 0);
  for (const L of lights) {   // and a little warmth (or a screen's cool glow) where the light falls
    const f = L.flicker ? 0.85 + 0.15 * Math.sin(t / 90 + L.x) : 1;
    const gr = g.createRadialGradient(L.x, L.y, 0, L.x, L.y, L.r * 0.8);
    gr.addColorStop(0, L.cool ? `rgba(120,240,170,${0.12 * f})` : `rgba(255,190,110,${0.2 * f})`); gr.addColorStop(1, "rgba(255,190,110,0)");
    g.fillStyle = gr; g.fillRect(L.x - L.r, L.y - L.r, L.r * 2, L.r * 2);
  }
}

// A window pane: the real sky of his world, with clouds, the moon or rain.
function windowView(g, x, y, w, h, t) {
  const [a, b] = sky(worldHour()), wx = worldWeather(), rain = wx && wx.env_rain > 0, night = isNight();
  for (let i = 0; i < h; i++) Px.rect(g, x, y + i, w, 1, i < h / 2 ? (rain ? Px.shade(a, 0.7) : a) : (rain ? Px.shade(b, 0.75) : b));
  if (night && !rain) {
    [[0.12, 0.12], [0.55, 0.25], [0.75, 0.08], [0.3, 0.5], [0.85, 0.6]].forEach(([fx, fy], i) => Px.rect(g, x + fx * w, y + fy * h, 1, 1, (Math.floor(t / 600) + i) % 4 ? "#fff" : "#99a"));
    Px.rect(g, x + w * 0.7, y + h * 0.3, 4, 4, "#f4f1d0");
  } else if (!night && !rain) {
    const cx = x + ((t / 400) % w);
    Px.rect(g, Math.min(cx, x + w - 10), y + h * 0.2, 10, 3, "#fff"); Px.rect(g, Math.min(cx + 2, x + w - 6), y + h * 0.2 - 2, 6, 2, "#fff");
  }
  if (rain) {
    for (let i = 0; i < 3; i++) Px.ellipse(g, x + ((i * 17 + t / 900) % w), y + 4 + i * 3, 7, 2.5, "#9aa0a8");
    for (let i = 0; i < Math.min(40, 8 + wx.env_rain * 10); i++) {
      const dx = (i * 13 + Math.floor(t / 30)) % w, dy = (i * 7 + Math.floor(t / 12)) % h;
      Px.rect(g, x + dx, y + dy, 1, 2, "rgba(200,220,240,.7)");
    }
  }
}

// ---- Sprout ------------------------------------------------------------------
const MOODS_HAPPY = /happy|content|excit|joy|proud|glad|curious|delight|eager|cheer|satisf|grate|inspir|calm|peace|playful/;
const MOODS_SAD = /sad|worr|tired|anx|frustr|confus|lonely|upset|bored|sleepy|weary|overwhelm/;

// o: { t, pose: stand|sit|type|sleep, walking, mood, prop: book|can|lens|tool|null, closed }
function drawSprout(g, x, y, o) {
  const look = o.look || {}, col = look.colors || {}, t = o.t || 0;
  const body = col.body || "#66c28a", dark = Px.shade(body, 0.7), belly = col.belly || "#a6e0b8", leaf = col.leaf || "#5fae57";
  const ink = col.eyes || "#1d2b22", cheeks = col.cheeks || "#ef9aa5";
  if (look.sprite) return drawOwnLook(g, x, y, o, look);
  if (o.pose === "sleep" && !o.walking) {   // only his head peeks out from under the blanket
    Px.ellipse(g, x + 24, y - 12, 7, 6, body);
    Px.rect(g, x + 20, y - 12, 3, 1, ink); Px.rect(g, x + 26, y - 12, 3, 1, ink);
    Px.rect(g, x + 24, y - 20, 1, 3, dark); Px.ellipse(g, x + 27, y - 21, 3, 1.5, leaf); Px.ellipse(g, x + 21, y - 20, 2.5, 1.2, leaf);
    const z = Math.floor(t / 700) % 3;
    g.fillStyle = "#ffffff"; g.font = "7px monospace";
    for (let i = 0; i <= z; i++) g.fillText("z", x + 32 + i * 5, y - 20 - i * 6);
    return;
  }
  const sit = o.pose === "sit" && !o.walking;
  const bob = o.walking ? Math.abs(Math.sin(t / 90)) * 2 : Math.sin(t / 600) * 0.6;
  const cy = Math.round(y - 11 + (sit ? 4 : 0) - bob);
  Px.ellipse(g, x, y, 8, 1.5, "rgba(0,0,0,.22)");
  if (!sit) {
    const step = o.walking ? Math.round(Math.sin(t / 90) * 2) : 0;
    Px.rect(g, x - 6 + step, y - 3, 4, 3, dark); Px.rect(g, x + 2 - step, y - 3, 4, 3, dark);
  }
  Px.ellipse(g, x, cy, 8, 9, body);
  Px.ellipse(g, x, cy + 3, 5, 5, belly);
  Px.rect(g, x - 6, cy - 6, 2, 2, Px.shade(body, 1.3));

  const busy = !o.walking && (o.pose === "type" || o.prop === "tool");
  const tap = busy ? Math.floor(t / 140) % 2 : 0;
  Px.ellipse(g, x - 8, cy + 2 - tap, 2, 2.5, body);
  Px.ellipse(g, x + 8, cy + 2 - (busy ? 1 - tap : 0), 2, 2.5, body);
  if (o.prop === "book") { Px.rect(g, x + 7, cy - 2, 6, 7, "#b5473a"); Px.rect(g, x + 8, cy - 1, 4, 5, "#f3ead8"); Px.rect(g, x + 8, cy + 1, 4, 1, "#c9bda6"); }
  if (o.prop === "can") {
    Px.rect(g, x + 8, cy, 7, 5, "#8aa0b4"); Px.rect(g, x + 15, cy - 2, 3, 1, "#8aa0b4"); Px.rect(g, x + 14, cy - 1, 2, 2, "#8aa0b4");
    if (Math.floor(t / 120) % 3) Px.rect(g, x + 18, cy + (Math.floor(t / 60) % 4), 1, 2, "#7cc6f2");
  }
  if (o.prop === "lens") { Px.ellipse(g, x + 13, cy - 2, 3, 3, "#d9c27a"); Px.ellipse(g, x + 13, cy - 2, 2, 2, "#cfeefc"); Px.rect(g, x + 10, cy + 1, 2, 3, "#6e4a2d"); }
  if (o.prop === "tool") { Px.rect(g, x + 9, cy - 4 + tap, 2, 7, "#6e4a2d"); Px.rect(g, x + 7, cy - 5 + tap, 6, 2, "#9aa3ab"); }

  const blink = o.closed || Math.floor(t / 100) % 45 === 0, gaze = o.pose === "type" && !o.walking ? 1 : 0;
  for (const ex of [-3, 3]) {
    Px.ellipse(g, x + ex, cy - 2, 2, 2.5, "#ffffff");
    if (blink) Px.rect(g, x + ex - 2, cy - 2, 4, 1, ink); else Px.rect(g, x + ex - 1 + gaze, cy - 2, 2, 2, ink);
  }
  Px.rect(g, x - 7, cy + 1, 2, 1, cheeks); Px.rect(g, x + 5, cy + 1, 2, 1, cheeks);
  const mood = String(o.mood || "");
  if (MOODS_SAD.test(mood)) { Px.rect(g, x - 1, cy + 3, 3, 1, ink); Px.rect(g, x - 2, cy + 4, 1, 1, ink); Px.rect(g, x + 2, cy + 4, 1, 1, ink); }
  else if (MOODS_HAPPY.test(mood) || !mood) { Px.rect(g, x - 2, cy + 3, 1, 1, ink); Px.rect(g, x - 1, cy + 4, 3, 1, ink); Px.rect(g, x + 2, cy + 3, 1, 1, ink); }
  else Px.rect(g, x - 1, cy + 4, 3, 1, ink);

  const sway = Math.round(Math.sin(t / 700));
  Px.rect(g, x, cy - 13, 1, 5, dark);
  Px.ellipse(g, x + 4 + sway, cy - 14, 3.5, 1.6, leaf);
  Px.ellipse(g, x - 3 + sway, cy - 12, 2.5, 1.3, leaf);
}

// A drawing he made of himself: it bobs, walks and sits; in bed it shows his "sleeping" drawing
// or, failing that, the top of his head peeking out.
function drawOwnLook(g, x, y, o, look) {
  const t = o.t || 0, art = look.sprite;
  if (o.pose === "sleep" && !o.walking) {
    if (look.sleeping) Px.art(g, look.sleeping, look.sleeping.pixels, x + 24, y - 6);
    else Px.art(g, art, art.pixels.slice(0, Math.ceil(art.pixels.length * 0.45)), x + 24, y - 6);
    g.fillStyle = "#ffffff"; g.font = "7px monospace";
    for (let i = 0; i <= Math.floor(t / 700) % 3; i++) g.fillText("z", x + 34 + i * 5, y - 20 - i * 6);
    return;
  }
  const bob = o.walking ? Math.round(Math.abs(Math.sin(t / 90)) * 2) : 0, sit = o.pose === "sit" && !o.walking ? 4 : 0;
  Px.ellipse(g, x, y, 8, 1.5, "rgba(0,0,0,.22)");
  Px.art(g, art, art.pixels, x, y + sit - bob);
}

// ---- things he brings to life ---------------------------------------------------
function specNorm(sp, name) {
  const v = sp.spec.vars[name];
  return v ? Math.min(1, Math.max(0, (sp.values[name] - v.min) / (v.max - v.min))) : null;
}

// Draws a specimen standing on (x, y); returns its bounding box so it can be clicked.
function drawSpecimen(g, sp, x, y, t) {
  if (sp.status !== "dead") return drawSpecimenBody(g, sp, x, y, t);
  g.save(); g.globalAlpha = 0.5;   // things that have died fade, so they stand out even when already grey
  const box = drawSpecimenBody(g, sp, x, y, t);
  g.restore();
  return box;
}

function drawSpecimenBody(g, sp, x, y, t) {
  const spec = sp.spec, look = spec.look, kind = spec.kind, dead = sp.status === "dead", seed = Px.hash(sp.id);
  const parts = new Set(look.parts);
  if (sp.moving) x += Math.round(Math.sin(t / (kind === "vehicle" || kind === "machine" ? 900 : 1600) + seed) * (kind === "vehicle" ? 14 : 6));
  const flip = sp.moving && Math.cos(t / (kind === "vehicle" || kind === "machine" ? 900 : 1600) + seed) < 0 ? -1 : 1;

  if (spec.sprite) {   // his own pixel art
    const rows = sp.state_sprite != null && spec.sprite.states ? spec.sprite.states[sp.state_sprite].pixels : spec.sprite.pixels;
    const scale = spec.sprite.size_var ? 0.5 + 0.5 * specNorm(sp, spec.sprite.size_var) : 1;
    Px.ellipse(g, x, y, (Math.max(...rows.map((r) => r.length)) * scale) / 2, 1.5, "rgba(0,0,0,.22)");
    const { w, h } = Px.art(g, spec.sprite, rows, x, y - (sp.moving ? Math.round(Math.abs(Math.sin(t / 150))) : 0), dead, scale);
    if (parts.has("steam") && !dead) steam(g, x, y - h, t);
    return { x: x - w / 2, y: y - h, w, h };
  }

  const health = spec.alive_var ? specNorm(sp, spec.alive_var) : 1;
  let col = look.color, part = look.part_color;
  if (dead) { col = Px.grey(col); part = Px.grey(part); }
  else if (health < 0.35) { col = Px.shade(col, 0.8); part = Px.shade(part, 0.75); }
  const size = look.size_var ? 0.55 + 0.45 * Math.min(1, Math.sqrt(specNorm(sp, look.size_var) * 6)) : 0.8;
  const lush = dead ? 0 : look.lush_var ? specNorm(sp, look.lush_var) : 1;
  const w = (kind === "vehicle" ? 30 : 16) * size;

  let base = y;
  Px.ellipse(g, x, y, Math.max(9, w / 2), 1.5, "rgba(0,0,0,.25)");
  if (parts.has("pot") || (kind === "plant" && !parts.has("plate"))) {
    Px.rect(g, x - 7, y - 8, 14, 8, parts.has("pot") && kind !== "plant" ? "#3b3b40" : "#b5653a");
    Px.rect(g, x - 8, y - 9, 16, 2, parts.has("pot") && kind !== "plant" ? "#55555c" : "#c97a4c");
    if (kind === "plant") Px.rect(g, x - 6, y - 10, 12, 1, "#5a3b22");
    base = y - 9;
  } else if (parts.has("plate") || kind === "food") {
    Px.ellipse(g, x, y - 1, w / 2 + 4, 2, "#f4f1ea"); Px.ellipse(g, x, y - 1, w / 2 + 1, 1, "#ddd8cc"); base = y - 2;
  } else if (kind === "object" || kind === "machine") {
    Px.rect(g, x - 9, y - 4, 18, 4, "#6e4a2d"); Px.rect(g, x - 8, y - 5, 16, 1, "#8a5d3a"); base = y - 5;
  }
  const legs = parts.has("legs") ? 3 : 0, wheels = parts.has("wheels") ? 3 : 0;
  const lift = legs + wheels;
  let top, cy, cx = x;
  if (look.shape === "dome") { const h = w * 0.6; Px.ellipse(g, cx, base - lift, w / 2, h, col, true); top = base - lift - h; cy = base - lift - h / 2; }
  else if (look.shape === "tall") { cy = base - lift - w * 0.8; Px.ellipse(g, cx, cy, w / 3, w * 0.8, col); top = cy - w * 0.8; }
  else if (look.shape === "long") { cy = base - lift - w / 3; Px.ellipse(g, cx, cy, w * 0.7, w / 3, col); top = cy - w / 3; }
  else if (look.shape === "box") { const h = kind === "vehicle" ? w * 0.4 : w * 0.8; Px.rect(g, cx - w / 2, base - lift - h, w, h, col); top = base - lift - h; cy = top + h / 2; }
  else if (look.shape === "bush") { cy = base - lift - w / 2; [[-w / 3, 0], [w / 3, 0], [0, -w / 3]].forEach(([dx, dy]) => Px.ellipse(g, cx + dx, cy + dy, w / 3, w / 3, col)); top = cy - w * 0.66; }
  else if (look.shape === "crystal") { for (let i = 0; i < w; i++) Px.rect(g, cx - i / 3, base - lift - w + i, (i / 3) * 2 + 1, 1, col); top = base - lift - w; cy = base - lift - w / 2; }
  else { const wob = look.shape === "blob" ? Math.sin(t / 400) : 0; cy = base - lift - w / 2; Px.ellipse(g, cx, cy, w / 2 + wob, w / 2 - wob, col); top = cy - w / 2; }
  const bottom = base - lift, half = (bottom - top) / 2 || 1;

  const tex = look.texture, dk = Px.shade(col, 0.72), lt = Px.shade(col, 1.3);
  for (let i = 0; i < w * 3; i++) {
    const px = cx - w / 2 + ((i * 7 + seed) % Math.max(1, Math.round(w))), py = top + 2 + ((i * 5 + seed) % Math.max(1, Math.round(bottom - top - 2)));
    if (look.shape !== "box" && Math.hypot((px - cx) / (w / 2), (py - (top + half)) / half) > 0.8) continue;
    if (tex === "cracked" && i % 2 === 0) Px.rect(g, px, py, (i % 3) + 1, 1, dk);
    else if (tex === "spotted" && i % 4 === 0) Px.rect(g, px, py, 2, 2, dk);
    else if (tex === "scaly" && i % 2 === 0) Px.rect(g, px, py, 1, 1, i % 4 ? dk : lt);
    else if (tex === "furry" && i % 3 === 0) Px.rect(g, px, py, 1, 2, lt);
    else if (tex === "leafy" && i % 3 === 0) Px.rect(g, px, py, 2, 1, part);
  }
  if (tex === "striped") for (let sx = -w / 2 + 2; sx < w / 2; sx += 4) Px.rect(g, cx + sx, top + 2, 1, bottom - top - 3, dk);
  if (tex === "shiny") { Px.rect(g, cx - w / 3, top + 2, 3, 1, "#ffffff"); Px.rect(g, cx - w / 3, top + 3, 1, 2, "#ffffff"); }
  else if (look.shape !== "crystal") Px.rect(g, cx - w / 4, top + 1, 2, 1, lt);

  const step = sp.moving || kind === "animal" ? Math.round(Math.sin(t / 120)) : 0;
  if (legs) [-w / 3, -w / 8, w / 8, w / 3].forEach((dx, i) => Px.rect(g, cx + dx, bottom + (i % 2 ? step : -step) * 0.5, 1, legs, dk));
  if (wheels) for (const dx of [-w / 3, w / 3]) { Px.ellipse(g, cx + dx, base - 2, 3, 3, "#222"); Px.rect(g, cx + dx - (sp.moving ? Math.floor(t / 80) % 2 : 0), base - 2, 1, 1, "#999"); }
  if (parts.has("windows")) for (let wx = -w / 2 + 3; wx < w / 2 - 3; wx += 6) Px.rect(g, cx + wx, top + 2, 4, Math.max(2, half * 0.6), "#bfe3f5");
  if (parts.has("chimney")) { Px.rect(g, cx + flip * w / 3, top - 5, 3, 5, dk); if (sp.moving) steam(g, cx + flip * w / 3 + 1, top - 5, t); }
  if (parts.has("lights")) Px.rect(g, cx + flip * (w / 2 - 1), cy, 2, 2, sp.moving || isNight() ? "#ffe680" : "#bba");
  if (parts.has("steam") && !dead) steam(g, cx, top, t);
  if (parts.has("shell")) Px.ellipse(g, cx, cy - 1, w / 2.6, half * 0.7, Px.shade(part, 0.9), true);
  if (parts.has("spikes")) for (let sx = -w / 3; sx <= w / 3; sx += 3) Px.rect(g, cx + sx, top - 2, 1, 3, part);
  if (parts.has("ears")) { Px.rect(g, cx - w / 4, top - 3, 2, 4, col); Px.rect(g, cx + w / 4 - 1, top - 3, 2, 4, col); }
  if (parts.has("antennae")) { Px.rect(g, cx - 2, top - 5, 1, 5, dk); Px.rect(g, cx + 2, top - 5, 1, 5, dk); }
  if (parts.has("tail")) Px.rect(g, cx - flip * (w / 2 + 3), cy - 1 + Math.round(Math.sin(t / 300)), 4, 1, dk);
  if (parts.has("wings")) { const fl = dead ? 0 : Math.round(Math.sin(t / 150) * 2); Px.ellipse(g, cx - 2, cy - 2 - fl, w / 4, 2, Px.shade(part, 1.2)); }
  if (parts.has("eyes") || kind === "animal" || kind === "creature") {
    const ex = cx + flip * w / 5;
    if (dead) Px.rect(g, ex - 1, cy - 2, 3, 1, "#222");
    else { Px.rect(g, ex - 2, cy - 3, 2, 2, "#fff"); Px.rect(g, ex + 1, cy - 3, 2, 2, "#fff"); Px.rect(g, ex - 1 + (flip > 0 ? 0 : -1), cy - 2, 1, 1, "#111"); Px.rect(g, ex + 2 + (flip > 0 ? 0 : -1), cy - 2, 1, 1, "#111"); }
  }

  const spots = [];
  if (parts.has("vine") && lush > 0.03) {
    const len = Math.round(6 + 34 * lush);
    Px.rect(g, x + 5, base - len - 4, 1, len + 4, "#8a6a45");
    for (let i = 0; i < len; i++) {
      const vx = x + 5 + Math.round(Math.sin(i / 3 + t / 2000) * 2), vy = top - i + (bottom - top) * 0.2;
      Px.rect(g, vx, vy, 1, 1, Px.shade(part, 0.8));
      if (i % 4 === 2) spots.push([vx + (i % 8 === 2 ? 2 : -2), vy]);
    }
  } else if (lush > 0.03 && (parts.has("leaves") || parts.has("flowers"))) {
    const n = Math.round(3 + 7 * lush);
    for (let i = 0; i < n; i++) spots.push([cx + Math.cos(i * 2.4) * w / 3, top - 1 - (i % 3) * 2]);
  }
  if (parts.has("leaves")) spots.slice(0, Math.round(spots.length * Math.max(0.2, lush))).forEach(([lx, ly]) => Px.ellipse(g, lx, ly, 2, 1.2, part));
  if (parts.has("flowers") && lush > 0.5) spots.filter((_, i) => i % 3 === 1).forEach(([lx, ly]) => Px.rect(g, lx, ly - 1, 2, 2, kind === "plant" ? "#e3d36a" : part));
  const highest = Math.min(top - 6, spots.length ? Math.min(...spots.map((s) => s[1])) : top);
  return { x: cx - w / 2 - 4, y: highest, w: w + 12, h: y - highest };
}

function steam(g, x, y, t) {
  for (let i = 0; i < 3; i++) {
    const k = ((t / 40) + i * 13) % 20;
    Px.rect(g, x + Math.round(Math.sin((t / 300) + i) * 2) + (i - 1) * 2, y - k, 1, 1, `rgba(235,235,235,${1 - k / 20})`);
  }
}

// ---- furniture -----------------------------------------------------------------------
const WOOD = "#8a5d3a";
// Floor pieces stand on (x, y); wall pieces hang with their top centre at (x, y). Returns width/height.
const FURNITURE = {
  table: (g, x, y, c = WOOD) => { Px.rect(g, x - 14, y - 15, 28, 3, c); Px.rect(g, x - 12, y - 12, 2, 12, Px.shade(c, .75)); Px.rect(g, x + 10, y - 12, 2, 12, Px.shade(c, .75)); return [28, 15]; },
  chair: (g, x, y, c = WOOD) => { Px.rect(g, x - 5, y - 20, 2, 20, Px.shade(c, .8)); Px.rect(g, x - 5, y - 10, 11, 2, c); Px.rect(g, x + 4, y - 8, 2, 8, Px.shade(c, .8)); return [12, 20]; },
  stove: (g, x, y, c = "#e8e4dc") => { Px.rect(g, x - 11, y - 22, 22, 22, c); Px.rect(g, x - 11, y - 22, 22, 3, "#333"); Px.rect(g, x - 8, y - 15, 16, 10, "#2a2a30"); Px.rect(g, x - 6, y - 13, 12, 2, isNight() ? "#ff9a4a" : "#555"); Px.rect(g, x - 7, y - 25, 5, 3, "#444"); Px.rect(g, x + 2, y - 25, 5, 3, "#444"); return [22, 25]; },
  oven: (g, x, y, c) => FURNITURE.stove(g, x, y, c),
  fridge: (g, x, y, c = "#f1f1ee") => { Px.rect(g, x - 9, y - 38, 18, 38, c); Px.rect(g, x - 9, y - 26, 18, 1, Px.shade(c, .8)); Px.rect(g, x + 6, y - 34, 1, 6, "#999"); Px.rect(g, x + 6, y - 22, 1, 8, "#999"); return [18, 38]; },
  counter: (g, x, y, c = "#d9cbb0") => { Px.rect(g, x - 18, y - 18, 36, 18, Px.shade(c, .8)); Px.rect(g, x - 19, y - 20, 38, 3, c); Px.rect(g, x - 16, y - 14, 15, 12, Px.shade(c, .7)); Px.rect(g, x + 1, y - 14, 15, 12, Px.shade(c, .7)); return [38, 20]; },
  sink: (g, x, y, c) => { FURNITURE.counter(g, x, y, c); Px.rect(g, x - 8, y - 20, 16, 2, "#9aa3ab"); Px.rect(g, x - 1, y - 26, 2, 6, "#9aa3ab"); Px.rect(g, x - 1, y - 26, 5, 2, "#9aa3ab"); return [38, 26]; },
  sofa: (g, x, y, c = "#7a5c9e") => { Px.rect(g, x - 20, y - 18, 40, 10, Px.shade(c, .85)); Px.rect(g, x - 20, y - 10, 40, 8, c); Px.rect(g, x - 22, y - 13, 4, 11, Px.shade(c, .75)); Px.rect(g, x + 18, y - 13, 4, 11, Px.shade(c, .75)); Px.rect(g, x - 18, y - 2, 2, 2, "#3a2a1c"); Px.rect(g, x + 16, y - 2, 2, 2, "#3a2a1c"); return [44, 18]; },
  armchair: (g, x, y, c = "#5b7fa6") => { Px.rect(g, x - 12, y - 20, 24, 10, Px.shade(c, .85)); Px.rect(g, x - 12, y - 11, 24, 9, c); Px.rect(g, x - 14, y - 14, 4, 12, Px.shade(c, .75)); Px.rect(g, x + 10, y - 14, 4, 12, Px.shade(c, .75)); return [28, 20]; },
  lamp: (g, x, y, c = "#e9d79a") => { Px.rect(g, x - 4, y - 2, 8, 2, "#444"); Px.rect(g, x, y - 30, 1, 28, "#555"); Px.rect(g, x - 5, y - 36, 11, 7, c); if (isNight()) Px.ellipse(g, x, y - 26, 12, 6, "rgba(255,230,140,.18)"); return [12, 36]; },
  rug: (g, x, y, c = "#9b4d4a") => { Px.ellipse(g, x, y - 2, 26, 4, c); Px.ellipse(g, x, y - 2, 21, 3, Px.shade(c, 1.2)); return [52, 6]; },
  cabinet: (g, x, y, c = WOOD) => { Px.rect(g, x - 10, y - 24, 20, 24, c); Px.rect(g, x - 8, y - 22, 7, 20, Px.shade(c, .85)); Px.rect(g, x + 1, y - 22, 7, 20, Px.shade(c, .85)); Px.rect(g, x - 2, y - 13, 1, 2, "#e3c15b"); Px.rect(g, x + 2, y - 13, 1, 2, "#e3c15b"); return [20, 24]; },
  bookcase: (g, x, y, c = "#5b3a22") => { Px.rect(g, x - 12, y - 44, 24, 44, c); for (let r = 0; r < 4; r++) for (let i = 0; i < 6; i++) Px.rect(g, x - 10 + i * 3.5, y - 42 + r * 11, 2, 9, ["#b5473a", "#3d6fa6", "#5aa04a", "#d6a640"][(i + r) % 4]); return [24, 44]; },
  bed: (g, x, y, c = "#5b7fa6") => { Px.rect(g, x - 22, y - 12, 44, 12, "#6e4a2d"); Px.rect(g, x - 21, y - 16, 42, 6, "#e9e2d0"); Px.rect(g, x + 8, y - 18, 12, 5, "#fdfbf5"); Px.rect(g, x - 21, y - 14, 27, 8, c); return [44, 18]; },
  desk: (g, x, y, c = WOOD) => { FURNITURE.table(g, x, y, c); Px.rect(g, x + 2, y - 12, 9, 8, Px.shade(c, .85)); Px.rect(g, x + 5, y - 9, 3, 1, "#e3c15b"); return [28, 15]; },
  plant: (g, x, y, c = "#4f9a49") => { Px.rect(g, x - 5, y - 9, 10, 9, "#b5653a"); for (let i = 0; i < 6; i++) Px.ellipse(g, x + Math.cos(i * 1.2) * 4, y - 13 - (i % 3) * 3, 3, 2, Px.shade(c, 0.85 + (i % 3) * 0.15)); return [12, 20]; },
  tree: (g, x, y, c = "#3f8a3a") => { Px.rect(g, x - 3, y - 30, 6, 30, "#6e4a2d"); Px.ellipse(g, x, y - 42, 18, 14, c); Px.ellipse(g, x - 8, y - 36, 10, 8, Px.shade(c, .85)); Px.ellipse(g, x + 6, y - 48, 9, 6, Px.shade(c, 1.2)); return [36, 56]; },
  bush: (g, x, y, c = "#4f9a49") => { Px.ellipse(g, x - 6, y - 6, 8, 6, Px.shade(c, .85)); Px.ellipse(g, x + 6, y - 6, 8, 6, c); Px.ellipse(g, x, y - 10, 8, 6, Px.shade(c, 1.15)); return [28, 16]; },
  flowerbed: (g, x, y, c = "#e3637a") => { Px.rect(g, x - 18, y - 4, 36, 4, "#6b4a2e"); for (let i = 0; i < 9; i++) { Px.rect(g, x - 16 + i * 4, y - 9, 1, 5, "#4f9a49"); Px.rect(g, x - 17 + i * 4, y - 11, 3, 2, i % 3 ? c : "#f2d45c"); } return [36, 11]; },
  fence: (g, x, y, c = "#e8e0d0") => { for (let i = -24; i <= 24; i += 6) { Px.rect(g, x + i, y - 18, 3, 18, c); Px.rect(g, x + i + 1, y - 19, 1, 1, c); } Px.rect(g, x - 26, y - 14, 54, 2, Px.shade(c, .85)); Px.rect(g, x - 26, y - 6, 54, 2, Px.shade(c, .85)); return [54, 19]; },
  bench: (g, x, y, c = WOOD) => { Px.rect(g, x - 16, y - 9, 32, 3, c); Px.rect(g, x - 16, y - 16, 32, 2, c); Px.rect(g, x - 14, y - 6, 2, 6, "#444"); Px.rect(g, x + 12, y - 6, 2, 6, "#444"); return [32, 16]; },
  workbench: (g, x, y, c = "#a77a4a") => { FURNITURE.table(g, x, y, c); Px.rect(g, x - 10, y - 18, 6, 3, "#9aa3ab"); Px.rect(g, x - 2, y - 19, 2, 4, "#b5473a"); Px.rect(g, x + 4, y - 17, 7, 2, "#555"); Px.rect(g, x - 14, y - 4, 28, 2, Px.shade(c, .7)); return [28, 19]; },
  tv: (g, x, y, c = "#2a2a30") => { Px.rect(g, x - 10, y - 10, 20, 10, WOOD); Px.rect(g, x - 12, y - 26, 24, 15, c); Px.rect(g, x - 11, y - 25, 22, 13, `hsl(${(Date.now() / 50) % 360} 40% 45%)`); return [24, 26]; },
  pond: (g, x, y, c = "#4f8fc0") => { Px.ellipse(g, x, y - 3, 24, 5, "#8a8f86"); Px.ellipse(g, x, y - 3, 21, 4, c); Px.rect(g, x - 8 + (Date.now() / 300) % 14, y - 4, 3, 1, Px.shade(c, 1.4)); return [48, 8]; },
  shed: (g, x, y, c = "#9b6a43") => { Px.rect(g, x - 18, y - 26, 36, 26, c); for (let i = 0; i < 18; i++) Px.rect(g, x - 20 + i, y - 27 - i * 0.7, 40 - i * 2, 1, "#6e3b2b"); Px.rect(g, x - 5, y - 18, 10, 18, Px.shade(c, .7)); return [40, 40]; },
  barbecue: (g, x, y, c = "#2f2f33") => { Px.ellipse(g, x, y - 16, 9, 6, c, true); Px.rect(g, x - 9, y - 16, 18, 2, "#555"); Px.rect(g, x - 6, y - 14, 1, 14, "#555"); Px.rect(g, x + 5, y - 14, 1, 14, "#555"); return [18, 22]; },
  piano: (g, x, y, c = "#1f1b1b") => { Px.rect(g, x - 16, y - 30, 32, 30, c); Px.rect(g, x - 14, y - 16, 28, 4, "#f4f1ea"); for (let i = 0; i < 9; i++) Px.rect(g, x - 13 + i * 3, y - 16, 1, 2, "#111"); return [32, 30]; },
  easel: (g, x, y, c = "#f4f1ea") => { Px.rect(g, x - 8, y - 30, 1, 30, WOOD); Px.rect(g, x + 7, y - 30, 1, 30, WOOD); Px.rect(g, x - 9, y - 30, 18, 14, c); Px.rect(g, x - 6, y - 26, 5, 4, "#e3637a"); Px.rect(g, x, y - 24, 6, 5, "#3d6fa6"); return [18, 30]; },
  telescope: (g, x, y, c = "#c7ccd2") => { Px.rect(g, x - 6, y - 14, 1, 14, "#555"); Px.rect(g, x + 5, y - 14, 1, 14, "#555"); for (let i = 0; i < 16; i++) Px.rect(g, x - 6 + i, y - 16 - i * 0.6, 3, 3, c); return [22, 28]; },
  train_table: (g, x, y, c = "#4f8a4a") => { Px.rect(g, x - 26, y - 16, 52, 4, c); Px.rect(g, x - 24, y - 12, 2, 12, WOOD); Px.rect(g, x + 22, y - 12, 2, 12, WOOD); Px.rect(g, x - 22, y - 17, 44, 1, "#5a4a3a"); return [52, 17]; },
  garage_door: (g, x, y, c = "#c9cdd2") => { Px.rect(g, x - 26, y - 44, 52, 44, c); for (let i = 1; i < 6; i++) Px.rect(g, x - 26, y - 44 + i * 7, 52, 1, Px.shade(c, .8)); return [52, 44]; },
  // wall pieces
  painting: (g, x, y, c = "#c9a06b") => { Px.rect(g, x - 12, y, 24, 18, c); Px.rect(g, x - 10, y + 2, 20, 14, "#8fd0f5"); Px.rect(g, x - 10, y + 10, 20, 6, "#5aa04a"); Px.ellipse(g, x + 5, y + 6, 2, 2, "#f2d45c"); return [24, 18]; },
  shelf: (g, x, y, c = WOOD) => { Px.rect(g, x - 16, y + 10, 32, 2, c); Px.rect(g, x - 12, y + 3, 4, 7, "#b5473a"); Px.rect(g, x - 6, y + 5, 6, 5, "#e9e2d0"); Px.rect(g, x + 4, y + 4, 3, 6, "#3d6fa6"); Px.rect(g, x + 9, y + 6, 4, 4, "#5aa04a"); return [32, 12]; },
  clock: (g, x, y, c = "#f4f1ea") => { Px.ellipse(g, x, y + 7, 7, 7, "#6e4a2d"); Px.ellipse(g, x, y + 7, 6, 6, c); const d = worldTime(), a = ((d.getUTCHours() % 12) + d.getUTCMinutes() / 60) / 12 * Math.PI * 2, m = d.getUTCMinutes() / 60 * Math.PI * 2;
    for (let i = 0; i < 3; i++) Px.rect(g, x + Math.sin(a) * i, y + 7 - Math.cos(a) * i, 1, 1, "#222"); for (let i = 0; i < 5; i++) Px.rect(g, x + Math.sin(m) * i, y + 7 - Math.cos(m) * i, 1, 1, "#555"); return [14, 14]; },
  window: (g, x, y, c = "#6e4a2d") => { Px.rect(g, x - 15, y, 30, 28, c); windowView(g, x - 12, y + 2, 24, 24, Date.now()); Px.rect(g, x - 1, y + 2, 2, 24, c); Px.rect(g, x - 12, y + 13, 24, 2, c); return [30, 28]; },
  poster: (g, x, y, c = "#3d6fa6") => { Px.rect(g, x - 9, y, 18, 24, c); Px.rect(g, x - 6, y + 4, 12, 8, Px.shade(c, 1.5)); Px.rect(g, x - 6, y + 15, 12, 1, "#fff"); Px.rect(g, x - 6, y + 18, 8, 1, "#fff"); return [18, 24]; },
  mirror: (g, x, y, c = "#c9a06b") => { Px.ellipse(g, x, y + 12, 9, 12, c); Px.ellipse(g, x, y + 12, 7, 10, "#cfe6ee"); Px.rect(g, x - 4, y + 6, 1, 6, "#fff"); return [18, 24]; },
  cupboard: (g, x, y, c = "#d9cbb0") => { Px.rect(g, x - 16, y, 32, 18, c); Px.rect(g, x - 14, y + 2, 13, 14, Px.shade(c, .85)); Px.rect(g, x + 1, y + 2, 13, 14, Px.shade(c, .85)); return [32, 18]; },
  lights: (g, x, y) => { for (let i = 0; i < 12; i++) { const yy = y + Math.sin(i / 1.9) * 3 + 3; Px.rect(g, x - 33 + i * 6, yy, 1, 1, "#333"); Px.rect(g, x - 33 + i * 6, yy + 1, 2, 2, (Math.floor(Date.now() / 500) + i) % 3 ? ["#f2d45c", "#e3637a", "#7cc6f2"][i % 3] : "#555"); } return [70, 8]; },
  plaque: (g, x, y, c = "#c9a06b") => { Px.rect(g, x - 10, y, 20, 8, c); Px.rect(g, x - 7, y + 3, 14, 1, Px.shade(c, .6)); return [20, 8]; },
};

function drawItem(g, item, x, floorY, wallY, grey) {
  if (item.sprite) {
    const y = item.place === "wall" ? wallY + item.sprite.pixels.length : floorY;
    const { w, h } = Px.art(g, item.sprite, item.sprite.pixels, x, y, grey);
    return { x: x - w / 2, y: y - h, w, h };
  }
  const fn = FURNITURE[item.preset]; if (!fn) return null;
  const hangs = isWallPreset(item.preset);   // wall pieces are drawn from their top edge, floor pieces from their feet
  const y = hangs ? (item.place === "floor" ? floorY - 30 : wallY) : (item.place === "wall" ? wallY + 30 : floorY);
  const [w, h] = fn(g, x, y, item.color || undefined);
  return hangs ? { x: x - w / 2, y, w, h } : { x: x - w / 2, y: y - h, w, h };
}
const WALL_PRESETS = new Set(["painting", "shelf", "clock", "window", "poster", "mirror", "cupboard", "lights", "plaque"]);
const isWallPreset = (p) => WALL_PRESETS.has(p);

// ---- rooms he builds -------------------------------------------------------------------
function drawBuiltRoom(g, room, W, H, t) {
  const night = isNight(), hour = worldHour();
  if (room.kind === "outdoor") {
    const [a, b] = sky(hour).map((c) => parseInt(c.slice(1), 16));
    const mix = (k) => "#" + [16, 8, 0].map((s) => Math.round(((a >> s) & 255) * (1 - k) + ((b >> s) & 255) * k).toString(16).padStart(2, "0")).join("");
    for (let y = 0; y < 100; y++) Px.rect(g, 0, y, W, 1, mix(y / 100));
    if (night) { for (let i = 0; i < 30; i++) Px.rect(g, (i * 97) % W, (i * 31) % 70, 1, 1, (Math.floor(t / 700) + i) % 5 ? "#fff" : "#88a"); Px.ellipse(g, W - 40, 24, 6, 6, "#f4f1d0"); }
    else { Px.ellipse(g, W - 40, 24, 8, 8, "#fff3b0"); for (let i = 0; i < 3; i++) { const cx = ((t / 300) + i * 130) % (W + 40) - 20; Px.ellipse(g, cx, 20 + i * 12, 14, 4, "#ffffff"); } }
    const hill = GRASS[worldSeason()];
    Px.ellipse(g, W * 0.25, 104, W * 0.35, 18, Px.shade(hill, 1.05), true); Px.ellipse(g, W * 0.75, 104, W * 0.3, 14, Px.shade(hill, 0.92), true);
  } else {
    drawWall(g, room, W);
    const n = room.windows || 0;
    for (let i = 0; i < n; i++) FURNITURE.window(g, (W * (i + 1)) / (n + 1), 24);
  }
  drawFloor(g, room, W, room.kind === "outdoor" ? 100 : 118, H);
}

function drawWall(g, room, W) {
  const wall = room.wall || "#d9b98f", pc = room.pattern_color || Px.shade(wall, 0.92);
  if (room.wall_tile) Px.tile(g, room.wall_tile, 0, 0, W, 112);
  else {
    Px.rect(g, 0, 0, W, 118, wall);
    const p = room.pattern;
    if (p === "stripes") for (let x = 0; x < W; x += 12) Px.rect(g, x, 0, 4, 118, pc);
    if (p === "dots") for (let y = 6; y < 112; y += 12) for (let x = (y / 12 % 2) * 6; x < W; x += 12) Px.rect(g, x, y, 2, 2, pc);
    if (p === "brick") for (let y = 0; y < 118; y += 8) { Px.rect(g, 0, y, W, 1, pc); for (let x = (y / 8 % 2) * 8; x < W; x += 16) Px.rect(g, x, y, 1, 8, pc); }
    if (p === "wood") for (let x = 0; x < W; x += 10) Px.rect(g, x, 0, 1, 118, pc);
    if (p === "checks") for (let y = 0; y < 118; y += 10) for (let x = ((y / 10) % 2) * 10; x < W; x += 20) Px.rect(g, x, y, 10, 10, pc);
    if (p === "tiles") for (let y = 0; y < 118; y += 10) { Px.rect(g, 0, y, W, 1, pc); for (let x = 0; x < W; x += 10) Px.rect(g, x, y, 1, 10, pc); }
    if (p === "wallpaper") for (let y = 10; y < 110; y += 20) for (let x = (y / 20 % 2) * 12; x < W; x += 24) { Px.rect(g, x, y, 1, 5, pc); Px.rect(g, x - 2, y + 2, 5, 1, pc); }
  }
  Px.rect(g, 0, 112, W, 6, Px.shade(wall, 0.6));
}

function drawFloor(g, room, W, top, H) {
  if (room.floor_tile) { Px.tile(g, room.floor_tile, 0, top, W, H - top); return; }
  const season = worldSeason(), seasonal = room.floor === "grass" && !room.floor_color;
  const floorCol = room.floor_color || { wood: "#a0714b", tile: "#d9d4c7", carpet: "#8a6f9e", stone: "#9a968d", grass: GRASS[season], dirt: "#8a6a45", sand: "#dcc58e", checks: "#e8e4dc", concrete: "#a7a7a2" }[room.floor];
  Px.rect(g, 0, top, W, H - top, floorCol);
  const dk = Px.shade(floorCol, 0.88);
  if (room.floor === "wood") for (let y = top + 6; y < H; y += 9) { Px.rect(g, 0, y, W, 1, dk); for (let x = (y % 2) * 20; x < W; x += 40) Px.rect(g, x, y - 8, 1, 8, dk); }
  if (room.floor === "tile" || room.floor === "concrete") for (let y = top; y < H; y += 12) { Px.rect(g, 0, y, W, 1, dk); for (let x = 0; x < W; x += room.floor === "tile" ? 16 : 48) Px.rect(g, x, y, 1, 12, dk); }
  if (room.floor === "checks") for (let y = top; y < H; y += 10) for (let x = ((y - top) / 10 % 2) * 10; x < W; x += 20) Px.rect(g, x, y, 10, 10, "#3a3a40");
  if (room.floor === "grass") for (let i = 0; i < W * 1.2; i++) Px.rect(g, (i * 37) % W, top + ((i * 53) % (H - top)), 1, 2, Px.shade(floorCol, i % 2 ? 0.8 : 1.2));
  if (seasonal && SPECKS[season]) for (let i = 0; i < W / 4; i++) Px.rect(g, (i * 71 + 13) % W, top + 3 + ((i * 43) % (H - top - 4)), 2, 1, SPECKS[season][i % 3]);   // spring flowers, autumn leaves
  const wx = worldWeather();
  if (seasonal && season === "winter" && wx && wx.env_temp < 3) for (let i = 0; i < W / 2; i++) Px.rect(g, (i * 59) % W, top + ((i * 31) % (H - top)), 1, 1, "rgba(255,255,255,.7)");   // frost
  if (room.floor === "stone") for (let i = 0; i < W / 3; i++) Px.ellipse(g, (i * 41) % W, top + 4 + ((i * 29) % (H - top - 6)), 6, 2, dk);
  if (room.floor === "dirt" || room.floor === "sand" || room.floor === "carpet") for (let i = 0; i < W; i++) Px.rect(g, (i * 37) % W, top + ((i * 53) % (H - top)), 1, 1, dk);
}

// Rain falling across an outdoor room; heavier rain means more drops.
function rain(g, W, H, t, mm) {
  const drops = Math.min(220, 30 + mm * 60);
  for (let i = 0; i < drops; i++) {
    const x = (i * 53 + t / 9) % W, y = (i * 97 + t / 3) % H;
    Px.rect(g, x, y, 1, 3, "rgba(190,215,240,.55)");
  }
}
