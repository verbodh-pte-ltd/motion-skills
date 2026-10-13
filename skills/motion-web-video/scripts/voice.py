#!/usr/bin/env python3
"""Narrate a film: one clip per scene from film.json "narration", written to voice.json.

usage: voice.py <film_dir> [--paid] [--voice VOICE_ID] [--plan]

Free system voice by default, for drafts. --paid uses ElevenLabs, once the user approves the
draft. Clips are kept and reused, so unchanged words are never paid for twice. --plan prints the
characters a paid run would bill and calls nothing. The narration code is narrate.py, next to this file.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from narrate import narrate, report  # noqa: E402


def main():
    args = sys.argv[1:]
    root = Path(args[0]).resolve()
    paid, plan = "--paid" in args, "--plan" in args
    film = json.loads((root / "film.json").read_text(encoding="utf-8"))
    # film.json "voice": {"id", "model_id", "voice_settings"} picks and tunes the paid voice.
    chosen = dict(film.get("voice", {}))
    voice = args[args.index("--voice") + 1] if "--voice" in args else chosen.pop("id", None)
    chosen.pop("id", None)
    chosen.pop("name", None)
    lines = [(name, words.strip()) for name, words in film.get("narration", {}).items() if words.strip()]
    if not lines:
        sys.exit('film.json has no "narration" to speak')
    clips, new, billed = narrate(root, lines, paid=paid, voice=voice, plan=plan, settings=chosen)
    report(new, billed, paid, plan)
    if not plan:
        (root / "voice.json").write_text(json.dumps(clips, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
