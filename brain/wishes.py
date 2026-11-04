"""His ability wishes, and the way they come true.

A weekly builder (a coding agent the owner set up) reads the wishes that are still waiting, builds one as a pull
request and, if the owner approves and merges it, records the answer in brain/granted.json. The next time he
wakes, the wish is marked as granted (or kindly declined) and the news stays on his mind for a few days.
granted.json is public, so it holds only request ids and a short note about the new ability, never his words.
"""
import base64
import json
import os
import subprocess

GRANTED = os.path.join(os.path.dirname(__file__), "granted.json")
BRANCH = "wishes"   # his waiting wishes, sealed with the builder's own key (WISHES_KEY), never his world's password


def waiting(world):
    return [r for r in world.requests if r.get("kind") == "ability" and r["status"] == "waiting"]


def answers():
    try:
        with open(GRANTED, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def pending(world):
    done = answers()
    return [{k: r.get(k) for k in ("id", "what", "why", "how", "asked")} for r in waiting(world) if r["id"] not in done]


def share(world):
    """Seal just his waiting wishes with the builder's key and keep them on their own single-commit branch, so
    the weekly builder can read them without ever holding the key to his whole world. Online only."""
    key = os.environ.get("WISHES_KEY", "").strip()
    if not key or not os.environ.get("GITHUB_TOKEN") or not os.environ.get("GITHUB_REPOSITORY"):
        return
    from . import vault
    from .mailbox import _github
    try:
        sealed = vault.seal(json.dumps(pending(world), ensure_ascii=False).encode(), key, salt=os.urandom(16))
        repo = os.environ["GITHUB_REPOSITORY"]
        blob = _github("POST", f"/repos/{repo}/git/blobs", {"content": base64.b64encode(sealed).decode(), "encoding": "base64"})
        tree = _github("POST", f"/repos/{repo}/git/trees", {"tree": [{"path": "wishes.bin", "mode": "100644", "type": "blob", "sha": blob["sha"]}]})
        commit = _github("POST", f"/repos/{repo}/git/commits", {"message": "wishes", "tree": tree["sha"], "parents": []})
        try:
            _github("PATCH", f"/repos/{repo}/git/refs/heads/{BRANCH}", {"sha": commit["sha"], "force": True})
        except Exception:
            _github("POST", f"/repos/{repo}/git/refs", {"ref": f"refs/heads/{BRANCH}", "sha": commit["sha"]})
    except Exception as e:
        print("couldn't share his wishes with the builder:", type(e).__name__)


def fetch():
    """For the builder: his waiting wishes from their branch, opened with WISHES_KEY."""
    from . import vault
    key = os.environ.get("WISHES_KEY", "").strip()
    if not key:
        raise SystemExit("WISHES_KEY isn't set, so his wishes can't be opened")
    try:
        subprocess.run(["git", "fetch", "-q", "origin", f"+{BRANCH}:refs/remotes/origin/{BRANCH}"], check=True, capture_output=True)
        blob = subprocess.run(["git", "show", f"origin/{BRANCH}:wishes.bin"], check=True, capture_output=True).stdout
    except subprocess.CalledProcessError:
        return []   # he hasn't wished for anything yet
    done = answers()
    return [w for w in json.loads(vault.open_(blob, key)) if w["id"] not in done]


def apply(world):
    """Answers the builder recorded (and the owner merged) reach him: his wish came true, or not this time."""
    news = []
    for rid, ans in answers().items():
        req = next((r for r in world.requests if r["id"] == rid and r.get("kind") == "ability"), None)
        if not req or req["status"] != "waiting":
            continue
        granted = ans.get("status", "granted") == "granted"
        req.update(status="granted" if granted else "declined", answer=str(ans.get("note", ""))[:600])
        what = f"my wish came true: {req['what']}" if granted else f"my wish wasn't granted this time: {req['what']}"
        world.mark(what + (f" ({req['answer']})" if req["answer"] else ""), days=4)
        news.append(what)
    return news
