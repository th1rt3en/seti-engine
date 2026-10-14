#!/bin/bash
# Builds the website for Cloudflare under Linux. OpenNext's Cloudflare build does not work with Windows paths, so on Windows run this in WSL
# (it needs Node 22 and pnpm 10 in WSL: see docs/deploy-web.md). Copies the repository to ~/seti, builds there and leaves the result in
# ~/seti/apps/web/.open-next. Copy that folder back to apps/web/.open-next and run `wrangler deploy` there.
set -e
export PATH=$HOME/tools/node/bin:$PATH
SRC="${1:-/mnt/c/Users/Admin/workspace/seti-engine}"
mkdir -p ~/seti
cd "$SRC"
tar --exclude=./node_modules --exclude='*/node_modules' --exclude='*/.next' --exclude='*/.open-next' --exclude='*/.wrangler' \
    --exclude='*/.venv' --exclude=./.git --exclude='*/.turbo' --exclude=./assets --exclude=./docs/rules --exclude='*/__pycache__' \
    --exclude=./services -cf - . | (cd ~/seti && tar -xf -)
cd ~/seti
pnpm install --no-frozen-lockfile 2>&1 | tail -3
cd apps/web
pnpm exec opennextjs-cloudflare build 2>&1 | tail -6
