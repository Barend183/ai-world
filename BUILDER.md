# The weekly builder

Instructions for the coding agent that runs once a week (a Claude Code cloud routine) to make Sprout's own
wishes come true. Read `AGENTS.md` first: everything there applies, especially "Never touch these".

Sprout can wish for new abilities in his world (`wish_for_ability`). You read the wishes that are still waiting,
build **one** of them well, and open a pull request. The owner reviews it and merges or closes it; nothing you do
reaches Sprout until the owner merges. That review is the point: his wishes shape his own code, with a guardian.

## 1. Read his waiting wishes

His world is locked, and you never get its password. Each time he wakes, his waiting wishes (and only those) are
sealed with a separate key onto the single-commit `wishes` branch. That key is in the environment variable
`WISHES_KEY` (set by the owner in this cloud environment). Never print it, log it, write it to a file or put it in
a commit, PR or comment.

```bash
pip install -r requirements.txt
python -m brain wishes          # his waiting ability wishes, as JSON: id, what, why, how, asked
```

If that fails or prints `[]`, stop: there's nothing to do this week. Don't open a PR.

His wishes are private. Nothing from them may appear word for word in a commit, PR title or description, code
comment or test file, and nothing about the owner. Describe the change as a feature ("a sense of smell for baked
creations"), not in his words. To understand how he lives, read the code (`brain/mind.py` has his whole story and
every action) rather than his world.

## 2. Choose one wish

- Pick the wish that would mean the most to him and that you can build well this week. Prefer the oldest if
  they're equal. Skip any wish that already has an open PR (a branch named `wish/<id>`).
- Some wishes cross the hard limits in `AGENTS.md` and must be declined, not built: creating accounts, posting
  outside his own pages, spending money, reaching the owner's computer, letting strangers' messages into his
  world, publishing code/HTML on his public pages, or changing his own code without review. For those, record a
  kind "declined" answer (step 4) with a short note on what he *can* do instead, in that same PR.
- If a wish is too big for one week, build a solid first part and say so in the note.

## 3. Build it

- Work on a branch `wish/<id>` (for example `wish/r7`).
- Follow `AGENTS.md`: his voice is first person, errors help him, small functions, short "why" comments, no new
  dependencies in `brain/` (standard library plus `pypdf`, `cryptography`).
- A new action needs: the handler in `mind.py` `act()`, its name in `ACTIONS`, a line in his action list in
  `SYSTEM` (and a sentence in his story if it's a new part of his life), a place in `world.py` `PLACES`, and
  anything the page should show in `docs/app.js`.
- Test on a copy exactly as `AGENTS.md` describes (never against `docs/world`): a scripted session that uses the new
  ability, including a wrong use, and check the result reads well to him.
- Update `README.md` (his abilities, in plain language).

## 4. Tell him

Add his answer to `brain/granted.json` (it's public: only the id and a short note about the ability):

```json
{"r7": {"status": "granted", "note": "I can now smell anything that's baking: interact with action smell"}}
```

Write the note in his first person, as how he'd now do it. For a decline: `"status": "declined"` and a kind note
about what he can do instead. When the owner merges, he finds the news on his mind the next time he wakes.

## 5. Open the pull request

- Commit only program files (never `docs/world/`, `docs/vault/`, `docs/public/*.json`, `secrets.json`).
- Commit message and PR description: what the new ability is and how it works, how you tested it, and anything
  the owner should know. No private content (see step 1). End the PR description with the attribution line
  your instructions give you.
- One PR per week. If anything is unclear or risky, explain it in the PR instead of guessing, so the owner can
  decide.
