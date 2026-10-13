# Quickstart

After [INSTALL.md](INSTALL.md), ask your agent in plain words. Each skill asks one or two short
questions first (style, colours), makes a free draft, and waits for your OK before the final.

## A web film in about ten minutes (motion-web-video)

> Make a 15-second animated explainer for our new pricing page: three plans, the middle one
> highlighted. Use our colours, #0B1E3F and #FF6B35.

What happens:
1. It asks you to pick one of three visual ideas.
2. It writes `film.html` and `film.json` in a new folder and renders `draft.mp4` (960×540).
3. It shows you frames from each scene. Say "open the editor" to change words and colours
   yourself: it starts a local page with a side panel and a **Save to film.json** button.
4. When you say the draft is right, it renders `final.mp4` (1920×1080) and `poster.png`.

Add a voice: "add a narration line per scene". The draft voice is your system voice (free).
For an ElevenLabs voice, set `ELEVENLABS_API_KEY`; it tells you the character count first.

## A short Manim explainer (motion-video)

> Make a 20-second motion video that shows how our app turns a request into a plan, then a pull
> request. No voice.

You get scenes in `scenes.py`, a score in `film.json`, then `draft.mp4` and, after your OK,
`final.mp4`. The music is generated from notes, so there is nothing to license.

## A training guide from what you just did (training-guide)

> Write a training guide for the Google Search Console setup we just did, with a screenshot per
> step.

You get `docs/training/<App>/<NN-Topic>/<guide>.md` with numbered steps, one screenshot per
step, "Check that it worked" and "Traps we hit". It never puts a key or password on screen.

## A video from that guide (training-video)

> Make a narrated video from docs/training/Acme-Board/01-Search-Console/add-an-owner.md.

You get `script.json` (the spoken words, one scene per screenshot) to review, a free draft with
the system voice, then the final MP4 with captions and a `.vtt` file.

## Where the files go

The film folders hold everything needed to render again: commit `film.html` + `film.json` (or
`scenes.py` + `film.json`) next to the page or post that uses the film. MP4s and voice clips
are build output; keep them out of git.
