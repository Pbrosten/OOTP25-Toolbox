# Installation

[← Back to Home](Home.md)

## Prerequisites

- **Podman** or **Docker** (with `docker-compose`/`podman compose`) — runs the
  backend, frontend, and MariaDB containers.
- **OOTP Baseball 25**, with a save game you want to analyze.
- Optionally, for running the backend outside a container (host `.venv`):
  [`uv`](https://docs.astral.sh/uv/getting-started/) and Python 3.13.

## 1. Clone the repo

```bash
git clone <repo-url> OOTP25-Toolbox
cd OOTP25-Toolbox
```

## 2. Configure OOTP to export dump files

The toolbox ingests OOTP's MySQL dump exports, not the save file directly.
In-game:

1. **Game → Almanac → Almanac Options...**
2. Check **Monthly data dump to MySQL file**, then **Edit Profile** and make
   sure `players_batting`, `players_fielding`, and `players_pitching` are
   checked.
3. Repeat for **Yearly data dump to MySQL file** — in that profile, ensure
   `players_basic`, `teams`, and `players_career_batting_stats` are checked.

Dump files land in `saved_games/<save_name>/dump/`. See
[Updating the Database](Updating-the-Database.md) for how these get ingested,
including an important note about needing a yearly dump before monthly dumps
are useful.

## 3. Set up `backend/.env`

Copy the template and fill in the paths for your machine:

```bash
cp backend/templates/.env-template backend/.env
```

See [Configuration](Configuration.md) for what each variable means and how to
point `DUMP_PATH` at your OOTP save's dump folder via the `docker-compose.yml`
bind mount.

## 4. (Optional) Backend host virtualenv

Only needed if you want to run `flask` commands or tests directly on the
host, outside the containers:

```bash
cd backend
uv venv
uv pip install --system .      # or: uv sync
```

## 5. Bring up the stack

```bash
podman compose up -d      # or: docker-compose up --build
```

- Backend: `http://localhost:5000`
- Frontend: `http://localhost:5173`
- MariaDB: published on host port `5001` (container port `3306`)

Once the containers are healthy, load your dump files following
[Updating the Database](Updating-the-Database.md) — the app has no data until
that step runs.
