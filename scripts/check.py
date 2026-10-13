#!/usr/bin/env python3
"""Check that this machine can run the motion-skills, and say how to fix what is missing.

    python scripts/check.py                  # every skill
    python scripts/check.py motion-web-video # one skill

Read-only: it runs each tool's version command and installs nothing. Exit code 0 when every
skill you asked about is ready, 1 when something is missing.
"""
import os
import platform
import re
import shutil
import subprocess
import sys

OS = {"Darwin": "mac", "Windows": "windows"}.get(platform.system(), "linux")

# How to install each tool, per OS. Shown only for what is missing.
HOW = {
    "python": {"mac": "brew install python", "windows": "winget install --id Python.Python.3.12 -e", "linux": "sudo apt install python3"},
    "node": {"mac": "brew install node", "windows": "winget install --id OpenJS.NodeJS.LTS -e", "linux": "see https://nodejs.org/en/download (Node 22 or later)"},
    "chrome": {"mac": "brew install --cask google-chrome", "windows": "winget install --id Google.Chrome -e", "linux": "install google-chrome or chromium, or set CHROME_PATH"},
    "ffmpeg": {"mac": "brew install ffmpeg", "windows": "winget install --id Gyan.FFmpeg -e  (then open a new shell)", "linux": "sudo apt install ffmpeg"},
    "manim": {"mac": "uv tool install manim", "windows": "uv tool install manim", "linux": "sudo apt install libcairo2-dev libpango1.0-dev && uv tool install manim"},
    "uv": {"mac": "brew install uv", "windows": "winget install --id astral-sh.uv -e", "linux": "curl -LsSf https://astral.sh/uv/install.sh | sh"},
    "espeak-ng": {"linux": "sudo apt install espeak-ng"},
}

CHROME_PATHS = [
    os.environ.get("CHROME_PATH"),
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/usr/bin/google-chrome",
    "/usr/bin/chromium",
]


def version(cmd):
    """The first version number a command prints, or None when it is not installed."""
    exe = shutil.which(cmd[0])
    if not exe:
        return None
    try:
        out = subprocess.run([exe, *cmd[1:]], capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.TimeoutExpired):
        return None
    m = re.search(r"(\d+)\.(\d+)(?:\.(\d+))?", out.stdout + out.stderr)
    return m.group(0) if m else "found"


def check_python():
    ok = sys.version_info >= (3, 10)
    return ok, f"Python {platform.python_version()}" + ("" if ok else " (need 3.10 or later)")


def check_node():
    v = version(["node", "--version"])
    if not v:
        return False, "Node not found"
    ok = int(v.split(".")[0]) >= 22
    return ok, f"Node {v}" + ("" if ok else " (need 22 or later)")


def check_chrome():
    path = next((p for p in CHROME_PATHS if p and os.path.exists(p)), None)
    return bool(path), f"Chrome at {path}" if path else "Chrome not found (set CHROME_PATH to its executable)"


def check_tool(name, cmd):
    v = version(cmd)
    return bool(v), f"{name} {v}" if v else f"{name} not found on PATH"


def check_voice():
    if OS == "linux":
        return check_tool("espeak-ng", ["espeak-ng", "--version"])
    return True, "system voice: " + ("say" if OS == "mac" else "Windows System.Speech")


def check_key():
    # Never print the key: say only whether it is set.
    if os.environ.get("ELEVENLABS_API_KEY"):
        return True, "ELEVENLABS_API_KEY is set (paid voice available)"
    return True, "ELEVENLABS_API_KEY not set: drafts use the free voice; set it only for a paid final voice"


CHECKS = {
    "python": check_python,
    "node": check_node,
    "chrome": check_chrome,
    "ffmpeg": lambda: check_tool("ffmpeg", ["ffmpeg", "-version"]),
    "ffprobe": lambda: check_tool("ffprobe", ["ffprobe", "-version"]),
    "manim": lambda: check_tool("manim", ["manim", "--version"]),
    "uv": lambda: check_tool("uv", ["uv", "--version"]),
    "voice": check_voice,
    "key": check_key,
}

SKILLS = {
    "motion-video": ["python", "ffmpeg", "ffprobe", "manim"],
    "motion-web-video": ["python", "node", "chrome", "ffmpeg", "ffprobe", "voice", "key"],
    "training-guide": ["python"],
    "training-video": ["uv", "voice", "key"],
}

INSTALL_FOR = {"ffprobe": "ffmpeg", "voice": "espeak-ng"}


def main():
    wanted = sys.argv[1:] or list(SKILLS)
    unknown = [s for s in wanted if s not in SKILLS]
    if unknown:
        sys.exit(f"unknown skill: {', '.join(unknown)}. Skills: {', '.join(SKILLS)}")
    results = {}
    missing = set()
    for skill in wanted:
        print(f"\n{skill}")
        ready = True
        for item in SKILLS[skill]:
            if item not in results:
                results[item] = CHECKS[item]()
            ok, text = results[item]
            print(f"  {'ok     ' if ok else 'MISSING'}  {text}")
            if not ok:
                ready = False
                missing.add(INSTALL_FOR.get(item, item))
        print(f"  -> {'ready' if ready else 'not ready'}")
    if missing:
        print(f"\nInstall ({OS}):")
        for tool in sorted(missing):
            print(f"  {tool}: {HOW.get(tool, {}).get(OS, 'see docs/INSTALL.md')}")
        print("Then open a new shell and run this check again. Details: docs/INSTALL.md")
        sys.exit(1)
    print("\nAll set. Next: docs/QUICKSTART.md")


if __name__ == "__main__":
    main()
