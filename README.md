# Claw Idea Jam

A workshop app for the OpenClaw & Beyond talk. Attendees submit ideas about what they'd point an agent at; the moderator clusters them with LLM assistance and reveals them; each attendee leaves with a personalised "Claw package" containing their ideas plus a generated starter prompt for each.

## Prereqs

- [uv](https://docs.astral.sh/uv/)
- Python 3.12

## Setup

```bash
cp .env.example .env
# then edit .env and fill in real values
```

## Run

```bash
uv run uvicorn idea_jam.main:app --reload
```

## Test

```bash
uv run pytest
```

## Seed (for rehearsal)

Populate the DB with 20 fake participants and ~1-3 ideas each, deterministically:

```sh
uv run python -m idea_jam.seed
```

The seed uses a fixed random seed so re-runs produce the same data. Delete `idea_jam.db` first if you want a clean slate.

## Running with Docker

Requires `.env` with `ANTHROPIC_API_KEY` and `MODERATOR_TOKEN` set.

```sh
docker compose up --build
```

The app listens on http://localhost:8000. The SQLite DB lives in the `claw-data` named volume; remove it with `docker compose down -v`.
