# AGENTS.md — motion-skills

Instructions for any coding agent (Codex, Claude Code, Copilot, Gemini and others) and for the
people who run them. This repository holds four skills that turn product work into short films
and training material.

## The skills

All four live in `skills/<name>/`. Each folder has a `SKILL.md` with the full steps.
Read that file before you start the task it covers.

| Skill | Use it when the user asks for | It makes |
|---|---|---|
| `motion-video` | a 10–30 s explainer, a product teaser, a motion clip for a post | a silent MP4 from Manim scenes and a score written as notes |
| `motion-web-video` | an animated explainer with web-style motion, editable words, an optional voice | an MP4 from a web page animated with Motion, plus a live editor |
| `training-guide` | a write-up of a setup or a feature checked in a browser | a guide in `docs/training/<App>/<NN-Topic>/` with one screenshot per step |
| `training-video` | a video from a training guide | a narrated MP4 with captions timed to the voice |

`motion-web-video` reuses the score synth of `motion-video`. Keep both folders side by side.

## Use them with your agent

- **Codex** reads `.agents/skills/`. Copy the skill folders there in your project.
- **Claude Code** reads `.claude/skills/`. Copy the skill folders into `.claude/skills/` (per
  project) or `~/.claude/skills/` (every project).
- **Other agents:** give the agent the skill's `SKILL.md` as its instructions for the task.

In every `SKILL.md`, `<this skill>` means that skill's folder, for example
`.claude/skills/motion-video`.

## Tools to install

| Skill | Needs |
|---|---|
| `motion-video` | Python 3, Manim Community (`uv tool install manim`), ffmpeg and ffprobe |
| `motion-web-video` | Node 22 or later, Google Chrome, ffmpeg and ffprobe, Python 3. No npm packages |
| `training-guide` | a browser tool that can take screenshots (for example Claude in Chrome) |
| `training-video` | `uv` (it brings Pillow and an ffmpeg binary) |

ffmpeg: `brew install ffmpeg` on macOS, `winget install --id Gyan.FFmpeg -e` on Windows (open a
new shell after it).

## Settings

Drafts need no setting: they use the free system voice and write files locally.

| Variable | Used by | What for |
|---|---|---|
| `ELEVENLABS_API_KEY` | motion-web-video, training-video | the paid voice, only after the user approves a free draft |
| `TRAINING_VIDEO_BUCKET` | training-video | optional S3 bucket for the voice cache and published videos, e.g. `example-training-media` |
| `TRAINING_VIDEO_BASE_URL` | training-video | optional site that serves that bucket, e.g. `https://www.example.com` |
| `TRAINING_VIDEO_PREFIX` | training-video | optional folder in the bucket, default `media/training` |
| `AWS_PROFILE`, `AWS_REGION` | training-video | read by the AWS CLI, only when a bucket is set |
| `CHROME_PATH` | motion-web-video | the Chrome executable, when it is not found |

## Rules for every agent

1. **Draft first, pay last.** Make every film and video with the free system voice first. Use
   ElevenLabs only after the user approves the draft, and tell them the character count before
   the first paid run.
2. **Look before you report.** Take a frame from the middle of each scene and view it. Check that
   the MP4 has sound: `ffmpeg -i <file>.mp4 -af volumedetect -f null -` must show `Audio: aac` and
   a mean volume above about −40 dB.
3. **Every claim on screen is true today.** A feature that is only planned or only on a test site
   is not shown as live.
4. **Nothing private on screen or in a file.** No keys, tokens, passwords, customer names, emails
   or security findings in a screenshot, a film or a commit. Read keys from the environment only;
   never print them or write them to a file.
5. **Use made-up names in shared examples:** the product *Acme Board* at `board.example.com`, the
   bucket `example-training-media`.
6. **Never embed a narrated video as muted autoplay.** Browsers autoplay only muted video, so the
   voice is never heard. Embed it with `controls` and a poster.
7. **Ask, then build.** Ask the user the two questions each film skill lists (style and colours)
   in one go, then build. Do not ask again for what the request already says.

## Check that the skills work

```bash
python skills/motion-video/scripts/test_motion.py       # score maths, cue timing, levels
python skills/motion-web-video/scripts/test_render.py   # renders the example film (Chrome, ffmpeg)
python skills/motion-web-video/scripts/test_voice.py    # free voice, clip reuse, --plan (ffmpeg)
```

The voice test never calls ElevenLabs.

## Layout

```
motion-skills/
├── AGENTS.md                 this file
├── README.md                 overview and install
├── LICENSE                   MIT
└── skills/
    ├── motion-video/         SKILL.md, scripts/motion.py, test
    ├── motion-web-video/     SKILL.md, example/, templates/, runtime/ (Motion, MIT), scripts/
    ├── training-guide/       SKILL.md, scripts/session_screenshots.py
    └── training-video/       SKILL.md, scripts/guide_video.py
```

## Licences

MIT. `skills/motion-web-video/runtime/motion.js` is Motion (motion.dev), MIT, with its
own licence file beside it. Do not copy Motion+ (paid) code into a film or a skill. Claude Motion
is Anthropic's product; do not use its name or branding in published films.
