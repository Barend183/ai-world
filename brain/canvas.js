"use strict";
// A tiny pretend canvas, so the page's own drawing code (docs/sprites.js, docs/app.js) can run in Node.js and
// draw exactly what the page shows, for the AI to look at. Used by render.js (one creation) and scene.js (what he sees).
const zlib = require("zlib");

function parseColor(c) {
  let m;
  if ((m = /^#([0-9a-f]{6})$/i.exec(c))) { const n = parseInt(m[1], 16); return [n >> 16, (n >> 8) & 255, n & 255, 1]; }
  if ((m = /^rgba?\(([^)]+)\)$/i.exec(c))) { const p = m[1].split(",").map(Number); return [p[0], p[1], p[2], p[3] ?? 1]; }
  if ((m = /^hsl\(([\d.]+)\s+([\d.]+)%\s+([\d.]+)%\)$/i.exec(c))) {
    const h = +m[1] / 360, s = +m[2] / 100, l = +m[3] / 100, q = l < 0.5 ? l * (1 + s) : l + s - l * s, p = 2 * l - q;
    const f = (t) => { t = (t + 1) % 1; return 255 * (t < 1 / 6 ? p + (q - p) * 6 * t : t < 1 / 2 ? q : t < 2 / 3 ? p + (q - p) * (2 / 3 - t) * 6 : p); };
    return [f(h + 1 / 3), f(h), f(h - 1 / 3), 1];
  }
  if ((m = /^#([0-9a-f]{6})([0-9a-f]{2})$/i.exec(c))) { const n = parseInt(m[1], 16); return [n >> 16, (n >> 8) & 255, n & 255, parseInt(m[2], 16) / 255]; }
  return [0, 0, 0, 0];
}

class Radial {   // a radial gradient: enough for the glows and lamps the page draws
  constructor(x, y, r) { this.x = x; this.y = y; this.r = r; this.stops = []; }
  addColorStop(o, c) { this.stops.push([o, parseColor(c)]); this.stops.sort((p, q) => p[0] - q[0]); }
  at(x, y) {
    const t = Math.min(1, Math.hypot(x - this.x, y - this.y) / this.r), s = this.stops;
    if (!s.length) return [0, 0, 0, 0];
    for (let n = 1; n < s.length; n++) if (t <= s[n][0]) {
      const [o0, c0] = s[n - 1], [o1, c1] = s[n], k = (t - o0) / ((o1 - o0) || 1);
      return c0.map((v, i) => v + (c1[i] - v) * k);
    }
    return s[s.length - 1][1];
  }
}

class Canvas {
  constructor(w = 1, h = 1) { this.width = w; this.height = h; this.ctx = null; }
  getContext() { return this.ctx || (this.ctx = new Ctx(this)); }
}
class Ctx {
  constructor(canvas) { this.canvas = canvas; this.fillStyle = "#000"; this.globalAlpha = 1; this.globalCompositeOperation = "source-over"; this.tx = 0; this.ty = 0; this.stack = []; this.font = ""; }
  get px() { const c = this.canvas; if (!c.px || c.px.length !== c.width * c.height * 4) c.px = new Float32Array(c.width * c.height * 4); return c.px; }
  blend(x, y, [r, g, b, a]) {
    const c = this.canvas; if (x < 0 || y < 0 || x >= c.width || y >= c.height) return;
    const i = (y * c.width + x) * 4, px = this.px, k = a * this.globalAlpha, under = px[i + 3];
    px[i] = r * k + px[i] * (1 - k); px[i + 1] = g * k + px[i + 1] * (1 - k); px[i + 2] = b * k + px[i + 2] * (1 - k); px[i + 3] = k + under * (1 - k);
  }
  fillRect(x, y, w, h) {
    const grad = this.fillStyle instanceof Radial ? this.fillStyle : null, col = grad ? null : parseColor(String(this.fillStyle));
    for (let j = Math.round(y + this.ty); j < Math.round(y + this.ty + h); j++)
      for (let i = Math.round(x + this.tx); i < Math.round(x + this.tx + w); i++) {
        const c = grad ? grad.at(i - this.tx, j - this.ty) : col;
        if (this.globalCompositeOperation === "destination-out") this.erase(i, j, c[3]); else this.blend(i, j, c);
      }
  }
  erase(x, y, a) {   // "destination-out": cuts the lamps' light out of a layer of darkness
    const c = this.canvas; if (x < 0 || y < 0 || x >= c.width || y >= c.height) return;
    const i = (y * c.width + x) * 4, px = this.px, k = 1 - a * this.globalAlpha;
    for (let n = 0; n < 4; n++) px[i + n] *= k;
  }
  drawImage(src, x, y) {
    const px = src.px; if (!px) return;
    for (let j = 0; j < src.height; j++) for (let i = 0; i < src.width; i++) {
      const k = (j * src.width + i) * 4; if (px[k + 3] > 0) this.blend(x + i + this.tx, y + j + this.ty, [px[k] / px[k + 3], px[k + 1] / px[k + 3], px[k + 2] / px[k + 3], px[k + 3]]);
    }
  }
  createRadialGradient(x0, y0, r0, x1, y1, r1) { return new Radial(x1, y1, r1); }
  save() { this.stack.push([this.globalAlpha, this.tx, this.ty]); }
  restore() { [this.globalAlpha, this.tx, this.ty] = this.stack.pop() || [1, 0, 0]; }
  translate(x, y) { this.tx += x; this.ty += y; }
  clearRect() {} fillText() {} beginPath() {} rect() {} clip() {} createPattern() { return "#000000"; }
}

function png(canvas, scale, bg) {
  const w = canvas.width * scale, h = canvas.height * scale, raw = Buffer.alloc((w * 3 + 1) * h), px = canvas.px, back = parseColor(bg);
  for (let y = 0; y < h; y++) {
    raw[y * (w * 3 + 1)] = 0;
    for (let x = 0; x < w; x++) {
      const k = (Math.floor(y / scale) * canvas.width + Math.floor(x / scale)) * 4, a = px[k + 3], o = y * (w * 3 + 1) + 1 + x * 3;
      for (let c = 0; c < 3; c++) raw[o + c] = Math.round(px[k + c] + back[c] * (1 - a));
    }
  }
  const table = Array.from({ length: 256 }, (_, n) => { for (let k = 0; k < 8; k++) n = n & 1 ? 0xedb88320 ^ (n >>> 1) : n >>> 1; return n >>> 0; });
  const crc = (buf) => { let c = 0xffffffff; for (const b of buf) c = table[(c ^ b) & 255] ^ (c >>> 8); return (c ^ 0xffffffff) >>> 0; };
  const chunk = (type, data) => { const len = Buffer.alloc(4); len.writeUInt32BE(data.length); const td = Buffer.concat([Buffer.from(type), data]); const c = Buffer.alloc(4); c.writeUInt32BE(crc(td)); return Buffer.concat([len, td, c]); };
  const head = Buffer.alloc(13); head.writeUInt32BE(w, 0); head.writeUInt32BE(h, 4); head[8] = 8; head[9] = 2;
  return Buffer.concat([Buffer.from([137, 80, 78, 71, 13, 10, 26, 10]), chunk("IHDR", head), chunk("IDAT", zlib.deflateSync(raw)), chunk("IEND", Buffer.alloc(0))]);
}


module.exports = { Canvas, Ctx, png, parseColor };
