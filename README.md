# Add Your Line ✍️

A real-time, two-player collaborative story-writing game. Two people take turns
adding **exactly two sentences** each until the story is complete, then get a
beautiful, color-coded, shareable result. No accounts, no passwords — just a
name and a link. Fully bilingual: **English & Hebrew (RTL)**.

Production: **https://addyourline.com**

---

## ✨ Features

- **Two ways to play** — match with a random writer, or invite a friend by link.
- **Real-time turns over WebSockets** — both players stay in sync with no refresh.
- **Server-authoritative game logic** — the backend owns whose turn it is; turns
  can't be skipped, duplicated, or edited.
- **No auth** — a locally-stored player token lets you refresh/reconnect safely.
- **English & Hebrew** with full RTL layout and a centralized translation system.
- **Exactly-two-sentence validation** on both client and server (EN + HE punctuation).
- **Shareable completed stories** at a public read-only URL with Open Graph previews.
- **Mobile-first, animated, polished UI** with blue (Player 1) / green (Player 2) colors.

---

## 🏗️ Architecture

```
addyourline/
├── backend/                 FastAPI + async SQLAlchemy + WebSockets
│   └── app/
│       ├── main.py          App, CORS, error handling, router wiring
│       ├── config.py        Env-driven settings (pydantic-settings)
│       ├── database.py      Async engine/session (SQLite ⇄ Postgres)
│       ├── models.py        Story / Player / Sentence ORM models
│       ├── schemas.py       Pydantic request/response models
│       ├── routers/         REST (stories, matchmaking) + WebSocket endpoint
│       ├── services/        Game logic + in-memory matchmaking queue
│       ├── websocket/       Connection manager + event helpers
│       ├── utils/           Token hashing + sentence validation
│       └── frontend.py      Serves the built SPA + injects OG tags (prod)
│   └── tests/               Pytest: validation + full game-flow integration
└── frontend/                React + TypeScript + Vite
    └── src/
        ├── pages/           Home, Play (waiting+game), Completed, Join
        ├── components/      Shell, StoryProse, ShareButtons, LanguageSelector
        ├── hooks/           useGameSocket (resilient WS with reconnect)
        ├── services/        api, storage (localStorage), config
        ├── i18n/            Centralized EN/HE translations + RTL context
        └── utils/           Sentence counter, player helpers
```

### Database schema

- **stories** — `id (uuid)`, `language`, `mode (random|friend)`, `total_turns`,
  `current_turn`, `status (waiting|active|completed)`, timestamps.
- **story_players** — `id (uuid)`, `story_id`, `display_name`,
  `player_number (1|2)`, `player_token_hash`, `joined_at`.
  Unique `(story_id, player_number)`.
- **sentences** — `id`, `story_id`, `player_id`, `position`, `turn_number`,
  `text`, `created_at`. Unique `(story_id, position)`, indexed.
  **Each turn = exactly two sentence rows** (a 10-turn game = 20 rows), written
  atomically in one transaction as the turn advances.

### Real-time events

`player_joined`, `game_started`, `turn_submitted`, `turn_changed`,
`player_disconnected`, `player_reconnected`, `story_completed`.

### Identity model (no auth)

On create/join, the server issues a random token and stores only its SHA-256
hash. The client keeps the raw token in `localStorage` per story, so refreshing
or reconnecting restores the correct game state. A leaked DB cannot impersonate
players.

---

## 🚀 Run locally

### Prerequisites
- Python 3.11+ and Node.js 20+

### 1. Backend

```bash
cd backend
python -m venv .venv
# Windows:  .venv\Scripts\activate
# macOS/Linux:  source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # optional; defaults work for local dev
uvicorn app.main:app --reload --port 8000
```

Backend runs at **http://localhost:8000** (interactive API docs at `/docs`).

### 2. Frontend (separate terminal)

```bash
cd frontend
npm install
npm run dev
```

Frontend runs at **http://localhost:5173** and proxies `/api` and `/ws` to the
backend, so everything is same-origin. Open it in **two different browsers**
(or a normal + incognito window), start a story, share/join, and write together.

