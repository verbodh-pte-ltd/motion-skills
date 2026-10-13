"""Turn a training guide (docs/training/<App>/<NN-Topic>/<guide>.md) into a narrated video.

Each guide step becomes a scene: its screenshot, a step label, a caption bar that shows the
words as the voice reads them, and an ElevenLabs voice. Voice clips are made once and cached
locally (and in S3 when TRAINING_VIDEO_BUCKET is set), keyed by voice + model + text, so a
re-render never calls ElevenLabs again.

    uv run --with pillow==12.3.0 --with imageio-ffmpeg==0.6.0 python guide_video.py script  <guide.md>
    uv run --with pillow==12.3.0 --with imageio-ffmpeg==0.6.0 python guide_video.py voice   <guide.md> [--local]
    uv run --with pillow==12.3.0 --with imageio-ffmpeg==0.6.0 python guide_video.py render  <guide.md> [--final]
    uv run --with pillow==12.3.0 --with imageio-ffmpeg==0.6.0 python guide_video.py publish <guide.md>

script  writes <topic>/video/<guide>/script.json from the guide: read and edit it first.
voice   makes one clip per scene (ElevenLabs, or --local for the free system voice).
render  writes <guide>.mp4 (+ .vtt captions). Draft is 1280x720; --final is 1920x1080.
publish uploads the final video and captions to S3 and adds a "Watch the video" link to the guide.

Environment: ELEVENLABS_API_KEY (paid voice). Optional S3 cache and publish: TRAINING_VIDEO_BUCKET,
TRAINING_VIDEO_PREFIX, TRAINING_VIDEO_BASE_URL; the AWS CLI reads AWS_PROFILE and AWS_REGION.
"""
import argparse, hashlib, json, os, pathlib, platform, re, shutil, subprocess, sys, tempfile, urllib.request

AWS = ["aws"]  # profile and region from AWS_PROFILE / AWS_REGION
BUCKET = os.environ.get("TRAINING_VIDEO_BUCKET")  # e.g. example-training-media; unset: no S3
PREFIX = os.environ.get("TRAINING_VIDEO_PREFIX", "media/training")
BASE_URL = os.environ.get("TRAINING_VIDEO_BASE_URL")  # e.g. https://www.example.com
DEFAULT_VOICE = {"id": "cjVigY5qzO86Huf0OWal", "name": "Eric - Smooth, Trustworthy", "model": "eleven_multilingual_v2"}

BG, FG, MUTED, BAND, ACCENT = (15, 22, 38), (245, 246, 248), (160, 168, 184), (15, 22, 38, 235), (229, 83, 42)
FONT_DIRS = ["C:/Windows/Fonts", "/System/Library/Fonts/Supplemental", "/Library/Fonts", "/usr/share/fonts/truetype/dejavu"]
FONT_REGULAR = ["segoeui.ttf", "Arial.ttf", "arial.ttf", "DejaVuSans.ttf"]
FONT_BOLD = ["segoeuib.ttf", "Arial Bold.ttf", "arialbd.ttf", "DejaVuSans-Bold.ttf"]


# ---------- guide -> script ----------

def plain(md):
    """Markdown to spoken words: links keep their text, emphasis and code marks go."""
    s = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", md)
    s = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", s)
    s = re.sub(r"<!--.*?-->", "", s, flags=re.S)
    s = s.replace("**", "").replace("__", "").replace("`", "")
    s = re.sub(r"(?<!\w)\*([^*]+)\*(?!\w)", r"\1", s)
    s = re.sub(r"^\s*[-*]\s+", "", s, flags=re.M)
    s = s.replace("→", "then").replace("·", ",")
    return re.sub(r"\s+", " ", s).strip()


