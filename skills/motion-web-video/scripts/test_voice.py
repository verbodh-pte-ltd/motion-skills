#!/usr/bin/env python3
"""Acceptance test for narration: free voice for drafts, paid voice only once, scenes fit the voice.

usage: python test_voice.py

Uses the free system voice only, so it costs nothing. Checks that:
- voice.py makes one clip per narrated scene and writes voice.json;
- a second run makes no new clips; changing one scene's words remakes only that scene;
- --plan --paid lists the characters ElevenLabs would bill, and calls nothing;
- a scene is stretched to fit its narration, and the draft has the voice in it.
"""
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
EXAMPLE = HERE.parent / "example"
PY = sys.executable


def run(*cmd):
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
    if r.returncode:
        sys.exit(f"{' '.join(map(str, cmd))} failed ({r.returncode}):\n{r.stdout}{r.stderr}")
    return r.stdout


def made(out):
    return int(re.search(r"(\d+) new clip", out).group(1))


def spoken_checks():
    """A test found the voice read '#' and dots aloud. Symbols are never spoken; @claude is 'at Claude'."""
    sys.path.insert(0, str(HERE))
    from narrate import spoken
    assert spoken("## Plan it: **mention** @claude → done.") == "Plan it: mention at Claude to done."
    assert spoken("Fix #42 in `api.ts` | now") == "Fix 42 in api.ts now"
    assert spoken("Plan it. Build it.") == "Plan it. Build it."


def main():
    spoken_checks()
    work = Path(tempfile.mkdtemp(prefix="mwv-voice-"))
    film = work / "film"
    shutil.copytree(EXAMPLE, film)
    data = json.loads((film / "film.json").read_text(encoding="utf-8"))
    long_line = "Three plans. Pick the one that fits your team today, and change it whenever your team grows."
    data["narration"] = {"Wake": "Meet Acme Board.", "Plans": long_line}
    (film / "film.json").write_text(json.dumps(data, indent=2), encoding="utf-8")

    out = run(PY, str(HERE / "voice.py"), str(film))
    assert made(out) == 2, out
    voice = json.loads((film / "voice.json").read_text(encoding="utf-8"))
    assert set(voice) == {"Wake", "Plans"}, voice
    assert all((film / v["file"]).exists() and v["seconds"] > 0.3 for v in voice.values()), voice

    assert made(run(PY, str(HERE / "voice.py"), str(film))) == 0, "second run remade clips"

    data["narration"]["Wake"] = "Say hello to Acme Board."
    (film / "film.json").write_text(json.dumps(data, indent=2), encoding="utf-8")
    assert made(run(PY, str(HERE / "voice.py"), str(film))) == 1, "changing one scene should remake one clip"

    plan = run(PY, str(HERE / "voice.py"), str(film), "--paid", "--plan")
    want = len("Say hello to Acme Board.") + len(long_line)
    assert f"would bill {want} characters" in plan, plan
    assert not list((film / "audio").glob("*elevenlabs*")), "--plan must not call ElevenLabs"

    run("node", str(HERE / "render.mjs"), str(film), "draft")
    timing = json.loads((film / "timing.json").read_text(encoding="utf-8"))
    plans = next(s for s in timing["scenes"] if s["name"] == "Plans")
    voice = json.loads((film / "voice.json").read_text(encoding="utf-8"))
    assert plans["end"] - plans["start"] >= voice["Plans"]["seconds"], (plans, voice["Plans"])

    probe = subprocess.run(["ffmpeg", "-i", str(film / "draft.mp4"), "-af", "volumedetect", "-f", "null", "-"],
                           capture_output=True, text=True, encoding="utf-8").stderr
    assert "Audio: aac" in probe, "no sound track"
    shutil.rmtree(work, ignore_errors=True)
    print(f"voice checks passed (Plans scene {plans['end'] - plans['start']:.1f}s for {voice['Plans']['seconds']}s of voice)")


if __name__ == "__main__":
    sys.exit(main())
