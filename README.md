# motion-skills

[![tests](https://github.com/verbodh-pte-ltd/motion-skills/actions/workflows/test.yml/badge.svg)](https://github.com/verbodh-pte-ltd/motion-skills/actions/workflows/test.yml)
[![MIT](https://img.shields.io/badge/licence-MIT-blue.svg)](LICENSE)

Video as code, on any Claude Code plan. Four skills for Claude Code (and Codex or any agent that
reads a `SKILL.md`) that turn work you already do into short films and training material:

| Skill | Ask for | You get |
|---|---|---|
| [motion-web-video](skills/motion-web-video/SKILL.md) | "a 15-second animated explainer of our pricing page" | a web page animated with [Motion](https://motion.dev), a live editor for words and colours, then an MP4 |
| [motion-video](skills/motion-video/SKILL.md) | "a 20-second motion video of how a request becomes a pull request" | Manim scenes and a generated score, rendered to MP4 |
| [training-guide](skills/training-guide/SKILL.md) | "a training guide for the setup we just did" | a step-by-step guide with one screenshot per step |
| [training-video](skills/training-video/SKILL.md) | "a narrated video from that guide" | an MP4 with captions timed to the voice |

Every film is code, so a re-render gives the same film, frame for frame. Drafts are free: they
use your system voice. An ElevenLabs voice is optional, for the final cut only.

## Install

In Claude Code:

```
/plugin install motion-skills --marketplace verbodh-pte-ltd/motion-skills
```

Older Claude Code: `/plugin marketplace add verbodh-pte-ltd/motion-skills`, then
`/plugin install motion-skills@motion-skills`. For Codex, or to copy the folders yourself:
`python scripts/install.py --help`. All options: [docs/INSTALL.md](docs/INSTALL.md).

## Check your machine

```bash
git clone https://github.com/verbodh-pte-ltd/motion-skills.git
python motion-skills/scripts/check.py
```

It says, per skill, **ready** or **not ready**, and prints the install command for each missing
tool on your OS (macOS, Windows or Linux). It installs nothing.

| Skill | Needs |
|---|---|
| motion-web-video | Python 3.10+, Node 22+, Chrome, ffmpeg |
| motion-video | Python 3.10+, ffmpeg, Manim Community |
| training-guide | Python 3.10+, a browser tool for screenshots |
| training-video | uv |

## Use it

Ask in plain words, for example: *"Make a 15-second animated explainer for our new pricing page:
three plans, the middle one highlighted."* The skill asks for a style and colours, renders a
draft, shows you frames, and renders the final only after you say it is right. More examples and
where the files go: [docs/QUICKSTART.md](docs/QUICKSTART.md).

Something wrong? [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md).

## Settings

None for drafts. Optional:

| Variable | For |
|---|---|
| `ELEVENLABS_API_KEY` | the paid voice, after you approve a free draft |
| `CHROME_PATH` | Chrome in an unusual place |
| `TRAINING_VIDEO_BUCKET`, `TRAINING_VIDEO_BASE_URL`, `TRAINING_VIDEO_PREFIX` | training-video: your own S3 bucket for a voice cache and publishing |

The scripts read keys from the environment only and never print them.

## Layout

```
.claude-plugin/        plugin.json and marketplace.json (one-command install)
skills/
├── motion-video/      SKILL.md, scripts/motion.py (render and synth), test
├── motion-web-video/  SKILL.md, example/, templates/ (launch, walkthrough), runtime/ (Motion, MIT), scripts/
├── training-guide/    SKILL.md, scripts/session_screenshots.py
└── training-video/    SKILL.md, scripts/guide_video.py
scripts/               check.py (what your machine needs), install.py (copy the skills)
docs/                  INSTALL, QUICKSTART, TROUBLESHOOTING
AGENTS.md              rules for any coding agent that uses these skills
```

The examples use a made-up product, *Acme Board*, at `board.example.com`.

## Contributing and licence

Issues and pull requests are welcome: [CONTRIBUTING.md](CONTRIBUTING.md). MIT, see
[LICENSE](LICENSE). `skills/motion-web-video/runtime/motion.js` is Motion, MIT, with its own
[licence](skills/motion-web-video/runtime/LICENSE-motion.md). Claude Motion is Anthropic's
product; this project is not affiliated with it.
