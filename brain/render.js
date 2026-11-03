// Draws one creation exactly as the web page does, and prints it as a PNG, so the AI can see it.
// Usage: node render.js < specimen.json > picture.png   (runs docs/sprites.js against a tiny pretend canvas)
"use strict";
const fs = require("fs"), path = require("path"), vm = require("vm"), zlib = require("zlib");

const { Canvas, png } = require("./canvas.js");

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
