#!/usr/bin/env python3
"""Turn script.md into one narration clip per scene, plus durations.json for Manim.

script.md format: one `## Scene1`, `## Scene2`, ... heading per scene, then the spoken text.

Narration comes last and is paid for once:
- Default: the free system voice (macOS `say`, Windows speech). Use it for every draft.
- `--paid`: ElevenLabs (key from $ELEVENLABS_API_KEY).
  Run it only after the user approves the draft.
- Every clip is kept under a name made from its voice and words. A clip whose words did not
  change is reused, so a re-run never pays for the same sentence twice.
- `--plan` prints what a run would make and how many characters ElevenLabs would bill. It calls nothing.

usage: narrate.py <video_dir> [--paid] [--voice VOICE_ID] [--plan]
"""
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path

API = "https://api.elevenlabs.io/v1"


def api_key():
    return os.environ.get("ELEVENLABS_API_KEY") or None


def request(path, key, body=None):
    req = urllib.request.Request(f"{API}{path}", headers={"xi-api-key": key, "Content-Type": "application/json"},
                                 data=json.dumps(body).encode() if body else None)
    with urllib.request.urlopen(req, timeout=120) as resp:
        return resp.read()


def scenes(text):
    parts = re.split(r"^##\s+(\S+).*$", text, flags=re.M)
    return [(parts[i], parts[i + 1].strip()) for i in range(1, len(parts), 2) if parts[i + 1].strip()]


def duration(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
                         capture_output=True, text=True, check=True)
    return round(float(out.stdout), 2)


def free_voice(words, out):
    """Speak `words` into `out` with the system voice. Free; for drafts."""
    if sys.platform == "darwin":
        subprocess.run(["say", "-o", str(out), words], check=True)
        return
    if sys.platform == "win32":
        with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8") as f:
            f.write(words)
        ps = ("Add-Type -AssemblyName System.Speech; $s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
              f"$s.SetOutputToWaveFile('{out}'); $s.Speak([IO.File]::ReadAllText('{f.name}')); $s.Dispose()")
        try:
            subprocess.run(["powershell", "-NoProfile", "-Command", ps], check=True, capture_output=True)
        finally:
            os.unlink(f.name)
        return
    subprocess.run(["espeak-ng", "-w", str(out), words], check=True)


def spoken(words):
    """The words as a person says them. A test found the voice read '#' and dots aloud.

    Markdown and other symbols are dropped, an arrow is said as 'to', and an @mention keeps its
    name ('@claude' is 'at Claude'). Sentence dots stay: they are pauses, not words.
    """
    words = re.sub(r"@(\w+)", lambda m: f"at {m.group(1).capitalize()}", words)
    words = re.sub(r"\s*(→|->)\s*", " to ", words)
    words = re.sub(r"[#*_`>|~\[\]{}]", "", words)
    return re.sub(r"\s+", " ", words).strip()


def clip_path(audio, name, provider, voice, words):
    tag = hashlib.sha256(f"{provider}|{voice}|{words}".encode()).hexdigest()[:12]
    ext = "mp3" if provider == "elevenlabs" else ("aiff" if sys.platform == "darwin" else "wav")
    return audio / f"{name}.{provider}.{tag}.{ext}"


def narrate(root, lines, paid=False, voice=None, plan=False, settings=None):
    """Make one clip per (scene, words) pair in `lines`, reusing every clip already made.

    Returns ({scene: {"file", "seconds"}}, new_clips, billed_characters). With plan=True nothing is
    made: the counts say what a real run would do. `settings` adds ElevenLabs body fields
    (model_id, voice_settings); they are part of the clip's name, so a change remakes the clip.
    """
    settings = settings or {}
    lines = [(name, spoken(words)) for name, words in lines]
    root = Path(root)
    audio = root / "audio"
    audio.mkdir(exist_ok=True)
    provider = "elevenlabs" if paid else "system"
    key = None
    out, new, billed = {}, 0, 0
    voice_id = voice  # the clip name keeps "default", so --plan matches without asking ElevenLabs
    for name, words in lines:
        tagged = words + (json.dumps(settings, sort_keys=True) if paid and settings else "")
        clip = clip_path(audio, name, provider, voice or "default", tagged)
        if not clip.exists():
            new += 1
            billed += len(words) if paid else 0
            if plan:
                continue
            if paid:
                key = key or api_key() or sys.exit("no ElevenLabs key: set ELEVENLABS_API_KEY")
                voice_id = voice_id or json.loads(request("/voices", key))["voices"][0]["voice_id"]
                clip.write_bytes(request(f"/text-to-speech/{voice_id}", key, {"text": words, **settings}))
            else:
                free_voice(words, clip)
        if clip.exists():
            out[name] = {"file": clip.relative_to(root).as_posix(), "seconds": duration(clip)}
    return out, new, billed


def report(new, billed, paid, plan):
    voice = "ElevenLabs voice" if paid else "free system voice"
    if plan:
        print(f"plan: {new} new clip(s) with the {voice}; would bill {billed} characters")
    else:
        print(f"{new} new clip(s) with the {voice}; billed {billed} characters")


def main():
    args = sys.argv[1:]
    root = Path(args[0])
    paid, plan = "--paid" in args, "--plan" in args
    voice = args[args.index("--voice") + 1] if "--voice" in args else None
    lines = scenes((root / "script.md").read_text(encoding="utf-8"))
    durations, new, billed = narrate(root, lines, paid=paid, voice=voice, plan=plan)
    report(new, billed, paid, plan)
    if plan:
        return
    for name, d in durations.items():
        print(f"{name}: {d['seconds']}s")
    (root / "durations.json").write_text(json.dumps(durations, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
