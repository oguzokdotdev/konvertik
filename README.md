# Konvertik

Simple media converter built on top of FFmpeg.
No ads. No countdown timers. No "please wait 30 seconds".

Upload a file, get it back in a different format. That's it.

## Free plan
- Up to 500MB per file
- 100 conversions per day
- All formats

## Pro plan
- Nah, I'll gift the whole project if you purchase a pro plan (maybe)

## Stack
- FastAPI · SQLite · TaskIQ · FFmpeg

## Don't wanna pay? Run it locally
```bash
poetry install
poetry run uvicorn src.main:app --reload
```

## Why
Because every paid converter is just FFmpeg with a pretty UI.
So here's FFmpeg with a pretty UI. Free.