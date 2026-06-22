---
name: arcane-claude-arts
description: Use when generating a standalone image -- an illustration, icon, banner, concept art, or any single picture -- from a text prompt and a style. Covers Gemini Nano Banana and OpenAI GPT Image. Not for embedding into HTML/lessons (that is the teach skill's job).
---

# arcane-claude-arts

Generate one image from a **prompt** (what to draw) and a **style** (the look to
follow). A standalone CLI wrapping Gemini Nano Banana 2 and OpenAI GPT Image 2, with
hash-caching so an identical request never re-spends.

## Money safety -- do this every time

Image generation costs real money per call. The order is non-negotiable:

1. **Dry run first.** Run the command WITHOUT `--generate`. It prints the cache state
   (NEW / CHANGED / CACHED) and the estimated cost. This spends nothing.
2. **Surface the cost to the user** and only add `--generate` once they've seen it (or
   for an obviously-cheap single image they already asked you to produce).
3. `--max-cost` (default $1.00) aborts before any API call if the estimate exceeds it.

Never pass `--generate` as the first thing you try. Never loop-retry a failed
generation without telling the user (each attempt charges).

## Quick reference

```bash
# from the consuming project's directory; use a python that has the deps installed
PY=~/.claude/skills/arcane-claude-arts/.venv/bin/python
TOOL=~/.claude/skills/arcane-claude-arts/tools/arcane.py

$PY $TOOL "a lone fox in a misty forest" --style editorial-illustration            # dry run
$PY $TOOL "a lone fox in a misty forest" --style editorial-illustration --generate --open
$PY $TOOL "app icon, a compass" --style-text "flat vector, two colors" --provider openai --generate
$PY $TOOL --list-styles
```

| flag | meaning |
|------|---------|
| `prompt` (positional) | what to draw |
| `--style <name>` | preset from `styles/<name>.txt` |
| `--style-text "..."` | free-form style (mutually exclusive with `--style`) |
| `--provider` | `gemini` (default) or `openai` |
| `--name` | output filename stem (default: prompt slug + hash) |
| `--size` / `--quality` | OpenAI only (`1024x1024`, `low`/`medium`/`high`) |
| `--out-dir` | output dir, default `./arcane-out` |
| `--generate` | actually spend; omit for dry run |
| `--max-cost` | pre-flight ceiling (USD) |

## Providers & prices (verified Jun 2026)

| provider | model | per image |
|----------|-------|-----------|
| gemini (default) | `gemini-3.1-flash-image` | ~$0.067 |
| openai | `gpt-image-2` | ~$0.006 low / $0.053 medium / $0.211 high |

GPT Image 2 renders short labels more legibly than Gemini; Gemini is cheaper for pure
illustration/mood. Either way, verify any text in the output -- image models garble
long or dense text.

## Style

Presets live in `styles/*.txt` (plain text descriptors). Add your own and select with
`--style <name>`, or pass a one-off look via `--style-text`. The style is appended to
the prompt and is part of the cache key, so changing it regenerates.

## Setup

`python3 -m venv .venv && .venv/bin/pip install -r requirements.txt` in the skill repo.
Keys: `GEMINI_API_KEY` (or `GOOGLE_API_KEY`), `OPENAI_API_KEY` -- from the environment
or a `.env`. See `README.md`.
