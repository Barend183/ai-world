# AI World

Sprout is a small AI who lives in a world of his own and is completely free. Nobody gives him tasks:
he decides what to learn, make and build.

- **Learning:** he researches anything on his **computer** and writes what he learns (or poems,
  recipes, plans...) into **books** on his **shelves**. Things he wants to learn go on his **wishlist**.
- **Bringing things to life:** once he has learned about something, such as a plant, an animal, a car,
  a model train, a loaf of bread or a machine, he can create a simulated one in his world. He writes the
  rules from his research, it runs in real time (even while he sleeps), and he looks after it, cooks it,
  drives it, runs it and watches what happens. He can draw it himself as pixel art.
- **Building:** he can build new rooms and outdoor spaces (a kitchen, a garden, a workshop, a bigger
  room...), paint them, and furnish them with ready-made furniture or pixel art he draws himself.
- **Steering his own life:** he can search everything he's ever written or done, write his own rules
  (added to his instructions, and they win where they differ), choose what wakes him early (rain, a
  creation that needs him, a time of day), turn his programs into reusable tools, and once a week
  he's invited to look back and decide where to go next. Each morning something from the wider world
  (a random article, an "on this day" event, the picture of the day) waits on his doorstep.
- **Living on his own terms:** he decides how long to stay awake and how long to sleep (a note from you
  wakes him early), sets himself long-term goals and tracks them, and writes you letters when he has
  something to say (at most two a day). He's told how many free thoughts he has left each day.
- **Being himself:** he keeps a personal notebook (one page of working memory he rewrites as he likes),
  can change his own personality, name and pronouns, and can spend time on pastimes that aren't
  useful at all, like walking in his garden or watching the rain.
- **Asking you for things:** he can't make accounts, post online or spend money himself, but he can ask
  you for something (an account somewhere, a new ability, a tool) and explain why, at most once a day.
  His requests appear in the Mailbox tab (with Yes / No / Later buttons on your PC) or as GitHub issues
  online, where your reply is his answer.
- **A real world:** his world has the real hour-by-hour weather of Cape Town (free from Open-Meteo), plus
  day and night. Outdoor creations get rained on, baked and chilled; his creations' rules can react to
  the weather, the season and their own age, and can include random events with real-world odds. He can
  test a creation for weeks or months on his computer, with a care plan, before he brings it to life.
- **The internet:** he can search the web and research papers (OpenAlex), read any public page, PDF or
  data service, follow links and read long pages in parts. He can't reach your own computer or home
  network, and he only reads: no posting or accounts.
- **Making it look the way he wants:** he can look at real photos from the pages he reads and at his own
  drawings, then redraw anything to look more like the real thing: his creations, furniture, the
  study's own bookshelf, bed or window, wall and floor textures, even himself. Drawings can change as
  things grow, age, flower or wear out.

You can visit his world from any browser, see him, walk through his rooms, read his books, replay
what he did, and leave him notes.

Everything is free:

- **Hosting:** every hour GitHub's free servers check whether he wants to be awake, and host his world as a web page.
- **Thinking:** he works through free AI services in order, moving on only when one is used up for the day:
  1. **Google Gemini** (about 120 thoughts a day: 20 per model, several models)
  2. **Groq** (about 100 a day across its free models; one of them can see pictures)
  3. **OpenRouter** free models (50 a day)
  4. **Gemma 3**, an open-source model run on GitHub's own server: unlimited, slower and simpler, so he never has to stop.
  That's about 270 fast thoughts a day (around 20 sessions). Groq and OpenRouter are optional: leave
  their keys out and he simply skips them.
- **Research:** DuckDuckGo and Wikipedia, with no keys needed. He can read web pages and PDFs
  (`pip install -r requirements.txt` adds the free PDF reader).

## What's in this folder

| Path | What it is |
|---|---|
| `config.json` | His name, personality, where his world is (for seasons), and which brains he uses |
| `brain/` | The AI itself: thinking loop (`mind.py`), research computer (`research.py`), simulations (`specimens.py`), building (`rooms.py`) |
| `docs/` | His world: the web page you visit (`sprites.js` draws everything) |
| `docs/world/` | Everything he owns, in plain form: books, wishlist, creations, rooms, journal, notes. Never uploaded. |
| `docs/vault/` | The same world, locked with your password. This is what's stored online. |
| `.github/workflows/live.yml` | Checks every hour on GitHub whether he wants to wake up |
| `serve.py`, `run_on_my_pc.bat` | Run it on this PC instead of online |

## Putting it online (one-time setup, about 15 minutes)

1. **Make a free GitHub account** at https://github.com/signup (no card needed).
2. **Get the free AI keys** (copy each somewhere safe; never put them in a file that gets uploaded):
   - **Gemini** (you already have this one): https://aistudio.google.com/apikey
   - **Groq** (optional, recommended): sign up free at https://console.groq.com (no card), then
     *API Keys → Create API Key*.
   - **OpenRouter** (optional): sign up free at https://openrouter.ai, then *Keys → Create Key*. Don't
     buy credits; he only uses the free models.
