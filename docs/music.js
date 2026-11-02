"use strict";
// Plays the music he composes: notes like "C4:1 E4:1 G4:2 R:1" (note+octave:beats; R is a rest).

const Music = {
  ctx: null, playing: null,
  SEMI: { C: 0, D: 2, E: 4, F: 5, G: 7, A: 9, B: 11 },

  freq(note) {
    const m = /^([A-Ga-g])([#b]?)([0-8])$/.exec(note);
    if (!m) return 0;
    const n = this.SEMI[m[1].toUpperCase()] + (m[2] === "#" ? 1 : m[2] === "b" ? -1 : 0) + (+m[3] + 1) * 12;
    return 440 * Math.pow(2, (n - 69) / 12);
  },

  // schedules one voice; returns when it ends (seconds from now)
  voice(text, start, beat, instrument, gainLevel) {
    let t = start;
    for (const tok of (text || "").split(/\s+/).filter(Boolean)) {
      const [note, beats] = tok.split(":");
      const dur = (+beats || 1) * beat;
      if (note !== "R") {
        const f = this.freq(note);
        if (f) this.tone(f, t, dur, instrument, gainLevel);
      }
      t += dur;
    }
    return t;
  },

  tone(f, t, dur, instrument, level) {
    const c = this.ctx, osc = c.createOscillator(), g = c.createGain();
    const shape = { piano: "triangle", organ: "square", flute: "sine" }[instrument] || instrument || "triangle";
    osc.type = shape; osc.frequency.value = f;
    const peak = level * (shape === "square" || shape === "sawtooth" ? 0.35 : 1);
    g.gain.setValueAtTime(0.0001, t);
    g.gain.exponentialRampToValueAtTime(peak, t + 0.02);
    const tail = instrument === "piano" ? Math.max(dur, 0.3) : dur;   // a piano note rings and fades
    if (instrument === "piano") g.gain.exponentialRampToValueAtTime(0.0001, t + tail);
    else { g.gain.setValueAtTime(peak, t + Math.max(0.02, dur - 0.05)); g.gain.exponentialRampToValueAtTime(0.0001, t + dur); }
    osc.connect(g).connect(c.destination);
    osc.start(t); osc.stop(t + tail + 0.05);
    this.playing.push(osc);
  },

  play(piece, onEnd) {
    this.stop();
    this.ctx = this.ctx || new (window.AudioContext || window.webkitAudioContext)();
    this.ctx.resume();
    this.playing = [];
    const beat = 60 / (piece.tempo || 100), start = this.ctx.currentTime + 0.1;
    const end = Math.max(this.voice(piece.melody, start, beat, piece.instrument, 0.18),
                         this.voice(piece.bass, start, beat, piece.instrument, 0.1));
    this.timer = setTimeout(() => { this.playing = null; onEnd && onEnd(); }, (end - this.ctx.currentTime) * 1000 + 200);
  },

  stop() {
    (this.playing || []).forEach((o) => { try { o.stop(); } catch {} });
    this.playing = null; clearTimeout(this.timer);
  },
};
