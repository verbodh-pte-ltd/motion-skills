---
name: training-video
description: Turn a training guide (docs/training/<App>/<NN-Topic>/<guide>.md, made with the training-guide skill) into a narrated video. Each step shows its screenshot, a step label, and captions that follow an ElevenLabs voice reading the step. Voice clips are cached, so a re-render costs nothing. Use when the user asks for a training video, a walkthrough video, a narrated guide, or "video from the guide".
---

# Training video from a guide

The guide is the source. The video says what the guide says, step by step, over the guide's own
screenshots. Fix wording in the guide, not in the video. Run everything from your repository root.

```bash
R="uv run --frozen --with pillow==12.3.0 --with imageio-ffmpeg==0.6.0 python ${CLAUDE_SKILL_DIR}/scripts/guide_video.py"
G=docs/training/<App>/<NN-Topic>/<guide>.md
```

`uv` brings Pillow and an ffmpeg binary on first use (Windows and Mac). Nothing else to install.

## 1. Check the guide first
- Every step is `### N. Title`, then its text, then its screenshot on its own line. Text above a
  screenshot is read over that screenshot.
- The screenshots are current. A screenshot that shows an old state (a status that is now
  different, a removed button) goes wrong in the video too: retake it first.
- No secrets on any screenshot. A published video is served at a public URL.

## 2. Script: `$R script $G`
Writes `<topic>/video/<guide>/script.json`: one scene per screenshot, plus a title scene and a
"Check that it worked" scene. It prints the scene count and the characters of narration.
- Read every `text`. Shorten long scenes; spoken lines should be short, plain sentences. Edit `script.json` directly, or fix the guide and run `script`
  again (that overwrites your edits).
- Tables and code blocks are not read aloud.

## 3. Write the narration (before any voice)
`script` copies the guide's written sentences. Written text read aloud sounds like a manual, so
rewrite each scene's `text` in `script.json` as speech. Do this after the guide is final:
running `script` again overwrites it (restore with `git checkout -- <script.json>`).

Each scene's `text` is both the voice and the burned-in caption. Write it so it reads well on
screen and sounds right aloud.

| Scene | Write |
|---|---|
| Title | One line on what the viewer will be able to do, then one line on what they need. About 15 seconds. |
| Each shot | Say what to look at on this screenshot, then the one action. One point per scene. Name the button as it appears ("select **Create**" → "select Create"). |
| A card without a screenshot | Only what the next shot needs. If it adds nothing, delete the scene. |
| Check that it worked | Say what the viewer sees when it worked, in two or three sentences. `script` cuts this scene at 600 characters, often mid-sentence: always rewrite it. |
| Closing | Add a last card: where to find the written guide, and one trap to avoid. |

**Rules**
- Sentences of at most 15 words, active voice, one instruction each.
- About 150 spoken words a minute. A shot scene is 10 to 25 seconds, about 25 to 60 words. A scene over 70 words: split it or cut it.
- Speak what the screen shows. Don't read IDs, URLs, file paths or task keys aloud. Say "the task" or "the pull request".
- Spell names as written (Acme Board, GitHub, Copilot), because the caption shows the same text. If the voice says a name wrong, reword around it. Never respell it.
- No parentheses, slashes or arrows: the voice reads them oddly. Write "Claude or Gemini", not "Claude/Gemini".
- Numbers as people say them: "three", "two minutes", "up to five per scan".
- Never read a secret, a key or a personal name.

**Check before the voice step**
1. Read the whole script aloud once, or run `$R voice $G --local` and `$R render $G` for a free draft with the system voice.
2. Count the characters (`script` prints them; recount after edits). Tell the user the count before the first ElevenLabs run.
3. Commit `script.json`, so the narration is reviewed like the guide.

Only changed scenes cost characters on a re-run: the voice cache is keyed by the text.

## 4. Voice: `$R voice $G`
- ElevenLabs, voice **Eric** (`cjVigY5qzO86Huf0OWal`, `eleven_multilingual_v2`). To change it, set
  `voice` in `script.json`; list voices with the account's `/v1/voices`.
- The key: `$ELEVENLABS_API_KEY`. Never print it or write it to a file.
- Cache: each clip is keyed by voice + model + text, stored locally in `voice/`, and also in
  `s3://$TRAINING_VIDEO_BUCKET/media/training/voice/` when that variable is set. Only new or
  changed lines call ElevenLabs. The output says how many were made and how many came from cache.
- Cost: ElevenLabs bills per character. Tell the user the count from step 2 before a first run.
  The free tier has 10,000 characters a month; a 4-minute guide is about 3,400.
- `--local` uses the free system voice (Windows System.Speech, macOS `say`, Linux `espeak-ng`). Use it to check the
  pipeline without spending characters. Captions are then spread by length, not by word timing.

## 5. Render
- Draft: `$R render $G` → `<guide>-draft.mp4`, 1280×720.
- Final: `$R render $G --final` → `<guide>.mp4`, 1920×1080, plus `<guide>.vtt` captions and `poster.png`.
- Captions are burned in and change with the voice's own word timings. The `.vtt` has the same
  lines for players that show subtitles.
- **Look at it before reporting.** Pull two frames and view them:
  `ffmpeg -ss 3 -i <mp4> -frames:v 1 f1.png` (the ffmpeg path: `uv run --frozen --with imageio-ffmpeg==0.6.0 python -c "import imageio_ffmpeg as f;print(f.get_ffmpeg_exe())"`).
  Then open the mp4 for the user to watch.
- **Check the voice is in the file** (a video can look right and be silent):
  `ffmpeg -i <mp4> -t 20 -af volumedetect -f null - 2>&1 | grep -E "Audio:|mean_volume"`.
  You need an `Audio: aac` stream and a mean volume above about −40 dB. Silence (−91 dB) or no
  audio stream means the voice step failed: rerun `voice`, then `render`.

## 6. Publish: `$R publish $G` (optional)
Only after the user says the video is right. It needs an S3 bucket behind a website.
- Set `TRAINING_VIDEO_BUCKET` (for example `example-training-media`) and
  `TRAINING_VIDEO_BASE_URL` (for example `https://www.example.com`). `TRAINING_VIDEO_PREFIX`
  defaults to `media/training`. The AWS CLI uses `AWS_PROFILE` and `AWS_REGION`.
- Uploads the mp4, `.vtt` and poster to
  `s3://$TRAINING_VIDEO_BUCKET/media/training/<App>/<NN-Topic>/<guide>.*`, served from
  `$TRAINING_VIDEO_BASE_URL/media/training/...`.
- Adds a **Watch the video:** line under the guide's title (replaced on a later publish).
- If your site deploy deletes old files from the bucket, exclude `media/*`, or a deploy removes
  the videos.
- **A narrated video is never embedded as muted autoplay.** Browsers autoplay only muted video,
  so the voice is never heard. Embed it stopped, with `controls`, not `muted`, and the published
  `poster` (the `.png` beside the mp4); the visitor's play starts it with sound. Silent loops
  (`autoPlay muted loop`) are only for clips with no voice.
- **Check it on the page, not only the file:** in the browser, the `<video>` must read
  `muted=false controls=true`, and after a play `currentTime` must move.

## What is committed
`script.json` and the `.vtt` are committed with the guide. The mp4, `poster.png` and `voice/` are
not (add them to `.gitignore`); keep them in S3 or another store.

## Report
- The video's URL (or local path before publish), its length and size.
- Characters sent to ElevenLabs this run, and how many clips came from cache.
- Any screenshot that looked out of date in the frames you checked.
