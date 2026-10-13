#!/usr/bin/env python3
"""Build a short motion film: Manim scenes + a synthesised score, no footage, no voice.

usage: motion.py <film_dir> [draft|final]

<film_dir>/film.json   {"shape": "16:9" | "1:1" | "9:16", "scenes": ["Wake", "Reach", ...],
                        "score": {"master": 0.8, "events": [...]}}
<film_dir>/scenes.py   one Manim Scene class per name in "scenes", in that order.

Score events (time "at" is seconds from the start of the named scene):
  {"type": "note", "scene": "Reach", "at": 0.5, "pitch": "E4", "len": 0.4, "wave": "triangle", "gain": 0.3}
  {"type": "pad",  "scene": "Wake",  "at": 0, "pitches": ["C3", "G3", "E4"], "len": 4, "gain": 0.12}
  {"type": "hit",  "scene": "Fence", "at": 1.2, "sound": "thud" | "pop" | "tick" | "whoosh", "gain": 0.5}
A "len" of "scene" lasts to the end of that scene.

Writes <film_dir>/final.mp4 (or draft.mp4), score.wav and poster.png.
"""
import array
import json
import math
import random
import shutil
import subprocess
import sys
import wave
from pathlib import Path

RATE = 44100
SHAPES = {"16:9": (1920, 1080), "1:1": (1080, 1080), "9:16": (1080, 1920)}
NOTE = {"C": -9, "D": -7, "E": -5, "F": -4, "G": -2, "A": 0, "B": 2}


def freq(pitch):
    """'A4' -> 440.0; accepts sharps and flats ('F#3', 'Bb2')."""
    name, octave = pitch[:-1], int(pitch[-1])
    semis = NOTE[name[0].upper()] + name[1:].count("#") - name[1:].count("b")
    return 440.0 * 2 ** ((semis + 12 * (octave - 4)) / 12)


def osc(wave_name, phase):
    if wave_name == "sine":
        return math.sin(phase)
    x = (phase / (2 * math.pi)) % 1.0
    if wave_name == "square":
        return 1.0 if x < 0.5 else -1.0
    if wave_name == "saw":
        return 2 * x - 1
    return 4 * abs(x - 0.5) - 1  # triangle


def add_tone(buf, start, length, hz, wave_name, gain, attack=0.01, release=0.15):
    n0, n = int(start * RATE), int(length * RATE)
    a, r = max(1, int(attack * RATE)), max(1, int(release * RATE))
    step = 2 * math.pi * hz / RATE
    for i in range(min(n, len(buf) - n0)):
        env = min(1.0, i / a, (n - i) / r)
        buf[n0 + i] += gain * env * osc(wave_name, step * i)


def add_hit(buf, start, sound, gain):
    n0 = int(start * RATE)
    rnd = random.Random(7)  # fixed seed: the same film always gets the same noise
    shapes = {  # seconds, pitch start -> end (Hz, 0 = noise), decay speed
        "thud": (0.35, 120, 45, 12), "pop": (0.12, 900, 400, 30),
        "tick": (0.04, 2500, 2500, 80), "whoosh": (0.6, 0, 0, 4),
    }
    length, f0, f1, decay = shapes[sound]
    n, phase = int(length * RATE), 0.0
    for i in range(min(n, len(buf) - n0)):
        t = i / RATE
        if sound == "whoosh":  # noise that swells, then fades
            env = math.sin(math.pi * i / n) ** 2
            s = rnd.uniform(-1, 1) * env
        else:
            phase += 2 * math.pi * (f0 + (f1 - f0) * i / n) / RATE
            s = math.sin(phase) * math.exp(-decay * t)
        buf[n0 + i] += gain * s


def synth(score, starts, ends, total):
    buf = array.array("f", bytes(4 * int(total * RATE)))
    for e in score.get("events", []):
        t0 = starts[e["scene"]] + e.get("at", 0)
        length = ends[e["scene"]] - t0 if e.get("len") == "scene" else e.get("len", 0.4)
        if e["type"] == "note":
            add_tone(buf, t0, length, freq(e["pitch"]), e.get("wave", "triangle"), e.get("gain", 0.3))
        elif e["type"] == "pad":
            for p in e["pitches"]:
                add_tone(buf, t0, length, freq(p), e.get("wave", "sine"), e.get("gain", 0.1), attack=0.6, release=1.0)
        elif e["type"] == "hit":
            add_hit(buf, t0, e["sound"], e.get("gain", 0.5))
        else:
            sys.exit(f"unknown score event type: {e['type']}")
    peak = max((abs(s) for s in buf), default=0) or 1.0
    scale = score.get("master", 0.8) / peak  # normalise, so stacked notes never clip
    return array.array("h", (int(s * scale * 32767) for s in buf))


def write_wav(path, pcm):
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(pcm.tobytes())


def seconds(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
                         capture_output=True, text=True, check=True).stdout
    return float(out.strip())


def run(*cmd):
    subprocess.run(cmd, check=True)


def main():
    sys.stdout.reconfigure(encoding="utf-8")  # Windows consoles default to cp1252 and cannot print "→"
    root = Path(sys.argv[1]).resolve()
    mode = sys.argv[2] if len(sys.argv) > 2 else "draft"
    if mode not in ("draft", "final"):
        sys.exit("mode must be draft or final")
    film = json.loads((root / "film.json").read_text(encoding="utf-8"))
    w, h = SHAPES[film.get("shape", "16:9")]
    fps = 30
    if mode == "draft":
        w, h, fps = w // 2, h // 2, 15
    media = root / "media" / mode  # a fresh folder per mode, so an old render never ends up in the film
    shutil.rmtree(media, ignore_errors=True)
    run("manim", "-a", "--disable_caching", "--progress_bar", "none", "-r", f"{w},{h}", "--fps", str(fps),
        "--media_dir", str(media), str(root / "scenes.py"))
    rendered = {p.stem: p for p in media.rglob("*.mp4") if "partial_movie_files" not in p.parts}
    missing = [s for s in film["scenes"] if s not in rendered]
    if missing:
        sys.exit(f"scenes.py did not render: {missing}")
    starts, ends, t = {}, {}, 0.0
    for name in film["scenes"]:
        starts[name] = t
        t += seconds(rendered[name])
        ends[name] = t
    write_wav(root / "score.wav", synth(film.get("score", {}), starts, ends, t))
    (media / "list.txt").write_text("".join(f"file '{rendered[s]}'\n" for s in film["scenes"]), encoding="utf-8")
    out = root / f"{mode}.mp4"
    run("ffmpeg", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(media / "list.txt"),
        "-i", str(root / "score.wav"), "-map", "0:v", "-map", "1:a", "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", str(out))
    run("ffmpeg", "-loglevel", "error", "-y", "-ss", str(max(0.0, t - 1.0)), "-i", str(out), "-frames:v", "1",
        str(root / "poster.png"))
    print(f"{out} ({seconds(out):.1f}s, {w}x{h} {fps}fps)")
    for name in film["scenes"]:
        print(f"  {name:<12} {starts[name]:5.1f}s → {ends[name]:5.1f}s")


if __name__ == "__main__":
    main()
