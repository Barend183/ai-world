"use strict";
// The sound of his world, made live in your browser from the same real weather he hears:
// rain, wind, birds at dawn and crickets on warm nights. Muffled indoors, open in his outdoor rooms.

const Ambience = {
  ctx: null, on: false, parts: null, timer: null,

  noise(ctx) {   // two seconds of white noise, looped
    const buf = ctx.createBuffer(1, ctx.sampleRate * 2, ctx.sampleRate), d = buf.getChannelData(0);
    for (let i = 0; i < d.length; i++) d[i] = Math.random() * 2 - 1;
    const src = ctx.createBufferSource(); src.buffer = buf; src.loop = true; src.start();
    return src;
  },

  start(conditions) {
    this.conditions = conditions;
    const c = this.ctx = this.ctx || new (window.AudioContext || window.webkitAudioContext)();
    c.resume();
    if (!this.parts) {
      const master = c.createGain(); master.gain.value = 0.9;
      const muffle = c.createBiquadFilter(); muffle.type = "lowpass"; muffle.frequency.value = 18000;
      muffle.connect(master).connect(c.destination);
      // rain: bright hiss
      const rainF = c.createBiquadFilter(); rainF.type = "highpass"; rainF.frequency.value = 900;
      const rain = c.createGain(); rain.gain.value = 0;
      this.noise(c).connect(rainF).connect(rain).connect(muffle);
      // wind: low, slowly swelling rush
      const windF = c.createBiquadFilter(); windF.type = "bandpass"; windF.frequency.value = 400; windF.Q.value = 0.7;
      const wind = c.createGain(); wind.gain.value = 0;
      const swell = c.createOscillator(), swellDepth = c.createGain();
      swell.frequency.value = 0.12; swellDepth.gain.value = 0; swell.connect(swellDepth).connect(wind.gain); swell.start();
      const gust = c.createOscillator(), gustDepth = c.createGain();
      gust.frequency.value = 0.07; gustDepth.gain.value = 250; gust.connect(gustDepth).connect(windF.frequency); gust.start();
      this.noise(c).connect(windF).connect(wind).connect(muffle);
      this.parts = { master, muffle, rain, wind, swellDepth };
    }
    this.on = true;
    this.update();
    clearInterval(this.timer);
    this.timer = setInterval(() => this.update(), 1500);
  },

  stop() {
    this.on = false; clearInterval(this.timer);
    if (this.parts) { this.parts.rain.gain.value = 0; this.parts.wind.gain.value = 0; this.parts.swellDepth.gain.value = 0; }
  },

  update() {
    if (!this.on) return;
    const w = this.conditions() || {}, p = this.parts, c = this.ctx, now = c.currentTime;
    const outdoors = !!w.outdoors, rain = w.env_rain || 0, wind = w.env_wind || 0;
    p.muffle.frequency.setTargetAtTime(outdoors ? 16000 : 1400, now, 0.5);   // indoors: heard through the window
    p.rain.gain.setTargetAtTime(rain > 0 ? Math.min(0.5, 0.08 + rain * 0.08) : 0, now, 1);
    const windLevel = wind < 5 ? 0 : Math.min(0.6, (wind - 5) / 50);
    p.wind.gain.setTargetAtTime(windLevel * 0.6, now, 1.5);
    p.swellDepth.gain.setTargetAtTime(windLevel * 0.4, now, 1.5);
    const hour = w.env_hour ?? 12, day = w.env_daylight ?? 1;
    const vol = outdoors ? 1 : 0.35;
    if (day && rain === 0 && wind < 25 && Math.random() < (hour >= 5 && hour <= 9 ? 0.75 : 0.2)) this.bird(vol);
    if (!day && rain === 0 && wind < 15 && (w.env_temp ?? 0) > 15 && Math.random() < 0.6) this.cricket(vol);
  },

  bird(vol) {   // a short song of a few rising and falling chirps
    const c = this.ctx, start = c.currentTime + Math.random() * 1.2, base = 2200 + Math.random() * 1800;
    const notes = 2 + Math.floor(Math.random() * 5);
    for (let i = 0; i < notes; i++) {
      const t = start + i * (0.09 + Math.random() * 0.08), o = c.createOscillator(), g = c.createGain();
      const f = base * (0.85 + Math.random() * 0.4);
      o.frequency.setValueAtTime(f, t); o.frequency.exponentialRampToValueAtTime(f * (Math.random() < 0.5 ? 1.35 : 0.7), t + 0.07);
      g.gain.setValueAtTime(0.0001, t); g.gain.exponentialRampToValueAtTime(0.05 * vol, t + 0.01); g.gain.exponentialRampToValueAtTime(0.0001, t + 0.08);
      o.connect(g).connect(this.parts.muffle); o.start(t); o.stop(t + 0.1);
    }
  },

  cricket(vol) {   // a quick trill of high pulses
    const c = this.ctx, start = c.currentTime + Math.random();
    for (let i = 0; i < 6; i++) {
      const t = start + i * 0.045, o = c.createOscillator(), g = c.createGain();
      o.frequency.value = 4300;
      g.gain.setValueAtTime(0.0001, t); g.gain.exponentialRampToValueAtTime(0.025 * vol, t + 0.005); g.gain.exponentialRampToValueAtTime(0.0001, t + 0.03);
      o.connect(g).connect(this.parts.muffle); o.start(t); o.stop(t + 0.04);
    }
  },
};
