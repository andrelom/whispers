#!/bin/bash

python3 -m venv .venv

if [ -f .venv/bin/activate ]; then
  source .venv/bin/activate
else
  echo "Virtual environment not found."
  exit 1
fi

if [ -f requirements.txt ]; then
  pip install -r requirements.txt
fi

echo "Virtual environment activated."
