# arcane-claude-arts

Generate a standalone image from a **prompt** (what to draw) and a **style** (the look
to follow), via Google Gemini Nano Banana 2 or OpenAI GPT Image 2.

Lifted out of the `/teach` lesson image pipeline and decoupled from HTML: there is no
lesson scanning and no `<img>` injection here — you pass the prompt and style directly.

## Setup

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

Set API keys (read from a `.env` walked up from the current directory, or the
environment):

- `GEMINI_API_KEY` (or `GOOGLE_API_KEY`) — for the default Gemini provider
- `OPENAI_API_KEY` — for `--provider openai`

## Usage

```bash
# Dry run (default) — prints state + estimated cost, spends nothing:
.venv/bin/python tools/arcane.py "a lone fox in a misty forest" --style editorial-illustration

# Generate for real (requires --generate):
.venv/bin/python tools/arcane.py "a lone fox in a misty forest" --style editorial-illustration --generate --open

# Free-form style instead of a preset:
.venv/bin/python tools/arcane.py "app icon, a compass" --style-text "flat vector, two flat colors" --provider openai --generate

# List available style presets:
.venv/bin/python tools/arcane.py --list-styles
```

Output: `arcane-out/<name>.webp` plus `arcane-out/manifest.json` in the current
directory (override with `--out-dir`). `<name>` defaults to a slug of the prompt plus a
short hash; override with `--name`.

## Cost safety

- **Dry run by default.** Nothing is generated (and nothing is charged) without
  `--generate`.
- `--max-cost` (default `1.00`) aborts *before* any API call if the estimate exceeds it.
- **Caching.** An identical prompt+style+provider+size is hashed; a re-run reports
  `CACHED` and spends nothing. Editing the prompt or style re-generates (`CHANGED`).

Per-image prices (verified Jun 2026): Gemini ~$0.067; OpenAI GPT Image 2 ~$0.006 (low)
/ $0.053 (medium) / $0.211 (high).

## Styles

Presets are plain text files in `styles/`. Add a `styles/<name>.txt` and select it with
`--style <name>`. A one-off look can be passed inline with `--style-text "..."`.
