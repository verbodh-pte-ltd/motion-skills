# Install

Three steps: get the skills into your agent, install the tools each skill needs, run the check.

## 1. Get the skills

**Claude Code, as a plugin (recommended).** In a Claude Code session:

```
/plugin install motion-skills --marketplace verbodh-pte-ltd/motion-skills
```

On an older Claude Code, use two steps:

```
/plugin marketplace add verbodh-pte-ltd/motion-skills
/plugin install motion-skills@motion-skills
```

The skills then run as `/motion-skills:motion-video` and so on, and Claude also picks them up
when your request matches. Update later with `/plugin marketplace update motion-skills`.

**Claude Code or Codex, by copying.** Clone the repo, then copy the skill folders:

```bash
git clone https://github.com/verbodh-pte-ltd/motion-skills.git
cd motion-skills
python scripts/install.py                          # Claude Code, all projects: ~/.claude/skills
python scripts/install.py --project ../my-app       # Claude Code, one project
python scripts/install.py --codex --project ../my-app  # Codex: my-app/.agents/skills
```

**Any other agent.** Give it the skill's `SKILL.md` as the instructions for the task, and replace
`${CLAUDE_SKILL_DIR}` in it with the skill's folder.

## 2. Install the tools

You need only the tools of the skills you use. `python scripts/check.py` prints the commands for
what is missing on your machine.

| Skill | Tools |
|---|---|
| motion-video | Python 3.10+, ffmpeg + ffprobe, Manim Community |
| motion-web-video | Python 3.10+, Node 22+, Google Chrome (or Chromium), ffmpeg + ffprobe |
| training-guide | Python 3.10+, and a browser tool for screenshots (for example Claude in Chrome) |
| training-video | uv (it brings Pillow and its own ffmpeg) |

| Tool | macOS | Windows | Linux (Debian/Ubuntu) |
|---|---|---|---|
| Python | `brew install python` | `winget install --id Python.Python.3.12 -e` | `sudo apt install python3` |
| Node 22+ | `brew install node` | `winget install --id OpenJS.NodeJS.LTS -e` | from https://nodejs.org |
| Chrome | `brew install --cask google-chrome` | `winget install --id Google.Chrome -e` | google-chrome or chromium |
| ffmpeg | `brew install ffmpeg` | `winget install --id Gyan.FFmpeg -e` | `sudo apt install ffmpeg` |
| uv | `brew install uv` | `winget install --id astral-sh.uv -e` | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| Manim | `uv tool install manim` | `uv tool install manim` | `sudo apt install libcairo2-dev libpango1.0-dev`, then `uv tool install manim` |
| Free voice | built in (`say`) | built in (System.Speech) | `sudo apt install espeak-ng` |

On Windows, open a new shell after `winget install`, so the new tools are on your PATH.

## 3. Check

```bash
python scripts/check.py                    # every skill
python scripts/check.py motion-web-video   # one skill
```

Each skill reads **ready** or **not ready**, with the install command for each missing tool. It
installs nothing and never prints a key.

## Optional settings

| Variable | For |
|---|---|
| `ELEVENLABS_API_KEY` | a paid ElevenLabs voice for the final film or video. Drafts never need it |
| `CHROME_PATH` | Chrome in an unusual place |
| `TRAINING_VIDEO_BUCKET`, `TRAINING_VIDEO_BASE_URL`, `TRAINING_VIDEO_PREFIX` | training-video: an S3 voice cache and publishing. `AWS_PROFILE` and `AWS_REGION` pick the account |

Keep keys in your shell or a secret store, never in a file you commit.
