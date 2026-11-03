"use strict";
// Shared by his public corner and his websites. Everything he wrote is escaped first and only his design
// choices are applied (colours checked as #rrggbb, fonts from a fixed list), so his text never becomes code.

const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const FONTS = { plain: "system-ui, sans-serif", serif: "Georgia, 'Times New Roman', serif", mono: "ui-monospace, Consolas, monospace",
  rounded: "'Trebuchet MS', 'Segoe UI', sans-serif", handwritten: "'Comic Sans MS', 'Segoe Print', cursive" };
const HEX = /^#[0-9a-f]{6}$/i;

// site: links written [text](page:<id>) go to that page of this website; [[picture:<name>]] shows one of his drawings.
function inline(s, site) {
  return s.replace(/`([^`]+)`/g, "<code>$1</code>").replace(/\*\*([^*]+)\*\*/g, "<b>$1</b>")
    .replace(/(^|[^*])\*([^*\s][^*]*)\*/g, "$1<i>$2</i>")
    .replace(/\[\[picture:([a-z0-9-]+)\]\]/g, '<canvas class="art" data-pic="$1"></canvas>')
    .replace(/\[([^\]]+)\]\(page:([a-z0-9-]+)\)/g, (m, text, id) => site ? `<a href="site.html?s=${encodeURIComponent(site)}&amp;p=${id}">${text}</a>` : text)
    .replace(/\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g, '<a href="$2" target="_blank" rel="noopener nofollow">$1</a>');
}
function markdown(md, site) {
  const out = []; let list = null, para = [];
  const flush = () => { if (para.length) { out.push(`<p>${inline(para.join(" "), site)}</p>`); para = []; } if (list) { out.push(`</${list}>`); list = null; } };
  for (const raw of esc(md).split("\n")) {
    const line = raw.trim(); let m;
    if (!line) { flush(); continue; }
    if ((m = line.match(/^(#{1,4})\s+(.*)/))) { flush(); out.push(`<h${m[1].length + 1}>${inline(m[2], site)}</h${m[1].length + 1}>`); continue; }
    if ((m = line.match(/^([-*]|\d+\.)\s+(.*)/))) {
      const want = /\d/.test(m[1]) ? "ol" : "ul";
      if (para.length) { out.push(`<p>${inline(para.join(" "), site)}</p>`); para = []; }
      if (list !== want) { if (list) out.push(`</${list}>`); out.push(`<${want}>`); list = want; }
      out.push(`<li>${inline(m[2], site)}</li>`); continue;
    }
    if (list) { out.push(`</${list}>`); list = null; }
    para.push(line);
  }
  flush(); return out.join("\n");
}

function applyLook(d) {
  const root = document.documentElement.style, c = (d && d.colors) || {};
  const set = (v, x) => { if (HEX.test(x || "")) root.setProperty(v, x); };
  set("--bg", c.background); set("--card", c.card); set("--ink", c.text); set("--accent", c.accent);
  if (HEX.test(c.text || "") && HEX.test(c.background || "")) {
    root.setProperty("--muted", `color-mix(in srgb, ${c.text} 62%, ${c.background})`);
    root.setProperty("--line", `color-mix(in srgb, ${c.text} 16%, ${c.background})`);
  }
  if (HEX.test(c.background || "")) document.body.style.background = c.background;
  if (HEX.test(c.text || "")) document.body.style.color = c.text;
  if (d && FONTS[d.font]) document.body.style.fontFamily = FONTS[d.font];
}

function drawBanner(cv, b) {
  if (!b || !b.pixels || !b.pixels.length) return;
  const w = Math.max(...b.pixels.map((r) => r.length)), h = b.pixels.length;
  cv.width = w; cv.height = h; cv.hidden = false;
  cv.style.maxWidth = Math.min(w * 6, 820) + "px";
  Px.art(cv.getContext("2d"), b, b.pixels, w / 2, h);
}

function drawArt(c, art) {
  const rows = art.pixels, w = Math.max(...rows.map((r) => r.length)), h = rows.length;
  c.width = w + 8; c.height = h + 8;
  Px.art(c.getContext("2d"), art, rows, c.width / 2, h + 4);
}
