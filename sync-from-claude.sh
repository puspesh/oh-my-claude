#!/usr/bin/env bash
#
# sync-from-claude.sh — pull the LIVE ~/.claude config back into this repo.
#
# Use this after you've edited skills/agents/CLAUDE.md/settings in ~/.claude
# (or via Claude itself). It refreshes the repo copy so you can review a
# `git diff` and commit. The reverse of install.sh.
#
# Note: settings.local.json, .env, venvs, caches and generated output are
# never pulled in.
#
# Usage:  ./sync-from-claude.sh
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLAUDE_DIR="${CLAUDE_HOME:-$HOME/.claude}"

EXCL=(--exclude='.venv' --exclude='__pycache__' --exclude='*.pyc'
      --exclude='.env' --exclude='arcane-out' --exclude='node_modules'
      --exclude='.DS_Store')

cp "$CLAUDE_DIR/CLAUDE.md"     "$REPO_DIR/CLAUDE.md"
cp "$CLAUDE_DIR/settings.json" "$REPO_DIR/settings.json"

# --delete so skills/agents removed from ~/.claude are removed from the repo too.
rsync -a --delete "${EXCL[@]}" "$CLAUDE_DIR/skills/"   "$REPO_DIR/skills/"
rsync -a --delete "${EXCL[@]}" "$CLAUDE_DIR/agents/"   "$REPO_DIR/agents/"
rsync -a --delete "${EXCL[@]}" "$CLAUDE_DIR/commands/" "$REPO_DIR/commands/"

echo "Pulled ~/.claude config into the repo. Review and commit:"
echo "  git -C \"$REPO_DIR\" status"
echo "  git -C \"$REPO_DIR\" add -A && git -C \"$REPO_DIR\" commit -m 'sync claude config'"
