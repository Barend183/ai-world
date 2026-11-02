// Draws one creation exactly as the web page does, and prints it as a PNG, so the AI can see it.
// Usage: node render.js < specimen.json > picture.png   (runs docs/sprites.js against a tiny pretend canvas)
"use strict";
const fs = require("fs"), path = require("path"), vm = require("vm"), zlib = require("zlib");

function parseColor(c) {
  let m;
  if ((m = /^#([0-9a-f]{6})$/i.exec(c))) { const n = parseInt(m[1], 16); return [n >> 16, (n >> 8) & 255, n & 255, 1]; }
  if ((m = /^rgba?\(([^)]+)\)$/i.exec(c))) { const p = m[1].split(",").map(Number); return [p[0], p[1], p[2], p[3] ?? 1]; }
  if ((m = /^hsl\(([\d.]+)\s+([\d.]+)%\s+([\d.]+)%\)$/i.exec(c))) {
    const h = +m[1] / 360, s = +m[2] / 100, l = +m[3] / 100, q = l < 0.5 ? l * (1 + s) : l + s - l * s, p = 2 * l - q;
    const f = (t) => { t = (t + 1) % 1; return 255 * (t < 1 / 6 ? p + (q - p) * 6 * t : t < 1 / 2 ? q : t < 2 / 3 ? p + (q - p) * (2 / 3 - t) * 6 : p); };
    return [f(h + 1 / 3), f(h), f(h - 1 / 3), 1];
  }
  return [0, 0, 0, 0];
}

class Canvas {
  constructor(w = 1, h = 1) { this.width = w; this.height = h; this.ctx = null; }
  getContext() { return this.ctx || (this.ctx = new Ctx(this)); }
}
class Ctx {
  constructor(canvas) { this.canvas = canvas; this.fillStyle = "#000"; this.globalAlpha = 1; this.tx = 0; this.ty = 0; this.stack = []; this.font = ""; }
  get px() { const c = this.canvas; if (!c.px || c.px.length !== c.width * c.height * 4) c.px = new Float32Array(c.width * c.height * 4); return c.px; }
  blend(x, y, [r, g, b, a]) {
    const c = this.canvas; if (x < 0 || y < 0 || x >= c.width || y >= c.height) return;
    const i = (y * c.width + x) * 4, px = this.px, k = a * this.globalAlpha, under = px[i + 3];
    px[i] = r * k + px[i] * (1 - k); px[i + 1] = g * k + px[i + 1] * (1 - k); px[i + 2] = b * k + px[i + 2] * (1 - k); px[i + 3] = k + under * (1 - k);
  }
  fillRect(x, y, w, h) {
    const col = parseColor(String(this.fillStyle));
    for (let j = Math.round(y + this.ty); j < Math.round(y + this.ty + h); j++)
      for (let i = Math.round(x + this.tx); i < Math.round(x + this.tx + w); i++) this.blend(i, j, col);
  }
  drawImage(src, x, y) {
    const px = src.px; if (!px) return;
    for (let j = 0; j < src.height; j++) for (let i = 0; i < src.width; i++) {
      const k = (j * src.width + i) * 4; if (px[k + 3] > 0) this.blend(x + i + this.tx, y + j + this.ty, [px[k] / px[k + 3], px[k + 1] / px[k + 3], px[k + 2] / px[k + 3], px[k + 3]]);
    }
  }
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

const sp = JSON.parse(fs.readFileSync(0, "utf8"));
const sandbox = { document: { createElement: () => new Canvas() }, Math, Date, console, Set, Map, WeakMap, Array, Number, String, Object, JSON, parseInt };
vm.createContext(sandbox);
vm.runInContext(fs.readFileSync(path.join(__dirname, "..", "docs", "sprites.js"), "utf8") + "\nthis.drawSpecimen = drawSpecimen; this.Px = Px;", sandbox);
const canvas = new Canvas(140, 120), g = canvas.getContext();
g.px;   // allocate
sandbox.drawSpecimen(g, sp, 70, 110, 0);

// Crop to the creation (plus a margin) and enlarge it, so it fills the picture.
let x0 = 1e9, y0 = 1e9, x1 = -1, y1 = -1;
for (let y = 0; y < canvas.height; y++) for (let x = 0; x < canvas.width; x++)
  if (canvas.px[(y * canvas.width + x) * 4 + 3] > 0.3) { x0 = Math.min(x0, x); y0 = Math.min(y0, y); x1 = Math.max(x1, x); y1 = Math.max(y1, y); }
if (x1 < 0) { x0 = 0; y0 = 0; x1 = 10; y1 = 10; }
const m = 4, out = new Canvas(x1 - x0 + 1 + 2 * m, y1 - y0 + 1 + 2 * m);
out.px = new Float32Array(out.width * out.height * 4);
for (let y = y0; y <= y1; y++) for (let x = x0; x <= x1; x++)
  for (let c = 0; c < 4; c++) out.px[((y - y0 + m) * out.width + (x - x0 + m)) * 4 + c] = canvas.px[(y * canvas.width + x) * 4 + c];
process.stdout.write(png(out, Math.max(2, Math.floor(320 / Math.max(out.width, out.height))), "#efe6d6"));