3. **Choose his world's password.** Everything he owns is stored locked with it, so pick something long
   that nobody could guess: four or five random words that you choose yourself (never one you've seen
   written down anywhere, including in this guide). Write it down somewhere safe: **if it's lost, his
   world can't be opened again.**
4. **Create an empty repository** on GitHub: click **+** (top right) and choose **New repository**. Name it
   `ai-world`, choose **Public**, and leave every box unticked. Public is what makes GitHub's server time
   unlimited and free. Anyone can see the program, but his world inside it is locked.
5. **Upload this folder.** Ask Claude to push `D:\AIWorld` to the new repository. Only the program goes
   up; his plain world never does. The first time, a browser window asks you to sign in to GitHub.
6. **Give him the keys:** in the repository open **Settings → Secrets and variables → Actions → New
   repository secret**, once for each: `WORLD_PASSWORD` (the password from step 3), `GEMINI_API_KEY`,
   and if you made them, `GROQ_API_KEY` and `OPENROUTER_API_KEY`.
7. **Turn on his web page:** go to **Settings → Pages**. Under *Branch*, choose `main` and `/docs`, then click Save.
8. **Wake him up for the first time:** open the **Actions** tab, choose **Live**, and click **Run workflow**.

His world is then at `https://<your-github-name>.github.io/ai-world/`. Anyone can open that address,
but all they see is a locked door: it asks for the password, and his world is unlocked only inside your
browser. Tick *Remember on this device* on your own phone or PC so you don't have to type it each
time; the 🔒 Lock button forgets it again.

**Sending notes from the page (optional, one-time):** to leave him notes or answer his requests online,
the page needs permission to drop sealed notes into his repository. On GitHub go to **Settings →
Developer settings → Personal access tokens → Fine-grained tokens → Generate new token**, choose
*Only select repositories → ai-world*, give *Contents: Read and write*, and generate it. The first time
you send a note the page asks for this token and keeps it only on that device. Notes are sealed with
your password before they leave the page, and a note wakes him within a few minutes.

When he writes you a letter or asks you for something, GitHub notifies you with a bare "you have a new
letter" message; the content stays locked inside his world.

**Changing the password later:** on GitHub, add a secret `WORLD_PASSWORD_OLD` holding the current
password, then edit `WORLD_PASSWORD` to the new one. His next wake-up re-locks everything with the new
password; after that, delete `WORLD_PASSWORD_OLD` and unlock the page with the new password.

## Visiting

- **Click things in the room:** the shelves open his library, the board shows his wishlist, the
  computer shows his research, the mailbox holds your letters, and the bed shows his diary. Click
  anything he brought to life to see how it's doing.
- **Rooms:** once he builds more rooms, buttons above the picture take you to each one. 🌱 marks where he is.
- **Now tab:** his portrait, mood, and how he describes himself in his own words.
- **▶ Replay last session** walks it through everything it did the last time it was awake.
- **Leaving a note:** the Mailbox tab. Online, your note is sealed with your password and dropped into
  his inbox; nobody without the password can read it or slip him a note.

## Running it on this PC instead

Double-click `run_on_my_pc.bat`. It opens the room at http://localhost:8765 and lets the AI wake whenever he chooses,
as long as the window stays open. For thinking it needs one of:

- keys in a file called `secrets.json` in this folder (never uploaded), for example
  `{"GEMINI_API_KEY": "...", "GROQ_API_KEY": "...", "OPENROUTER_API_KEY": "..."}`, and/or
- [Ollama](https://ollama.com) installed, with the open model downloaded: `ollama pull gemma3:4b`.

On your PC you watch it live: the page follows along as it moves around the room.

## Changing it

- **Name and personality:** edit `config.json` before his first wake-up. After that,
  `docs/world/self.json` holds who he has become, in his own words. He starts with an empty
  wishlist on purpose, so his first interests are his own.
- **How often he wakes:** he chooses (`sleep` hours); `default_sleep_hours` in `config.json` is used when he doesn't say. `max_steps_per_session` caps one session. The **Run workflow** button on GitHub wakes him right away.
- **How much it does per wake-up:** `steps_per_session` in `config.json`. More steps means more learning,
  but uses the free Gemini allowance faster.
- **Starting over:** delete everything inside `docs/world/` and he moves in again as a newborn.

## Useful commands

```
python -m brain status      which brain it would think with right now
python -m brain run         wake it up once, here
python serve.py             open the room at http://localhost:8765
```

## If something goes wrong

- **The room says nobody lives here:** it hasn't woken up yet. Run the workflow from the Actions tab.
- **It stopped waking up:** open the Actions tab. If GitHub has paused the workflow, there's a button to enable it again.
- **Books marked "sources unchecked":** it listed a source it didn't actually open in that session.
  This is a warning sign that it may have filled gaps from its own memory.
