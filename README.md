# oh-my-claude

My portable Claude Code configuration — the source of truth for `~/.claude` across
all my devices and workspaces. It works two ways:

1. **As a config repo** — clone it, run `install.sh`, and my global rules, skills,
   subagents, and commands land in `~/.claude`.
2. **As a plugin marketplace** — `/plugin marketplace add` + `/plugin install` pulls
   the same skills into any machine or teammate's setup.

Both paths ship in this repo; you pick **one per machine** (they're mutually exclusive
so you never get duplicate skills).

## What's tracked

| Path                          | What it is                                         |
| ----------------------------- | -------------------------------------------------- |
| `CLAUDE.md`                   | Global rules + planning/review workflow            |
| `settings.json`               | Permissions, hooks, enabled plugins, theme         |
| `skills/`                     | 11 personal skills (also the plugin's skill set)   |
| `agents/`                     | 10 `ns-*` subagents                                |
| `commands/`                   | Slash commands                                     |
| `.claude-plugin/marketplace.json` + `plugin.json` | Marketplace + plugin manifests |

**Not tracked** (machine-specific, secret, or runtime): `settings.local.json`, `.env`,
virtualenvs, generated `arcane-out/`, and `~/.claude`'s history/sessions/telemetry/caches.
Third-party plugins (superpowers, evo, …) are *referenced* by `settings.json` and
re-fetched from their marketplaces — not vendored here.

## Set up a new device

```bash
git clone git@github.com:puspesh/oh-my-claude.git ~/Code/oh-my-claude
cd ~/Code/oh-my-claude
```

Then pick **one** mode:

### Copy mode (default) — bare skill names

Skills become user-level: invoked as `/caveman`, `/clean-code`, etc.

```bash
./install.sh            # or ./install.sh --dry to preview
```

The `arcane-claude-arts` skill needs a venv afterward:

```bash
cd ~/.claude/skills/arcane-claude-arts
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
```

### Plugin mode — namespaced skill names

Skills come from the marketplace plugin: invoked as `/oh-my-claude:caveman`.

```bash
./install.sh --plugin   # copies CLAUDE.md + settings.json, enables the plugin,
                        # does NOT copy skills/agents/commands
```

`install.sh --plugin` registers the marketplace and enables the plugin in
`settings.json`; on next launch Claude fetches it from GitHub. To use the plugin
without a GitHub push (e.g. local testing), add the marketplace by path inside Claude:

```
/plugin marketplace add ~/Code/oh-my-claude
/plugin install oh-my-claude@oh-my-claude
```

## Push local changes back into the repo

`install.sh` is copy-based, so the live config can drift. After editing anything under
`~/.claude` (directly or via Claude), pull it back and commit:

```bash
./sync-from-claude.sh
git add -A && git commit -m "sync claude config"
git push
```

`sync-from-claude.sh` is the reverse of copy-mode install and applies the same
exclusions (no secrets, venvs, or generated output). It does not touch the
`.claude-plugin/` manifests.

## Renaming the GitHub repo

The GitHub remote is still `puspesh/arcane-claude-arts`. The marketplace manifest and
`settings.json` already target `puspesh/oh-my-claude`. When you rename on GitHub:

```bash
git remote set-url origin git@github.com:puspesh/oh-my-claude.git
```

## Credits

These skills are sourced from [mattpocock/skills](https://github.com/mattpocock/skills)
(MIT): `grill-me`, `grill-with-docs`, `grilling`, `teach`, `tdd`, `domain-modeling`,
`codebase-design`. Several are dependencies of others: `grill-me` and `grill-with-docs`
invoke `/grilling`; `grill-with-docs` also invokes `/domain-modeling`; `tdd` references
`/codebase-design`.

`thermo-nuclear-code-quality-review` is from
[cursor/plugins](https://github.com/cursor/plugins/tree/main/cursor-team-kit/skills/thermo-nuclear-code-quality-review)
(cursor-team-kit). That repo ships no explicit license; included here for personal use.
