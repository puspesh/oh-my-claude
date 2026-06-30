#!/usr/bin/env bash
#
# install.sh — install this repo's Claude config into ~/.claude on this device.
#
# Two delivery modes (pick ONE per machine — they are mutually exclusive so you
# never get duplicate skills):
#
#   ./install.sh            COPY MODE (default)
#       Copies CLAUDE.md, settings.json, skills/, agents/, commands/ into
#       ~/.claude. Skills are user-level and invoked bare:  /caveman
#
#   ./install.sh --plugin   PLUGIN MODE
#       Copies CLAUDE.md + settings.json, enables the oh-my-claude plugin, and
#       does NOT copy skills/agents/commands (the marketplace plugin owns them).
#       Skills are namespaced:  /oh-my-claude:caveman
#       Requires the repo to be reachable as a marketplace (pushed to GitHub, or
#       added locally with:  claude  ->  /plugin marketplace add <path>).
#
# Add --dry to either mode to preview without writing.
# settings.local.json is never touched. Existing targets are backed up to
# ~/.claude/backups/<timestamp>/.
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLAUDE_DIR="${CLAUDE_HOME:-$HOME/.claude}"
STAMP="$(date +%Y%m%d-%H%M%S)"
BACKUP_DIR="$CLAUDE_DIR/backups/$STAMP"
PLUGIN_ID="oh-my-claude@oh-my-claude"

MODE="copy"; DRY=0
for arg in "$@"; do
  case "$arg" in
    --plugin) MODE="plugin" ;;
    --dry)    DRY=1 ;;
    *) echo "unknown arg: $arg" >&2; exit 2 ;;
  esac
done

EXCL=(--exclude='.venv' --exclude='__pycache__' --exclude='*.pyc'
      --exclude='.env' --exclude='arcane-out' --exclude='node_modules'
      --exclude='.DS_Store')

say() { printf '%s\n' "$*"; }

backup() { # $1 = path under ~/.claude
  local target="$CLAUDE_DIR/$1"
  [ -e "$target" ] || return 0
  if [ "$DRY" = 1 ]; then say "  would back up  $1 -> backups/$STAMP/"; return 0; fi
  mkdir -p "$BACKUP_DIR/$(dirname "$1")"; cp -R "$target" "$BACKUP_DIR/$1"
}

copy_file() { # $1 = filename at repo root
  backup "$1"
  if [ "$DRY" = 1 ]; then say "  would copy     $1"; return 0; fi
  cp "$REPO_DIR/$1" "$CLAUDE_DIR/$1"; say "  copied         $1"
}

copy_dir() { # $1 = dir name
  backup "$1"
  if [ "$DRY" = 1 ]; then say "  would mirror   $1/"; return 0; fi
  # --delete makes ~/.claude/<dir> mirror the repo (cleans stale files from
  # replaced skills). Excluded paths (.venv, arcane-out, .env) are protected
  # from deletion by rsync. The pre-sync backup above is the safety net.
  mkdir -p "$CLAUDE_DIR/$1"; rsync -a --delete "${EXCL[@]}" "$REPO_DIR/$1/" "$CLAUDE_DIR/$1/"
  say "  mirrored       $1/"
}

enable_plugin() { # turn on the plugin in the freshly-copied settings.json
  if [ "$DRY" = 1 ]; then say "  would enable   plugin $PLUGIN_ID in settings.json"; return 0; fi
  python3 - "$CLAUDE_DIR/settings.json" "$PLUGIN_ID" <<'PY'
import json, sys
path, plugin = sys.argv[1], sys.argv[2]
with open(path) as f: data = json.load(f)
data.setdefault("enabledPlugins", {})[plugin] = True
with open(path, "w") as f: json.dump(data, f, indent=2); f.write("\n")
PY
  say "  enabled        plugin $PLUGIN_ID"
}

DRYLABEL=""; [ "$DRY" = 1 ] && DRYLABEL=" (dry run)"
say "Installing Claude config -> $CLAUDE_DIR   [mode: $MODE]$DRYLABEL"
mkdir -p "$CLAUDE_DIR"
copy_file CLAUDE.md
copy_file settings.json

if [ "$MODE" = "copy" ]; then
  copy_dir skills
  copy_dir agents
  copy_dir commands
  say ""
  say "Copy mode: skills are user-level, invoked bare (e.g. /caveman)."
  say "The arcane-claude-arts skill needs a venv:"
  say "  cd $CLAUDE_DIR/skills/arcane-claude-arts && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt"
else
  enable_plugin
  say ""
  say "Plugin mode: skills/agents/commands come from the oh-my-claude plugin (NOT copied)."
  say "On next launch Claude fetches the plugin from the registered marketplace."
  say "Skills are namespaced, e.g. /oh-my-claude:caveman."
fi

say ""
say "settings.local.json was NOT touched (machine-specific)."
