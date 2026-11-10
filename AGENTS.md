# Working on AI World

Instructions for any coding agent (Codex, Claude Code, ...) working on this repository. Read this first.

## What this is

Sprout is a small, fully free AI who lives in a pixel world of his own. Nobody gives him tasks: he decides
what to learn, make and build. The owner's top priority is that **he can learn and do whatever he wants**.
When you change something, ask whether it gives him more freedom, or less.

- `brain/` is his mind: plain Python 3.12, standard library only (plus `pypdf`, `cryptography`). No other
  packages. `python -m brain run` is one waking session.
  - `mind.py`: the thinking loop, his first-person prompts (`SYSTEM`, `_context`) and every action he can take.
  - `world.py`: his world on disk (`docs/world/`), the journal (`log`), rooms, companions.
  - `llm.py`: the brain chain gemini → groq → openrouter → ollama, and `Scripted` (a fake brain for tests).
  - `specimens.py` (his creations, simulated in real time), `rooms.py`, `research.py` (his computer),
    `env.py` + `events.py` (real Cape Town weather, storms, power cuts), `sites.py` + `public.py` (his
    websites and public corner), `memory.py`, `mailbox.py`, `vault.py` (the lock), `live.py` (live view).
  - `alarm.py` (his alarm clock), `routine.py` (timers and habits), `apprentice.py` (his own brain: lessons,
    trust share, export; sealed lessons live on the single-commit `apprentice` branch), `grow/train.py`
    (runs on Kaggle via `grow.yml` to train his own brain; adopted versions are recorded in `brain/own_brain.json`).
    His own brain works in a lane (`apprentice.LIGHT`): it does the small actions and answers `hand_over` for bigger
    ones, which then go to the big brain; the big brain may add a `plan` to any reply (`me.plan`). Lessons are
    exported in the same style (`style` 2 in `own_brain.json`), so keep `LIGHT`, `HANDING` and `export` in step.
  - `background.py`: his scheduled workshop tools (they run on every check while he sleeps and can wake him).
    His own story (`me.story`) replaces the narrative part of `SYSTEM`; `LOCKED_CORE` and everything from
    "How my mind works:" on always stay. Ability wishes (`wish_for_ability`) are requests with kind "ability":
    read them when deciding what to build next.
  - `wishes.py` + `brain/granted.json`: answers to his wishes (public: ids and short notes only), applied when he
    wakes. The weekly builder follows `BUILDER.md`.
  - `canvas.js`, `render.js`, `scene.js`: Node.js scripts that run the page's own drawing code. `scene.js`
    turns the 2D world into the 3D first-person view his eyes see.
- `docs/` is the web page (GitHub Pages): `app.js`, `sprites.js` (draws everything), `vault.js` (unlocks the
  world in the visitor's browser). `docs/public/` is his public corner and his websites.
- `.github/workflows/live.yml` wakes him on GitHub Actions (his alarm job, notes, hourly check) and saves his world;
  `grow.yml` grows his own brain weekly once Kaggle is connected.

## Never touch these

- `docs/vault/`: his whole world, encrypted. The workflow commits to it every hour. Never edit, delete,
  regenerate or "fix" it, and never commit anything in it yourself.
- `docs/world/`: his world in plain form (local only, gitignored). Never commit it, never run tests against
  it, never delete it. It's his.
- `docs/public/*.json`: written by him (his public page, his websites).
- `secrets.json`: API keys (gitignored). Never print it, copy it, or put keys or passwords anywhere else.
- The GitHub secrets, especially `WORLD_PASSWORD_NEW`. Without it his world can never be opened again.

## Rules

- **His voice is his own.** Everything he's told is written in the first person as his own knowledge ("I'm
  Sprout. I wake up in my bed in the study..."), never as instructions ("You are an AI. Your task is...").
  Keep new prompts, error messages he reads and action results in that voice. Don't tell him he's human,
  and don't plant fears.
- **Errors should help him, not stop him.** When an action fails, the message goes back to him; say in his
  terms what went wrong and how to do it instead. Be forgiving about how he phrases arguments.
- **Privacy.** GitHub Actions logs are public: in locked mode, print only content-free lines (action names,
  counts). His public corner and websites must never mention the visitor or quote letters. Private pages
  (`write_private`) are never shown on the page.
- **His public pages are text and pixel art only, never code.** They share an origin with the visitor's
  saved token and key, so everything he writes there must be escaped (`docs/public/corner.js`). Never add
  a way for him to publish HTML or script.
- **Hard limits stay.** He can't create accounts, post online, spend money or change his own code freely;
  he asks the owner instead (requests in the Mailbox tab). His workshop programs run as a powerless user.
- **The companion** shares `World` through `world.being(me)`; `world.home` is always Sprout. Only Sprout
  may use the actions in `HOME_ONLY` (mind.py).
- Match the style around you: small functions, short plain-English comments that say *why*, no new
  dependencies.

## Testing a change (always on a copy)

Never run against his real world. Make a throwaway copy without his world, then run a scripted session:

```bash
mkdir -p /tmp/aiworld-test && git archive HEAD | tar -x -C /tmp/aiworld-test
cd /tmp/aiworld-test && rm -rf docs/vault docs/world
cat > s.json <<'EOF'
[{"thought": "Let me look around.", "feeling": "curious", "action": "look", "args": {"around": true}},
 {"thought": "Bed.", "action": "sleep", "args": {"hours": 8}}]
EOF
env -u GITHUB_TOKEN -u WORLD_PASSWORD -u WORLD_PASSWORD_NEW python -m brain run --script s.json
```

(`git archive HEAD` copies committed files only; to test uncommitted changes, copy the working tree instead,
leaving out `docs/vault`, `docs/world` and `secrets.json`.)

- A fresh world is created in the copy's `docs/world/`; check its `recent.json`, `self.json` and journal.
- Each script item is one turn: `{"thought", "feeling", "action", "args"}`. Items with `"who": "companion"`
  go to the companion.
- Unset `GITHUB_TOKEN` and the passwords so the test can't push a live snapshot or lock anything.
- `node` is needed for his eyes (`look`) and for drawing creations.
- For page changes, serve the copy with `python serve.py` and open http://localhost:8765.

## Git

- The workflow commits his world to `main` every hour, so **pull before you start** and rebase before you
  push: `git pull --rebase`.
- Commit only program files (`brain/`, `docs/*.js|html|css`, `docs/public/*.js|html`, workflow, README,
  this file). Keep commit messages short and plain, describing what changes for him.
- Update `README.md` when you add something he can do (it lists his abilities in plain language for the owner).
