#!/usr/bin/env python3
"""Acceptance test: render the example film as a draft and check the MP4.

usage: python test_render.py

Checks: the MP4 exists, its length matches the film, it has a loud enough sound track,
the picture moves between the first and the last frame, and seeking the same time twice
gives the same frame (renders repeat frame for frame).
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


def run(*cmd):
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
    if r.returncode:
        sys.exit(f"{' '.join(map(str, cmd))} failed ({r.returncode}):\n{r.stdout}{r.stderr}")
    return r


def frame(mp4, t, out):
    run("ffmpeg", "-loglevel", "error", "-y", "-ss", str(t), "-i", str(mp4), "-frames:v", "1", "-f", "rawvideo",
        "-pix_fmt", "gray", "-s", "96x54", str(out))
    return out.read_bytes()


def main():
    work = Path(tempfile.mkdtemp(prefix="mwv-test-"))
    film = work / "film"
    shutil.copytree(EXAMPLE, film)
    run("node", str(HERE / "render.mjs"), str(film), "draft")

    mp4 = film / "draft.mp4"
    assert mp4.exists(), "draft.mp4 was not written"
    timing = json.loads((film / "timing.json").read_text(encoding="utf-8"))
    want = timing["total"]
    got = float(run("ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(mp4)).stdout)
    assert abs(got - want) < 0.25, f"length {got:.2f}s, film is {want:.2f}s"

    probe = subprocess.run(["ffmpeg", "-i", str(mp4), "-af", "volumedetect", "-f", "null", "-"],
                           capture_output=True, text=True, encoding="utf-8").stderr
    assert "Audio: aac" in probe, "no aac sound track"
    vol = float(re.search(r"mean_volume: (-?[\d.]+) dB", probe).group(1))
    assert vol > -40, f"sound too quiet: {vol} dB"

    first = frame(mp4, 0.05, work / "a.raw")
    last = frame(mp4, want - 0.2, work / "b.raw")
    moved = sum(abs(x - y) for x, y in zip(first, last)) / len(first)
    assert moved > 2, f"picture did not change (mean diff {moved:.2f})"

    run("node", str(HERE / "render.mjs"), str(film), "still", "1.0", str(work / "s1.png"))
    run("node", str(HERE / "render.mjs"), str(film), "still", "1.0", str(work / "s2.png"))
    assert (work / "s1.png").read_bytes() == (work / "s2.png").read_bytes(), "same time gave different frames"

    shutil.rmtree(work, ignore_errors=True)
    print(f"render checks passed ({got:.2f}s, {vol} dB, frame change {moved:.1f})")


if __name__ == "__main__":
    sys.exit(main())
