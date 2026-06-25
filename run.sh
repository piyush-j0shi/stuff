#!/usr/bin/env bash
# Create venv, install deps, seed data (first run), and serve.
set -e
cd "$(dirname "$0")"

if [ ! -d .venv ]; then
  python3 -m venv .venv
  .venv/bin/pip install -q --upgrade pip
  .venv/bin/pip install -q -r requirements.txt
fi

# Seed only if the database doesn't exist yet.
if [ ! -f media.db ]; then
  .venv/bin/python -m app.seed
fi

exec .venv/bin/uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