def parse_guide(path):
    text = path.read_text(encoding="utf-8")
    title = re.search(r"^# (.+)$", text, re.M).group(1).strip()
    purpose = re.search(r"\*\*Purpose\.\*\*(.+?)(?:\n\*\*|\n\n|\Z)", text, re.S)
    scenes = [{"kind": "title", "heading": title, "text": f"{title}. {plain(purpose.group(1))}" if purpose else title}]
    steps = re.split(r"^### ", text, flags=re.M)[1:]
    for block in steps:
        head, _, body = block.partition("\n")
        body = re.split(r"^## ", body, flags=re.M)[0]  # a step ends at the next section
        m = re.match(r"(\d+)\.\s*(.+)", head.strip())
        num, heading = (m.group(1), m.group(2)) if m else ("", head.strip())
        label = f"Step {num} · {plain(heading)}" if num else plain(heading)
        pending, beats = [], []
        body = re.sub(r"```.*?```", "", body, flags=re.S)  # code is read on the page, not aloud
        for line in body.splitlines():
            if line.lstrip().startswith("|"):
                continue  # so are tables
            img = re.search(r"!\[[^\]]*\]\(([^)]+)\)", line)
            if img:  # a screenshot closes the words written above it
                beats.append({"image": img.group(1), "text": " ".join(pending)})
                pending = []
            elif plain(line):
                pending.append(plain(line))
        if pending:
            if beats:
                beats[-1]["text"] = (beats[-1]["text"] + " " + " ".join(pending)).strip()
            else:
                beats.append({"image": None, "text": " ".join(pending)})
        for i, b in enumerate(beats):
            spoken = b["text"] if i else f"{plain(heading)}. {b['text']}"
            scenes.append({"kind": "shot" if b["image"] else "card", "heading": label, "image": b["image"], "text": spoken.strip()})
    check = re.search(r"^## Check that it worked\s*\n(.+?)(?=^## |\Z)", text, re.S | re.M)
    if check:
        scenes.append({"kind": "card", "heading": "Check that it worked", "image": None, "text": plain(check.group(1))[:600]})
    for i, s in enumerate(scenes, 1):
        s["id"] = f"s{i:02d}"
    return {"guide": str(path), "title": title, "voice": DEFAULT_VOICE, "scenes": scenes}


def workdir(guide):
    d = guide.parent / "video" / guide.stem
    d.mkdir(parents=True, exist_ok=True)
    return d


def load_script(guide):
    p = workdir(guide) / "script.json"
    if not p.exists():
        sys.exit(f"No script yet. Run: script {guide}")
    return json.loads(p.read_text(encoding="utf-8"))


# ---------- voice ----------

def aws(*args, check=True):
    return subprocess.run([*AWS, *args], capture_output=True, text=True, check=check)


def api_key():
    key = os.environ.get("ELEVENLABS_API_KEY")
    if not key:
        sys.exit("No ElevenLabs key: set ELEVENLABS_API_KEY, or use --local for the free system voice.")
    return key


def eleven(key, voice, text):
    import base64
    body = json.dumps({"text": text, "model_id": voice["model"], "voice_settings": {"stability": 0.55, "similarity_boost": 0.75}}).encode()
    req = urllib.request.Request(
        f"https://api.elevenlabs.io/v1/text-to-speech/{voice['id']}/with-timestamps?output_format=mp3_44100_128",
        data=body, headers={"xi-api-key": key, "Content-Type": "application/json"})
    res = json.load(urllib.request.urlopen(req))
    a = res["alignment"]
    return base64.b64decode(res["audio_base64"]), {"text": text, "starts": a["character_start_times_seconds"], "ends": a["character_end_times_seconds"]}


def local_voice(text, out):
    """Free voice: Windows System.Speech, macOS say, or espeak-ng on Linux. No timings, so captions
    are spread by length."""
    if platform.system() == "Linux":
        wav = out.with_suffix(".wav")
        subprocess.run(["espeak-ng", "-w", str(wav), text], check=True)
    elif platform.system() == "Windows":
        wav = out.with_suffix(".wav")
        ps = ("Add-Type -AssemblyName System.Speech; $s=New-Object System.Speech.Synthesis.SpeechSynthesizer; "
              f"$s.SetOutputToWaveFile('{wav}'); $s.Speak([Console]::In.ReadToEnd()); $s.Dispose()")
        subprocess.run(["powershell", "-NoProfile", "-Command", ps], input=text, text=True, check=True)
    else:
        wav = out.with_suffix(".aiff")
        subprocess.run(["say", "-o", str(wav), text], check=True)
    subprocess.run([ffmpeg(), "-y", "-loglevel", "error", "-i", str(wav), "-b:a", "128k", str(out)], check=True)
    wav.unlink()
    return {"text": text, "starts": None, "ends": None}


