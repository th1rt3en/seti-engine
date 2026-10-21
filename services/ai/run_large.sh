#!/bin/bash
# Training of the large network (144M): copy v008 first (it plays itself and the heuristic bot, and a few games of the bots are added), then improve by self-play against the opponent pool (models_large/pool.json).
# Everything goes to logs/train-large.log. Pause: `python -m uv run python -m seti_ai.train pause --models models_large` (or Ctrl+C); run this script again to go on.
cd "$(dirname "$0")"
M=models_large
if [ ! -f $M/bc-large/model.pt ]; then
  python -m uv run python -m seti_ai.train bc --teacher models/v008 --games 800 --epochs 6 --preset large --models $M || exit 1
fi
python -m uv run python -m seti_ai.train ppo --resume --start $M/bc-large --iters ${1:-300} --games 96 --eval-every 10 --eval-games 20 --models $M
