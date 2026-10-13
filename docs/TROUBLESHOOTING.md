# Troubleshooting

Run `python scripts/check.py` first: most problems are a missing tool.

| What you see | Why | Do this |
|---|---|---|
| `ffmpeg` or `ffprobe` not found on Windows, right after `winget install` | the shell started before the install changed PATH | open a new shell |
| `Chrome not found; set CHROME_PATH` | Chrome is not in a standard place | set `CHROME_PATH` to the Chrome (or Chromium) executable |
| `Chrome did not start` | another Chrome policy or a sandbox blocks headless Chrome | close other headless runs; on Linux CI, check Chrome runs with `--headless=new` |
| The MP4 looks right but is silent | the score has no events, or the voice step failed | check with `ffmpeg -i film.mp4 -af volumedetect -f null -`: you need `Audio: aac` and a mean volume above about −40 dB |
| A scene shows during the wrong scene | a rule like `display: grid` on a section beat the `hidden` attribute | keep `runtime/film.css` loaded; it forces hidden sections off |
| Text is soft in a walkthrough film | the capture was zoomed more than 2× | capture the window larger, or zoom less |
| Manim text looks small in 9:16 or 1:1 | Manim keeps the frame width | stack content vertically and scale it up |
| Manim shows a serif font | the default font | pass `font="Segoe UI"` (Windows) or `"Helvetica Neue"` (macOS) |
| `No ElevenLabs key` | the paid voice was asked for without a key | set `ELEVENLABS_API_KEY`, or use the free draft voice |
| The free voice fails on Linux | espeak-ng is not installed | `sudo apt install espeak-ng` |
| A narrated video plays silent on a web page | it was embedded as muted autoplay | embed it with `controls` and a poster, not `muted autoplay` |
| `publish needs TRAINING_VIDEO_BUCKET and TRAINING_VIDEO_BASE_URL` | publishing is optional and needs your own bucket | set both, or share the local MP4 instead |
| `motion-web-video` cannot import `motion` | `motion-video` is not installed beside it | install both skills (the plugin and `install.py` do this) |

Still stuck? Open an issue with the command, the full error and the output of
`python scripts/check.py`. Never paste a key.