### Run the tests

```bash
cd backend
pytest            # 26 tests: sentence validation + full game-flow rules
```

### Docker Compose (optional)

```bash
docker compose up --build
# frontend → http://localhost:5173 , backend → http://localhost:8000
```

---

## 🌐 Deployment (https://addyourline.com)

The simplest robust setup is a **single container**: FastAPI serves the built
React app, the API, and WebSockets from one origin. This makes WebSockets,
CORS, and SPA deep-link refreshes "just work", and enables server-rendered Open
Graph tags for shared stories.

### Build & run the production image

```bash
docker build -t addyourline .
docker run -p 8000:8000 \
  -e PUBLIC_BASE_URL=https://addyourline.com \
  -e CORS_ORIGINS=https://addyourline.com \
  -e DATABASE_URL=postgresql+asyncpg://USER:PASS@HOST:5432/addyourline \
  addyourline
```

(Without `DATABASE_URL` it uses SQLite — fine for a demo, but use Postgres for
real deployments. To use Postgres, uncomment `asyncpg` in
`backend/requirements.txt`.)

### Required production environment variables

| Variable           | Example                                            | Purpose                                   |
| ------------------ | -------------------------------------------------- | ----------------------------------------- |
| `PUBLIC_BASE_URL`  | `https://addyourline.com`                          | Builds invite & share links               |
| `CORS_ORIGINS`     | `https://addyourline.com`                          | Allowed browser origins                   |
| `DATABASE_URL`     | `postgresql+asyncpg://user:pass@host:5432/addyourline` | Database (Postgres in prod)          |
| `ALLOWED_TURN_COUNTS` | `10,20,30`                                      | Selectable story lengths                  |

> ⚠️ Never commit real secrets. Only `.env.example` is tracked; `.env` is
> git-ignored. Set production values in your host's environment / secrets store.

### Platforms

Any container host works (Render, Railway, Fly.io, Google Cloud Run, a VM with
Docker). The image honors `$PORT` if the platform sets one. Ensure the platform
**allows WebSocket (upgrade) connections** — all of the above do. For automatic
deploys, connect the GitHub repo so pushes to `main` build and deploy the image.

#### If you split frontend/backend onto different hosts
Serve the frontend as static files and point a reverse proxy so `/api` and `/ws`
reach the backend on the same public origin (keeps WS + cookies + OG simple).
Otherwise introduce `VITE_API_BASE` in `src/services/api.ts` and enable the
matching `CORS_ORIGINS`.

### DNS for addyourline.com

DNS/hosting is **not** preconfigured — do this manually at your registrar:

1. Deploy the app to your host and note its target (an IP, or a hostname such as
   `your-app.onrender.com`).
2. At your DNS provider for `addyourline.com`, add records:
   - **Apex** `addyourline.com`: an `A` record to the host's IP, **or** an
     `ALIAS`/`ANAME` to the host's hostname (if your provider supports it).
   - **www** `www.addyourline.com`: a `CNAME` to the host's hostname.
3. In your hosting platform, add `addyourline.com` (and `www`) as custom domains
   so it can provision a **TLS certificate** (most issue Let's Encrypt certs
   automatically once DNS resolves).
4. Wait for DNS propagation (minutes to a few hours), then verify:
   - `https://addyourline.com` loads the homepage,
   - an invite link `https://addyourline.com/<story-id>` opens the join screen,
   - a completed story `https://addyourline.com/story/<story-id>` shows a social
     preview when pasted into WhatsApp/Facebook/X.

---

## 🧩 Game rules enforced by the server

- A story has **exactly two** players; a third cannot join.
- Only the **active** player can submit, and only **two sentences** per turn.
- Turns can't be skipped; duplicate submissions for a turn are rejected.
- A **completed** story is immutable and publicly readable.
- Random matchmaking pairs only compatible settings and never matches you with
  yourself.
- Names and story text are length-limited and safely rendered (React escaping).
- Basic per-IP rate limiting guards write endpoints.

---

## 📜 License

MIT — do whatever you like. Built as a portfolio-quality MVP.
