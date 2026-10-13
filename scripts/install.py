#!/usr/bin/env python3
"""Copy the skills to where your coding agent looks for them (for agents without plugins).

    python scripts/install.py                       # Claude Code, every project: ~/.claude/skills
    python scripts/install.py --project PATH        # Claude Code, one project: PATH/.claude/skills
    python scripts/install.py --codex --project PATH  # Codex: PATH/.agents/skills
    python scripts/install.py --skill motion-video  # only some skills (repeat --skill)

Claude Code users can install with the plugin instead (README, "Install"). The four skills are
copied as folders. An existing folder of the same name is replaced only with --force.
`motion-web-video` needs `motion-video` beside it, so it brings that one too.
"""
import argparse
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent / "skills"
ALL = sorted(p.name for p in ROOT.iterdir() if (p / "SKILL.md").exists())


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--project", type=Path, help="install into this project instead of your home folder")
    ap.add_argument("--codex", action="store_true", help="use .agents/skills (Codex) instead of .claude/skills")
    ap.add_argument("--skill", action="append", choices=ALL, help="install only this skill (repeatable)")
    ap.add_argument("--force", action="store_true", help="replace skill folders that already exist")
    a = ap.parse_args()

    if a.codex and not a.project:
        sys.exit("--codex needs --project PATH (Codex reads .agents/skills in the project)")
    base = (a.project.resolve() if a.project else Path.home()) / (".agents" if a.codex else ".claude") / "skills"
    skills = set(a.skill or ALL)
    if "motion-web-video" in skills:
        skills.add("motion-video")  # its score synth lives there

    base.mkdir(parents=True, exist_ok=True)
    for name in sorted(skills):
        dest = base / name
        if dest.exists():
            if not a.force:
                print(f"skip    {dest} (exists; use --force to replace)")
                continue
            shutil.rmtree(dest)
        shutil.copytree(ROOT / name, dest, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        print(f"copied  {dest}")
    print("\nNext: python scripts/check.py   (what each skill still needs on this machine)")


if __name__ == "__main__":
    main()
