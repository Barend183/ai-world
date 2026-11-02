"""Notes from the visitor.

Online, a note is a GitHub issue opened by the repository's owner
(issues from anyone else are ignored, so strangers can't talk the AI into things).
The AI replies by commenting and closing the issue.
On your PC, the local server drops notes into docs/world/inbox/.
"""
import glob
import json
import os
import urllib.request

from .world import _path

API = "https://api.github.com"


def _github(method, path, body=None):
    req = urllib.request.Request(API + path, method=method, data=json.dumps(body).encode() if body else None, headers={
        "Authorization": "Bearer " + os.environ["GITHUB_TOKEN"],
        "Accept": "application/vnd.github+json",
        "User-Agent": "ai-world",
    })
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read() or b"null")


def _online():
    return os.environ.get("GITHUB_TOKEN") and os.environ.get("GITHUB_REPOSITORY")


def _locked():
    """In a locked world nothing personal may appear on GitHub: notes arrive sealed in the vault,
    and GitHub only gets a content-free "you've got mail" notice."""
    return bool(os.environ.get("WORLD_PASSWORD") or os.environ.get("WORLD_PASSWORD_NEW"))


def _notice(title):
    try:
        _github("POST", f"/repos/{os.environ['GITHUB_REPOSITORY']}/issues",
                {"title": title, "body": "Open his world and unlock it with your password to read it."})
    except Exception as e:
        print("couldn't send the notice:", e)


def _answer(world, rid, decision, message):
    req = next((r for r in world.requests if r["id"] == rid), None)
    if req and decision in ("granted", "declined", "waiting", "answered"):
        req.update(status=decision, answer=(message or "").strip()[:800] or None, answered=now_iso())


def now_iso():
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def collect(world):
    for path in sorted(glob.glob(_path("inbox", "*.json"))):
        try:
            with open(path, encoding="utf-8") as f:
                note = json.load(f)
            if note.get("answer_for"):   # the owner answered one of his requests on the page
                _answer(world, note["answer_for"], note.get("decision"), note.get("text"))
            else:
                world.add_note(note.get("from") or "Visitor", note.get("text", ""), "local")
        except (OSError, json.JSONDecodeError):
            pass
        os.remove(path)

    if _online() and not _locked():
        repo, owner = os.environ["GITHUB_REPOSITORY"], os.environ.get("GITHUB_REPOSITORY_OWNER", "")
        seen = {n.get("ref") for n in world.notes if n["source"] == "github"}
        try:
            issues = _github("GET", f"/repos/{repo}/issues?state=open&creator={owner}&per_page=20")
        except Exception as e:
            print("couldn't check notes:", e)
            return
        for req in world.requests:   # the owner's reply on a request issue is the answer
            if req.get("ref") and req["status"] == "waiting":
                try:
                    comments = _github("GET", f"/repos/{repo}/issues/{req['ref']}/comments")
                except Exception:
                    continue
                mine = [c for c in comments if c["user"]["login"].lower() == owner.lower()]
                if mine:
                    _answer(world, req["id"], "answered", mine[-1]["body"])
        for issue in issues:
            if issue["number"] in seen or "pull_request" in issue or issue["user"]["login"].lower() != owner.lower():
                continue
            text = issue["title"] + ("\n" + issue["body"] if issue.get("body") else "")
            world.add_note(issue["user"]["login"], text, "github", issue["number"])


def send_letter(letter):
    """Online, a letter becomes a GitHub issue in the owner's repository, so it reaches them."""
    if not _online():
        return
    if _locked():
        return _notice("📬 You have a new letter in your AI's world")
    try:
        issue = _github("POST", f"/repos/{os.environ['GITHUB_REPOSITORY']}/issues",
                        {"title": f"A letter from {letter['from']}", "body": letter["text"]})
        letter["ref"] = issue.get("number")
    except Exception as e:
        print("couldn't send letter:", e)


def send_request(req, name):
    """Online, a request becomes a GitHub issue the owner can answer."""
    if not _online():
        return
    if _locked():
        return _notice("🙋 Your AI has a new request for you")
    try:
        body = f"**What:** {req['what']}\n\n**Why:** {req['why']}\n\n(Reply here, or tell {name} in a note, whether you'll do it.)"
        issue = _github("POST", f"/repos/{os.environ['GITHUB_REPOSITORY']}/issues", {"title": f"{name} asks: {req['what'][:80]}", "body": body})
        req["ref"] = issue.get("number")
    except Exception as e:
        print("couldn't send request:", e)


def send_reply(note):
    if note["source"] != "github" or not _online() or _locked():
        return
    repo = os.environ["GITHUB_REPOSITORY"]
    try:
        _github("POST", f"/repos/{repo}/issues/{note['ref']}/comments", {"body": note["reply"]})
        _github("PATCH", f"/repos/{repo}/issues/{note['ref']}", {"state": "closed"})
    except Exception as e:
        print("couldn't post reply:", e)
