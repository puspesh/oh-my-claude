#!/usr/bin/env python3
"""Generate a standalone image from a text prompt and a style.

Pass what to draw as the prompt (the directive) and a style to follow -- either a
named preset from styles/<name>.txt or free-form via --style-text. The tool hashes
prompt+style+provider+size so an identical request is never re-generated (and never
re-charged). Default mode is a no-spend dry run; generation requires --generate and
stays under a --max-cost ceiling.

Providers: Gemini Nano Banana 2 (default) and OpenAI GPT Image 2.

    arcane.py "a lone fox in a misty forest" --style editorial-illustration --generate
    arcane.py "flat app icon, a compass" --style-text "flat vector, two flat colors" --provider openai
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from typing import Any

# Skill root (this file lives in <skill>/tools/), so presets resolve regardless of cwd.
SKILL_DIR = Path(__file__).resolve().parent.parent
STYLES_DIR = SKILL_DIR / "styles"

GEMINI_MODEL = "gemini-3.1-flash-image"
OPENAI_MODEL = "gpt-image-2"
DEFAULT_OPENAI_SIZE = "1024x1024"
DEFAULT_OPENAI_QUALITY = "medium"

# Per-image USD price, verified Jun 2026.
PRICE_GEMINI = 0.067
PRICE_OPENAI = {"low": 0.006, "medium": 0.053, "high": 0.211}


def _slug(text: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return s[:40].rstrip("-") or "image"


# --------------------------------------------------------------------------- #
# Job (the single generation unit)
# --------------------------------------------------------------------------- #

class Job:
    def __init__(
        self,
        prompt: str,
        style: str,
        provider: str,
        name: str | None,
        size: str,
        quality: str,
    ) -> None:
        self.prompt = (prompt or "").strip()
        self.style = (style or "").strip()
        self.provider = (provider or "gemini").strip().lower()
        self.quality = quality
        self._size = size
        self._name = (name or "").strip()

    @property
    def model(self) -> str:
        return GEMINI_MODEL if self.provider == "gemini" else OPENAI_MODEL

    @property
    def size(self) -> str | None:
        # Gemini returns its own resolution; only OpenAI takes size as input.
        return None if self.provider == "gemini" else self._size

    @property
    def name(self) -> str:
        return self._name or f"{_slug(self.prompt)}-{self.prompt_hash[:8]}"

    @property
    def full_prompt(self) -> str:
        return f"{self.prompt}\n\n{self.style}" if self.style else self.prompt

    @property
    def prompt_hash(self) -> str:
        payload = {
            "provider": self.provider,
            "model": self.model,
            "prompt": self.prompt,
            "style": self.style,
            "size": self.size,
        }
        blob = json.dumps(payload, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(blob.encode("utf-8")).hexdigest()

    @property
    def price(self) -> float:
        if self.provider == "gemini":
            return PRICE_GEMINI
        return PRICE_OPENAI[self.quality]

    def validate(self) -> None:
        if not self.prompt:
            raise SystemExit("a prompt is required (what to draw)")
        if self.provider not in ("gemini", "openai"):
            raise SystemExit(f"unknown provider '{self.provider}' (use gemini or openai)")
        if self.provider == "openai" and self.quality not in PRICE_OPENAI:
            raise SystemExit(f"unknown quality '{self.quality}' (use low, medium, or high)")


def resolve_style(style_name: str | None, style_text: str | None) -> str:
    if style_name and style_text:
        raise SystemExit("pass either --style or --style-text, not both")
    if style_text:
        return style_text
    if style_name:
        path = STYLES_DIR / f"{style_name}.txt"
        if not path.exists():
            available = ", ".join(sorted(p.stem for p in STYLES_DIR.glob("*.txt"))) or "(none)"
            raise SystemExit(f"no style preset '{style_name}'. available: {available}")
        return path.read_text(encoding="utf-8").strip()
    return ""


# --------------------------------------------------------------------------- #
# Manifest (cache + regeneration source-of-truth)
# --------------------------------------------------------------------------- #

def load_manifest(path: Path) -> dict[str, Any]:
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {}


def save_manifest(path: Path, manifest: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(
        json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    os.replace(tmp, path)


def _asset_ok(asset_path: Path) -> bool:
    """A cached asset must exist AND open as a valid image."""
    if not asset_path.exists():
        return False
    try:
        from PIL import Image

        with Image.open(asset_path) as im:
            im.verify()
        return True
    except Exception:
        return False


def cache_state(job: Job, manifest: dict[str, Any], out_dir: Path) -> str:
    entry = manifest.get(job.name)
    if entry is None:
        return "NEW"
    if entry.get("prompt_hash") != job.prompt_hash:
        return "CHANGED"
    if not _asset_ok(out_dir / f"{job.name}.webp"):
        return "NEW"
    return "CACHED"


# --------------------------------------------------------------------------- #
# Provider backends (lazy-imported; degrade if SDK/key absent)
# --------------------------------------------------------------------------- #

def _gemini_bytes(job: Job) -> bytes:
    api_key = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise SystemExit("set GOOGLE_API_KEY or GEMINI_API_KEY in .env for the gemini provider")
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=api_key)
    resp = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=job.full_prompt,
        config=types.GenerateContentConfig(response_modalities=["IMAGE"]),
    )
    for part in resp.candidates[0].content.parts:
        inline = getattr(part, "inline_data", None)
        if inline is not None and inline.data:
            return inline.data
    raise RuntimeError("gemini returned no image part")


def _openai_bytes(job: Job) -> bytes:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise SystemExit("set OPENAI_API_KEY in .env for the openai provider")
    from openai import OpenAI

    client = OpenAI(api_key=api_key)
    resp = client.images.generate(
        model=OPENAI_MODEL,
        prompt=job.full_prompt,
        size=job.size,
        quality=job.quality,
        output_format="webp",
    )
    return base64.b64decode(resp.data[0].b64_json)


def generate_asset(job: Job, out_dir: Path) -> tuple[Path, tuple[int, int]]:
    """Generate, normalize to WebP, write atomically. Returns (path, dims)."""
    from PIL import Image

    raw = _gemini_bytes(job) if job.provider == "gemini" else _openai_bytes(job)
    image = Image.open(BytesIO(raw))
    dims = image.size
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"{job.name}.webp"
    tmp = out.with_suffix(".webp.tmp")
    image.save(tmp, "WEBP", quality=90, method=6)
    os.replace(tmp, out)
    return out, dims


# --------------------------------------------------------------------------- #
# Env / CLI
# --------------------------------------------------------------------------- #

def _load_dotenv() -> None:
    try:
        from dotenv import load_dotenv

        for parent in [Path.cwd(), *Path.cwd().parents]:
            env = parent / ".env"
            if env.exists():
                load_dotenv(env, override=False)
                return
    except ImportError:
        for parent in [Path.cwd(), *Path.cwd().parents]:
            env = parent / ".env"
            if env.exists():
                for line in env.read_text(encoding="utf-8").splitlines():
                    line = line.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    key, _, val = line.partition("=")
                    os.environ.setdefault(key.strip(), val.strip().strip('"').strip("'"))
                return


def _parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(
        description="Generate a standalone image from a prompt and a style."
    )
    ap.add_argument("prompt", nargs="?", help="what to draw (the directive)")
    ap.add_argument("--style", default=None, help="named preset from styles/<name>.txt")
    ap.add_argument("--style-text", default=None, help="free-form style string (mutually exclusive with --style)")
    ap.add_argument("--provider", default="gemini", help="gemini (default) | openai")
    ap.add_argument("--name", default=None, help="output filename stem (default: slug of prompt + hash)")
    ap.add_argument("--size", default=DEFAULT_OPENAI_SIZE, help="OpenAI only, e.g. 1024x1024")
    ap.add_argument("--quality", default=DEFAULT_OPENAI_QUALITY, help="OpenAI only: low | medium | high")
    ap.add_argument("--out-dir", default="arcane-out", help="output dir (default: ./arcane-out)")
    ap.add_argument("--generate", action="store_true",
                    help="actually call the image API (default: dry run, no spend)")
    ap.add_argument("--max-cost", type=float, default=1.00,
                    help="abort before generating if the estimate exceeds this (USD)")
    ap.add_argument("--open", action="store_true", help="open the image after generating")
    ap.add_argument("--list-styles", action="store_true", help="list available style presets and exit")
    return ap.parse_args()


def main() -> None:
    args = _parse_args()

    if args.list_styles:
        presets = sorted(p.stem for p in STYLES_DIR.glob("*.txt"))
        print("\n".join(presets) if presets else "(no presets in styles/)")
        return

    _load_dotenv()

    style = resolve_style(args.style, args.style_text)
    job = Job(
        prompt=args.prompt,
        style=style,
        provider=args.provider,
        name=args.name,
        size=args.size,
        quality=args.quality,
    )
    job.validate()

    out_dir = Path(args.out_dir)
    manifest_path = out_dir / "manifest.json"
    manifest = load_manifest(manifest_path)
    state = cache_state(job, manifest, out_dir)

    print(f"[{state}] {job.name}  ({job.provider}/{job.model})")
    if job.style:
        clipped = job.style[:80] + ("..." if len(job.style) > 80 else "")
        print(f"  style: {clipped}")

    out_path = out_dir / f"{job.name}.webp"
    if state == "CACHED":
        print(f"  already at {out_path} -- nothing to do.")
        if args.open:
            subprocess.run(["open", str(out_path)], check=False)
        return

    print(f"  estimated cost: ${job.price:.3f}")

    if not args.generate:
        print("dry run -- nothing generated. Re-run with --generate to spend.")
        return

    if job.price > args.max_cost:
        raise SystemExit(
            f"estimated ${job.price:.3f} exceeds --max-cost ${args.max_cost:.2f}; "
            f"aborting before any API call. Raise --max-cost to proceed."
        )

    out_path, dims = generate_asset(job, out_dir)
    manifest[job.name] = {
        "provider": job.provider,
        "model": job.model,
        "prompt": job.prompt,
        "style": job.style,
        "size": f"{dims[0]}x{dims[1]}",
        "prompt_hash": job.prompt_hash,
        "path": f"{out_path.name}",
        "cost_usd": job.price,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    save_manifest(manifest_path, manifest)
    print(f"  generated {out_path} ({dims[0]}x{dims[1]}, ${job.price:.3f})")

    if args.open:
        subprocess.run(["open", str(out_path)], check=False)


if __name__ == "__main__":
    main()
