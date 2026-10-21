#!/bin/bash
# Training of the large network (144M): copy v008 first (it plays itself and the heuristic bot, and a few games of the bots are added), then improve by self-play against the opponent pool (models_large/pool.json).
# Everything goes to logs/train-large.log. Pause: `python -m uv run python -m seti_ai.train pause --models models_large` (or Ctrl+C); run this script again to go on.
cd "$(dirname "$0")"
M=models_large
if [ ! -f $M/bc-large/model.pt ]; then
  python -m uv run python -m seti_ai.train bc --teacher models/v008 --games 800 --epochs 6 --preset large --models $M || exit 1
fi
# 6 workers: every worker holds a copy of the libraries (about 2.5 GB of the memory that Windows can promise), and ten of them left no room
# for the trainer and the browser. --champion: a version is saved only when it beats v008 head to head over 100 games (seti_ai/gate.py).
python -m uv run python -m seti_ai.train ppo --resume --start $M/bc-large --champion models/v008 --iters ${1:-300} --games 96 --eval-every 10 --eval-games 20 --workers 6 --models $M
