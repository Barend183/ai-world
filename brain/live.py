"""Watching him live: while he's awake online, a sealed snapshot of what's changing goes to the `live`
branch about once a minute, so the owner's page can follow him as it happens instead of only replaying
the session afterwards.

The snapshot is sealed exactly like the vault (same password, same salt), so it's as private as the rest
of his world. The branch holds a single commit that is replaced each time, so it never grows, and it
isn't the branch the website is built from, so it doesn't rebuild the page every minute.
"""
import base64
import json
import os
import time

from .world import WORLD, now

FILES = ("self.json", "recent.json", "companions.json", "specimens.json", "rooms.json", "notes.json", "wishlist.json",
         "shelves.json", "goals.json", "music.json", "requests.json", "weather_now.json", "config.json")
EVERY = 45   # seconds between snapshots
_last = 0.0


def enabled():
    from . import vault
    return bool(os.environ.get("GITHUB_ACTIONS") and os.environ.get("GITHUB_TOKEN") and os.environ.get("GITHUB_REPOSITORY")
                and (os.environ.get("WORLD_PASSWORD_NEW") or os.environ.get("WORLD_PASSWORD"))
                and os.path.exists(os.path.join(vault.VAULT, "world.bin")))


def push(force=False):
    """Share a sealed snapshot, at most every EVERY seconds (or now, with force). Never stops his session."""
    global _last
    if not enabled() or (not force and time.time() - _last < EVERY):
        return
    _last = time.time()
    from . import vault
    from .mailbox import _github
    try:
        files = {}
        for name in FILES:
            try:
                with open(os.path.join(WORLD, name), encoding="utf-8") as f:
                    files[name] = f.read()
            except OSError:
                pass
        sealed = vault.seal(json.dumps({"files": files, "at": now()}, ensure_ascii=False).encode(), vault.password())
        repo = os.environ["GITHUB_REPOSITORY"]
        blob = _github("POST", f"/repos/{repo}/git/blobs", {"content": base64.b64encode(sealed).decode(), "encoding": "base64"})
        tree = _github("POST", f"/repos/{repo}/git/trees", {"tree": [{"path": "live.bin", "mode": "100644", "type": "blob", "sha": blob["sha"]}]})
        commit = _github("POST", f"/repos/{repo}/git/commits", {"message": "live", "tree": tree["sha"], "parents": []})
        try:
            _github("PATCH", f"/repos/{repo}/git/refs/heads/live", {"sha": commit["sha"], "force": True})
        except Exception:   # the first time, the branch doesn't exist yet
            _github("POST", f"/repos/{repo}/git/refs", {"ref": "refs/heads/live", "sha": commit["sha"]})
    except Exception as e:
        print("couldn't share the live view:", type(e).__name__)
