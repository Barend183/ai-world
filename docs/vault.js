"use strict";
// The locked world: online, everything he owns is stored encrypted (docs/vault/world.bin). It's unlocked
// here in your browser with your password and never leaves your device unlocked.
// Format (same as brain/vault.py): "AIW1" + salt(16) + nonce(12) + AES-256-GCM(zlib(data)), key = PBKDF2-SHA256(password, salt, 310000).

const Vault = {
  files: null, key: null, salt: null, stamp: null,
  REMEMBER: "aiworld-key",

  async deriveKey(password, salt) {
    const base = await crypto.subtle.importKey("raw", new TextEncoder().encode(password), "PBKDF2", false, ["deriveKey"]);
    return crypto.subtle.deriveKey({ name: "PBKDF2", salt, iterations: 310000, hash: "SHA-256" }, base,
      { name: "AES-GCM", length: 256 }, true, ["encrypt", "decrypt"]);
  },

  async inflate(bytes) {
    return new Uint8Array(await new Response(new Blob([bytes]).stream().pipeThrough(new DecompressionStream("deflate"))).arrayBuffer());
  },
  async deflate(bytes) {
    return new Uint8Array(await new Response(new Blob([bytes]).stream().pipeThrough(new CompressionStream("deflate"))).arrayBuffer());
  },

  async decrypt(blob, key) {
    if (String.fromCharCode(...blob.slice(0, 4)) !== "AIW1") throw new Error("not a locked world file");
    const plain = await crypto.subtle.decrypt({ name: "AES-GCM", iv: blob.slice(20, 32) }, key, blob.slice(32));
    return this.inflate(new Uint8Array(plain));
  },

  async seal(text) {
    const nonce = crypto.getRandomValues(new Uint8Array(12));
    const packed = await this.deflate(new TextEncoder().encode(text));
    const ct = new Uint8Array(await crypto.subtle.encrypt({ name: "AES-GCM", iv: nonce }, this.key, packed));
    const out = new Uint8Array(32 + ct.length);
    out.set(new TextEncoder().encode("AIW1")); out.set(this.salt, 4); out.set(nonce, 20); out.set(ct, 32);
    return out;
  },

  async fetchBlob() {
    const r = await fetch(`vault/world.bin?t=${Date.now()}`, { cache: "no-store" });
    return r.ok ? new Uint8Array(await r.arrayBuffer()) : null;
  },

  // Opens the latest locked world with the key we hold; returns false if the key no longer fits.
  async refresh(blob) {
    blob = blob || await this.fetchBlob();
    if (!blob || !this.key) return false;
    const stamp = blob.length + ":" + Array.from(blob.slice(20, 32)).join(",");
    if (stamp === this.stamp && this.files) return true;
    try {
      const bundle = JSON.parse(new TextDecoder().decode(await this.decrypt(blob, this.key)));
      this.files = bundle.files; this.stamp = stamp;
      return true;
    } catch { return false; }
  },

  async unlock(password, remember) {
    const blob = await this.fetchBlob();
    this.salt = blob.slice(4, 20);
    this.key = await this.deriveKey(password, this.salt);
    if (!(await this.refresh(blob))) { this.key = null; return false; }
    if (remember) {
      const raw = new Uint8Array(await crypto.subtle.exportKey("raw", this.key));
      try { localStorage.setItem(this.REMEMBER, JSON.stringify({ k: Array.from(raw), s: Array.from(this.salt) })); } catch {}
    }
    return true;
  },

  async tryRemembered() {
    let saved;
    try { saved = JSON.parse(localStorage.getItem(this.REMEMBER) || "null"); } catch { saved = null; }
    if (!saved) return false;
    this.salt = new Uint8Array(saved.s);
    this.key = await crypto.subtle.importKey("raw", new Uint8Array(saved.k), "AES-GCM", true, ["encrypt", "decrypt"]);
    if (await this.refresh()) return true;
    this.forget();
    return false;
  },

  forget() {
    try { localStorage.removeItem(this.REMEMBER); localStorage.removeItem("aiworld-github"); } catch {}
    this.key = null; this.files = null;
  },

  text(name) {
    const v = this.files && this.files[name];
    return typeof v === "string" ? v : null;
  },

  // Sends a sealed note (or an answer to one of his requests) into his vault inbox on GitHub.
  async send(repo, entry) {
    let token;
    try { token = localStorage.getItem("aiworld-github"); } catch { token = null; }
    if (!token) {
      token = prompt("To send notes from this page, paste a GitHub token that can write to your ai-world repository (see the guide). It's kept only on this device.");
      if (!token) throw new Error("no token");
      try { localStorage.setItem("aiworld-github", token.trim()); } catch {}
    }
    const sealed = await this.seal(JSON.stringify(entry));
    let b64 = ""; for (const byte of sealed) b64 += String.fromCharCode(byte);
    const path = `docs/vault/inbox/${Date.now()}.bin`;
    const r = await fetch(`https://api.github.com/repos/${repo}/contents/${path}`, {
      method: "PUT",
      headers: { Authorization: `Bearer ${token.trim()}`, Accept: "application/vnd.github+json" },
      body: JSON.stringify({ message: "📬", content: btoa(b64) }),
    });
    if (r.status === 401 || r.status === 403) { try { localStorage.removeItem("aiworld-github"); } catch {} throw new Error("GitHub refused the token"); }
    if (!r.ok) throw new Error(`GitHub said ${r.status}`);
  },
};
