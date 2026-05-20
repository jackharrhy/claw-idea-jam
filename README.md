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
