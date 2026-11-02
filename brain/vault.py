"""Keeps the AI's world locked while it lives in a public GitHub repository.

Everything it owns is stored encrypted in docs/vault/ (AES-256-GCM, key from your password with
PBKDF2-SHA256), so anyone browsing the repository sees only scrambled data. The plain world in
docs/world/ exists only while it's awake on GitHub's throwaway server (and on your PC); it's
never uploaded. The web page unlocks the same files in your browser with the same password.

File format: b"AIW1" + salt (16 bytes) + nonce (12 bytes) + AES-GCM(zlib(data)).
"""
import base64
import glob
import hashlib
import json
import os
import zlib

from .world import ROOT, WORLD

VAULT = os.path.join(ROOT, "docs", "vault")
MAGIC = b"AIW1"
ITERATIONS = 310_000
SKIP = {"inbox", "weather.json", "journal"}   # not bundled: delivered notes, the weather cache, the journal (kept per month)
_keys = {}


def password():
    pw = os.environ.get("WORLD_PASSWORD", "")
    if not pw:
        raise SystemExit("WORLD_PASSWORD isn't set, so the world can't be locked or unlocked.")
    return pw


def _key(pw, salt):
    if (pw, salt) not in _keys:
        _keys[(pw, salt)] = hashlib.pbkdf2_hmac("sha256", pw.encode(), salt, ITERATIONS, 32)
    return _keys[(pw, salt)]


def _salt():
    """The vault keeps one salt, so a key remembered by the web page keeps working after each update."""
    path = os.path.join(VAULT, "world.bin")
    if os.path.exists(path):
        with open(path, "rb") as f:
            head = f.read(20)
        if head[:4] == MAGIC:
            return head[4:20]
    return os.urandom(16)


def seal(data, pw, salt=None):
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    salt = salt or _salt()
    nonce = os.urandom(12)
    return MAGIC + salt + nonce + AESGCM(_key(pw, salt)).encrypt(nonce, zlib.compress(data, 9), None)


def open_(blob, pw):
    from cryptography.exceptions import InvalidTag
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    if blob[:4] != MAGIC:
        raise ValueError("not a locked world file")
    salt, nonce = blob[4:20], blob[20:32]
    try:
        return zlib.decompress(AESGCM(_key(pw, salt)).decrypt(nonce, blob[32:], None))
    except InvalidTag:
        raise ValueError("wrong password (or the file was damaged)")


def _write(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(data)


def lock():
    """Seal docs/world into docs/vault. Returns how many files changed."""
    pw = password()
    files = {}
    for path in glob.glob(os.path.join(WORLD, "**", "*"), recursive=True):
        rel = os.path.relpath(path, WORLD).replace(os.sep, "/")
        if os.path.isfile(path) and rel.split("/")[0] not in SKIP and not rel.endswith(".tmp") and rel != ".gitkeep":
            with open(path, "rb") as f:
                raw = f.read()
            try:
                files[rel] = raw.decode("utf-8")
            except UnicodeDecodeError:   # pictures and other non-text files from his workshop
                files[rel] = {"b64": base64.b64encode(raw).decode()}
    # Journal months: re-sealed only when they changed, so old months don't churn in git.
    old = _bundle_hashes(pw)
    hashes, changed = {}, 0
    for path in sorted(glob.glob(os.path.join(WORLD, "journal", "*.jsonl"))):
        month = os.path.basename(path)[:-6]
        with open(path, "rb") as f:
            raw = f.read()
        hashes[month] = hashlib.sha256(raw).hexdigest()
        target = os.path.join(VAULT, "journal", month + ".bin")
        if old.get(month) != hashes[month] or not os.path.exists(target):
            _write(target, seal(raw, pw))
            changed += 1
    bundle = json.dumps({"files": files, "journal": hashes}, ensure_ascii=False, sort_keys=True).encode()
    if bundle != _current_bundle(pw):   # unchanged (he slept through this check): leave the sealed file alone
        _write(os.path.join(VAULT, "world.bin"), seal(bundle, pw))
        changed += 1
    # notes that were delivered this session are gone from the vault inbox
    taken = os.path.join(WORLD, ".inbox_taken")
    if os.path.exists(taken):
        with open(taken, encoding="utf-8") as f:
            for name in f.read().split():
                p = os.path.join(VAULT, "inbox", name)
                if os.path.exists(p):
                    os.remove(p)
        os.remove(taken)
    return changed


def _current_bundle(pw):
    path = os.path.join(VAULT, "world.bin")
    if not os.path.exists(path):
        return None
    try:
        with open(path, "rb") as f:
            return json.dumps(json.loads(open_(f.read(), pw)), ensure_ascii=False, sort_keys=True).encode()
    except ValueError:
        return None


def _bundle_hashes(pw):
    path = os.path.join(VAULT, "world.bin")
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "rb") as f:
            return json.loads(open_(f.read(), pw)).get("journal", {})
    except ValueError:
        return {}


def unlock():
    """Open docs/vault into docs/world (plus any sealed notes waiting in the vault inbox)."""
    pw = password()
    path = os.path.join(VAULT, "world.bin")
    if not os.path.exists(path):
        print("No locked world yet: he starts fresh.")
        return False
    with open(path, "rb") as f:
        bundle = json.loads(open_(f.read(), pw))
    for rel, text in bundle["files"].items():
        if ".." in rel.split("/"):
            continue
        data = base64.b64decode(text["b64"]) if isinstance(text, dict) else text.encode("utf-8")
        _write(os.path.join(WORLD, *rel.split("/")), data)
    for month_file in glob.glob(os.path.join(VAULT, "journal", "*.bin")):
        with open(month_file, "rb") as f:
            _write(os.path.join(WORLD, "journal", os.path.basename(month_file)[:-4] + ".jsonl"), open_(f.read(), pw))
    taken = []
    for note_file in sorted(glob.glob(os.path.join(VAULT, "inbox", "*.bin"))):
        name = os.path.basename(note_file)
        try:
            with open(note_file, "rb") as f:
                note = json.loads(open_(f.read(), pw))
        except (ValueError, json.JSONDecodeError):
            print("A note in the inbox couldn't be opened and was left alone.")
            continue
        _write(os.path.join(WORLD, "inbox", name[:-4] + ".json"), json.dumps(note).encode())
        taken.append(name)
    if taken:
        _write(os.path.join(WORLD, ".inbox_taken"), "\n".join(taken).encode())
    return True
