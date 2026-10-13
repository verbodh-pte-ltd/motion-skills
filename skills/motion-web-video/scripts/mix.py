#!/usr/bin/env python3
"""Write <film_dir>/score.wav from the score in film.json and the scene times in timing.json.

usage: mix.py <film_dir>

The score format and the synth are the motion-video skill's, so one score works in both skills.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "motion-video" / "scripts"))
from motion import synth, write_wav  # noqa: E402


def main():
    root = Path(sys.argv[1]).resolve()
    film = json.loads((root / "film.json").read_text(encoding="utf-8"))
    timing = json.loads((root / "timing.json").read_text(encoding="utf-8"))
    starts = {s["name"]: s["start"] for s in timing["scenes"]}
    ends = {s["name"]: s["end"] for s in timing["scenes"]}
    unknown = sorted({e["scene"] for e in film.get("score", {}).get("events", [])} - starts.keys())
    if unknown:
        sys.exit(f"score names scenes the page does not have: {unknown}")
    write_wav(root / "score.wav", synth(film.get("score", {}), starts, ends, timing["total"]))


if __name__ == "__main__":
    main()
