# motion-skills

Four Claude Code skills that turn work you already do into short films and training material:
animated product explainers, a narrated web film, and step-by-step training guides with a video.
Every film is code, so a re-render gives the same film, frame for frame.

## The skills

| Skill | What it makes | Needs |
|---|---|---|
| [motion-video](skills/motion-video/SKILL.md) | A 10–30 s silent explainer: Manim scenes and an original score written as notes | Python 3, Manim Community, ffmpeg |
| [motion-web-video](skills/motion-web-video/SKILL.md) | A 5–60 s web film animated with [Motion](https://motion.dev), rendered to MP4, with a live editor for words and colours and an optional voice | Node 22+, Google Chrome, ffmpeg, Python 3 |
| [training-guide](skills/training-guide/SKILL.md) | A training guide from a browser click-through: purpose, numbered steps, one screenshot per step, checks and traps | nothing extra |
| [training-video](skills/training-video/SKILL.md) | A narrated video from a training guide: screenshots, step labels, captions timed to the voice | `uv` (brings Pillow and ffmpeg) |

`motion-web-video` reuses the score synth of `motion-video`: install both side by side.

## Install

Copy the skills you want into your project's `.claude/skills/` folder, or into `~/.claude/skills/`
to use them in every project:

```bash
git clone https://github.com/verbodh-pte-ltd/motion-skills.git
cp -r motion-skills/skills/* your-project/.claude/skills/
```

Claude Code loads a skill when your request matches its description, for example "make a
20-second explainer of our new pricing page" or "write a training guide for what we just set up".

## Settings

No setting is needed for drafts: they use the free system voice and write files locally.

| Variable | Used by | What for |
|---|---|---|
| `ELEVENLABS_API_KEY` | motion-web-video, training-video | the paid ElevenLabs voice, only after you approve a draft |
| `TRAINING_VIDEO_BUCKET` | training-video | optional: an S3 bucket for the voice cache and published videos, for example `example-training-media` |
| `TRAINING_VIDEO_BASE_URL` | training-video | optional: the site that serves the bucket, for example `https://www.example.com` |
| `TRAINING_VIDEO_PREFIX` | training-video | optional: the folder in the bucket, default `media/training` |
| `AWS_PROFILE`, `AWS_REGION` | training-video | read by the AWS CLI when a bucket is set |
| `CHROME_PATH` | motion-web-video | the Chrome executable, when it is not found |

Never commit a key. The scripts read keys from the environment only and never print them.

## Check that they work

```bash
python skills/motion-video/scripts/test_motion.py        # score maths, cue timing, levels
python skills/motion-web-video/scripts/test_render.py    # renders the example film (Chrome, ffmpeg)
python skills/motion-web-video/scripts/test_voice.py     # free voice, clip reuse, --plan (ffmpeg)
```

The voice test never calls ElevenLabs.

## Layout

```
skills/
├── motion-video/        SKILL.md, scripts/motion.py (render + synth), test
├── motion-web-video/    SKILL.md, example/ film, templates/ (launch, walkthrough),
│                        runtime/ (Motion 12.23.24, player, CSS), scripts/ (render, voice, mix, tests)
├── training-guide/      SKILL.md, scripts/session_screenshots.py
└── training-video/      SKILL.md, scripts/guide_video.py
```

The examples use a made-up product, *Acme Board*, at `board.example.com`.

## Licence

MIT, see [LICENSE](LICENSE). `skills/motion-web-video/runtime/motion.js` is Motion, MIT, with
its own licence in [LICENSE-motion.md](skills/motion-web-video/runtime/LICENSE-motion.md).
Claude Motion is Anthropic's product; these skills are not affiliated with it.