def voice(guide, local=False):
    script = load_script(guide)
    v, d = script["voice"], workdir(guide) / "voice"
    d.mkdir(exist_ok=True)
    key, made, cached = None, 0, 0
    for s in script["scenes"]:
        tag = "local" if local else f"{v['id']}|{v['model']}"
        h = hashlib.sha256(f"{tag}|{s['text']}".encode()).hexdigest()[:16]
        mp3, meta = d / f"{h}.mp3", d / f"{h}.json"
        s["voice"] = h
        if mp3.exists() and meta.exists():
            cached += 1
            continue
        remote = f"s3://{BUCKET}/{PREFIX}/voice/{h}"
        if not local and BUCKET and aws("s3", "cp", remote + ".mp3", str(mp3), check=False).returncode == 0:
            aws("s3", "cp", remote + ".json", str(meta))
            cached += 1
            continue
        if local:
            info = local_voice(s["text"], mp3)
        else:
            key = key or api_key()
            audio, info = eleven(key, v, s["text"])
            mp3.write_bytes(audio)
        meta.write_text(json.dumps(info), encoding="utf-8")
        if not local and BUCKET:
            cc = "public, max-age=31536000, immutable"
            aws("s3", "cp", str(mp3), remote + ".mp3", "--cache-control", cc, "--content-type", "audio/mpeg")
            aws("s3", "cp", str(meta), remote + ".json", "--cache-control", cc, "--content-type", "application/json")
        made += 1
        print(f"{s['id']}: made ({len(s['text'])} characters)")
    (workdir(guide) / "script.json").write_text(json.dumps(script, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"voice: {made} made, {cached} from cache")


# ---------- render ----------

def ffmpeg():
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()


def duration(mp3):
    out = subprocess.run([ffmpeg(), "-i", str(mp3)], capture_output=True, text=True).stderr
    hh, mm, ss = re.search(r"Duration: (\d+):(\d+):([\d.]+)", out).groups()
    return int(hh) * 3600 + int(mm) * 60 + float(ss)


def font(names, size):
    from PIL import ImageFont
    for d in FONT_DIRS:
        for n in names:
            p = pathlib.Path(d) / n
            if p.exists():
                return ImageFont.truetype(str(p), size)
    return ImageFont.load_default(size)


def chunks(text, limit):
    """Caption chunks of whole words, at most `limit` characters, breaking at sentence ends first."""
    out = []
    for sentence in re.split(r"(?<=[.!?:])\s+", text):
        line = ""
        for w in sentence.split():
            if line and len(line) + 1 + len(w) > limit:
                out.append(line)
                line = w
            else:
                line = f"{line} {w}".strip()
        if line:
            out.append(line)
    return out


def timings(text, meta, total, parts):
    """Start time of each caption chunk: ElevenLabs character times, else spread by length."""
    starts, pos = [], 0
    for p in parts:
        i = text.find(p, pos)
        i = pos if i < 0 else i
        if meta.get("starts"):
            starts.append(meta["starts"][min(i, len(meta["starts"]) - 1)])
        else:
            starts.append(total * i / max(len(text), 1))
        pos = i + len(p)
    return starts


def wrap(draw, text, fnt, width):
    lines, line = [], ""
    for w in text.split():
        trial = f"{line} {w}".strip()
        if draw.textlength(trial, font=fnt) > width and line:
            lines.append(line)
            line = w
        else:
            line = trial
    return lines + ([line] if line else [])


def frame(scene, caption, size, guide_dir, step_note):
    from PIL import Image, ImageDraw
    W, H = size
    k = W / 1920
    img = Image.new("RGB", size, BG)
    d = ImageDraw.Draw(img, "RGBA")
    band = int(190 * k)
    top = int(96 * k)
    if scene["kind"] == "shot" and scene.get("image"):
        shot = Image.open(guide_dir / scene["image"]).convert("RGB")
        box_w, box_h = W - int(120 * k), H - band - top - int(24 * k)
        r = min(box_w / shot.width, box_h / shot.height)
        shot = shot.resize((int(shot.width * r), int(shot.height * r)), Image.LANCZOS)
        x, y = (W - shot.width) // 2, top + (box_h - shot.height) // 2
        d.rectangle([x - 2, y - 2, x + shot.width + 1, y + shot.height + 1], outline=(70, 80, 100))
        img.paste(shot, (x, y))
    else:
        big = font(FONT_BOLD, int(64 * k))
        lines = wrap(d, scene["heading"], big, W - int(320 * k))
        y = (H - band) // 2 - len(lines) * int(40 * k)
        for ln in lines:
            d.text((W // 2, y), ln, font=big, fill=FG, anchor="ma")
            y += int(80 * k)
    # step label, top left
    lab = font(FONT_BOLD, int(30 * k))
    d.rounded_rectangle([int(48 * k), int(28 * k), int(48 * k) + int(14 * k), int(28 * k) + int(40 * k)], radius=int(4 * k), fill=ACCENT)
    d.text((int(76 * k), int(48 * k)), scene["heading"] if scene["kind"] != "title" else "Training", font=lab, fill=FG, anchor="lm")
    d.text((W - int(48 * k), int(48 * k)), step_note, font=font(FONT_REGULAR, int(24 * k)), fill=MUTED, anchor="rm")
    # caption band
    d.rectangle([0, H - band, W, H], fill=BAND)
    cap = font(FONT_REGULAR, int(44 * k))
    lines = wrap(d, caption, cap, W - int(240 * k))[:2]
    y = H - band // 2 - (len(lines) * int(56 * k)) // 2
    for ln in lines:
        d.text((W // 2, y), ln, font=cap, fill=FG, anchor="ma")
        y += int(56 * k)
    return img


def vtt_time(t):
    h, rem = divmod(t, 3600)
    m, s = divmod(rem, 60)
    return f"{int(h):02d}:{int(m):02d}:{s:06.3f}"


def render(guide, final=False):
    script = load_script(guide)
    if any("voice" not in s for s in script["scenes"]):
        sys.exit(f"Voice missing. Run: voice {guide}")
    size = (1920, 1080) if final else (1280, 720)
    work, vdir = workdir(guide), workdir(guide) / "voice"
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="guide-video-"))
    lead, tail = 0.35, 0.6
    segments, cues, clock = [], [], 0.0
    n = len(script["scenes"])
    for idx, s in enumerate(script["scenes"], 1):
        mp3 = vdir / f"{s['voice']}.mp3"
        meta = json.loads((vdir / f"{s['voice']}.json").read_text(encoding="utf-8"))
        talk = duration(mp3)
        total = lead + talk + tail
        parts = chunks(s["text"], 90)
        starts = timings(s["text"], meta, talk, parts)
        listing = []
        for j, (p, st) in enumerate(zip(parts, starts)):
            begin = 0 if j == 0 else lead + st
            end = total if j == len(parts) - 1 else lead + starts[j + 1]
            f = tmp / f"{s['id']}_{j:02d}.png"
            frame(s, p, size, guide.parent, f"{idx} / {n}").save(f)
            listing.append((f, max(end - begin, 0.1)))
            cues.append((clock + begin, clock + end, p))
        lst = tmp / f"{s['id']}.txt"
        lst.write_text("".join(f"file '{f.as_posix()}'\nduration {dur:.3f}\n" for f, dur in listing) + f"file '{listing[-1][0].as_posix()}'\n", encoding="utf-8")
        seg = tmp / f"{s['id']}.mp4"
        subprocess.run([ffmpeg(), "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(lst), "-i", str(mp3),
                        "-filter_complex", f"[1:a]adelay={int(lead * 1000)}:all=1,apad[a]", "-map", "0:v", "-map", "[a]",
                        "-t", f"{total:.3f}", "-r", "30", "-c:v", "libx264", "-preset", "medium", "-crf", "22" if final else "28",
                        "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "128k", "-ar", "44100", str(seg)], check=True)
        segments.append(seg)
        clock += total
        print(f"{s['id']}: {total:.1f} s")
    all_list = tmp / "all.txt"
    all_list.write_text("".join(f"file '{p.as_posix()}'\n" for p in segments), encoding="utf-8")
    out = work / f"{guide.stem}{'' if final else '-draft'}.mp4"
    subprocess.run([ffmpeg(), "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(all_list), "-c", "copy", "-movflags", "+faststart", str(out)], check=True)
    (out.with_suffix(".vtt")).write_text("WEBVTT\n\n" + "".join(f"{vtt_time(a)} --> {vtt_time(b)}\n{t}\n\n" for a, b, t in cues), encoding="utf-8")
    poster = tmp / "s02_00.png"
    shutil.copy(poster if poster.exists() else tmp / "s01_00.png", work / "poster.png")
    shutil.rmtree(tmp, ignore_errors=True)
    print(f"wrote {out} ({out.stat().st_size / 1e6:.1f} MB, {clock:.0f} s) and {out.with_suffix('.vtt').name}")


# ---------- publish ----------

def publish(guide):
    work = workdir(guide)
    mp4, vtt, poster = work / f"{guide.stem}.mp4", work / f"{guide.stem}.vtt", work / "poster.png"
    if not mp4.exists():
        sys.exit(f"No final video. Run: render {guide} --final")
    if not (BUCKET and BASE_URL):
        sys.exit("publish needs TRAINING_VIDEO_BUCKET and TRAINING_VIDEO_BASE_URL.")
    rel = guide.parent.relative_to(guide.parents[2]).as_posix()  # <App>/<NN-Topic>
    key = f"{PREFIX}/{rel}/{guide.stem}"
    for f, ct in ((mp4, "video/mp4"), (vtt, "text/vtt"), (poster, "image/png")):
        aws("s3", "cp", str(f), f"s3://{BUCKET}/{key}{f.suffix}", "--content-type", ct, "--cache-control", "public, max-age=300")
    url = f"{BASE_URL}/{key}.mp4"
    text = guide.read_text(encoding="utf-8")
    line = f"**Watch the video:** {url} (captions: {BASE_URL}/{key}.vtt)"
    if "**Watch the video:**" in text:
        text = re.sub(r"\*\*Watch the video:\*\*.*", line, text)
    else:
        text = re.sub(r"^(# .+\n)", rf"\1\n{line}\n", text, count=1)
    guide.write_text(text, encoding="utf-8")
    print(url)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("step", choices=["script", "voice", "render", "publish"])
    ap.add_argument("guide", type=pathlib.Path)
    ap.add_argument("--local", action="store_true", help="free system voice instead of ElevenLabs")
    ap.add_argument("--final", action="store_true", help="1920x1080 instead of the 1280x720 draft")
    a = ap.parse_args()
    guide = a.guide.resolve()
    if a.step == "script":
        p = workdir(guide) / "script.json"
        p.write_text(json.dumps(parse_guide(guide), indent=2, ensure_ascii=False), encoding="utf-8")
        s = json.loads(p.read_text(encoding="utf-8"))
        chars = sum(len(x["text"]) for x in s["scenes"])
        print(f"wrote {p}: {len(s['scenes'])} scenes, {chars} characters of narration")
    elif a.step == "voice":
        voice(guide, a.local)
    elif a.step == "render":
        render(guide, a.final)
    else:
        publish(guide)


if __name__ == "__main__":
    main()
