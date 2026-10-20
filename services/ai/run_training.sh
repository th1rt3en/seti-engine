#!/bin/bash
# Starts a full training run on this machine: copy the heuristic bot first, then improve by self-play. Everything is written to logs/ and models/.
cd "$(dirname "$0")"
PY=.venv/Scripts/python.exe
$PY -m seti_ai.train bc --games 400 --epochs 6 --preset base --models models
$PY -m seti_ai.train ppo --start models/bc-base --iters ${1:-300} --games 96 --eval-every 10 --eval-games 20 --models models
