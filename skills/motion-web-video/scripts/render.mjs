#!/usr/bin/env node
// Render a Motion film page to MP4 with headless Chrome and ffmpeg. No npm packages.
//
// usage: node render.mjs <film_dir> draft|final        -> <film_dir>/draft.mp4 or final.mp4 (+ poster.png on final)
//        node render.mjs <film_dir> still <sec> <out.png>   one frame, full size
//        node render.mjs <film_dir> edit                 serve the editor at http://127.0.0.1:<port>/film.html?edit
//        node render.mjs <film_dir> preview              serve the preview page
//
// <film_dir> holds film.html and film.json. The page loads /runtime/motion.js and /runtime/player.js,
// which this script serves from the skill's runtime folder.
import { createServer } from "node:http";
import { spawn, spawnSync } from "node:child_process";
import { existsSync, mkdtempSync, readFileSync, rmSync, writeFileSync, createReadStream, statSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, extname, join, resolve, sep } from "node:path";
import { fileURLToPath } from "node:url";

const HERE = dirname(fileURLToPath(import.meta.url));
const RUNTIME = resolve(HERE, "..", "runtime");
const SHAPES = { "16:9": [1920, 1080], "1:1": [1080, 1080], "9:16": [1080, 1920] };
const TYPES = { ".html": "text/html", ".js": "text/javascript", ".mjs": "text/javascript", ".css": "text/css",
  ".json": "application/json", ".png": "image/png", ".jpg": "image/jpeg", ".svg": "image/svg+xml",
  ".woff2": "font/woff2", ".ttf": "font/ttf" };

const [dirArg, mode = "draft", ...rest] = process.argv.slice(2);
if (!dirArg || !["draft", "final", "still", "edit", "preview"].includes(mode)) {
  console.error("usage: node render.mjs <film_dir> draft|final|still <sec> <out.png>|edit|preview");
  process.exit(2);
}
const root = resolve(dirArg);
if (!existsSync(join(root, "film.html"))) fail(`no film.html in ${root}`);
const film = JSON.parse(readFileSync(join(root, "film.json"), "utf8"));
const [W, H] = SHAPES[film.shape ?? "16:9"] ?? fail(`unknown shape ${film.shape}`);

function fail(msg) { console.error(msg); process.exit(1); }

function serve({ allowSave }) {
  const server = createServer((req, res) => {
    const url = new URL(req.url, "http://x");
    if (req.method === "POST" && url.pathname === "/save") {
      if (!allowSave) { res.writeHead(403).end("saving is only on in edit mode"); return; }
      let body = "";
      req.on("data", c => (body += c));
      req.on("end", () => {
        try { JSON.parse(body); } catch { res.writeHead(400).end("not valid JSON"); return; }
        writeFileSync(join(root, "film.json"), body + "\n");
        res.writeHead(200).end("saved");
      });
      return;
    }
    const base = url.pathname.startsWith("/runtime/") ? RUNTIME : root;
    const rel = decodeURIComponent(url.pathname.replace(/^\/runtime\//, "/")).slice(1) || "film.html";
    const file = resolve(base, rel);
    if (!file.startsWith(base + sep) || !existsSync(file) || !statSync(file).isFile()) { res.writeHead(404).end(); return; }
    res.writeHead(200, { "Content-Type": TYPES[extname(file)] ?? "application/octet-stream", "Cache-Control": "no-store" });
    createReadStream(file).pipe(res);
  });
  return new Promise(r => server.listen(0, "127.0.0.1", () => r(server)));
}

function findChrome() {
  const paths = [process.env.CHROME_PATH,
    "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
    "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/usr/bin/google-chrome", "/usr/bin/chromium"];
  return paths.find(p => p && existsSync(p)) ?? fail("Chrome not found; set CHROME_PATH");
}

async function launchChrome() {
  const profile = mkdtempSync(join(tmpdir(), "mwv-chrome-"));
  const proc = spawn(findChrome(), ["--headless=new", "--remote-debugging-port=0", `--user-data-dir=${profile}`,
    "--hide-scrollbars", "--mute-audio", "--no-first-run", "--no-default-browser-check", "--force-color-profile=srgb",
    "--disable-background-timer-throttling", "--disable-renderer-backgrounding", "about:blank"], { stdio: "ignore" });
  const portFile = join(profile, "DevToolsActivePort");
  for (let i = 0; i < 100 && !existsSync(portFile); i++) await new Promise(r => setTimeout(r, 100));
  if (!existsSync(portFile)) fail("Chrome did not start");
  await new Promise(r => setTimeout(r, 100));
  const port = readFileSync(portFile, "utf8").split("\n")[0].trim();
  const target = await (await fetch(`http://127.0.0.1:${port}/json/new?about:blank`, { method: "PUT" })).json();
  const ws = new WebSocket(target.webSocketDebuggerUrl);
  await new Promise((r, j) => { ws.onopen = r; ws.onerror = j; });
  let id = 0;
  const pending = new Map();
  ws.onmessage = e => {
    const m = JSON.parse(e.data);
    if (m.id && pending.has(m.id)) {
      const { r, j } = pending.get(m.id); pending.delete(m.id);
      m.error ? j(new Error(m.error.message)) : r(m.result);
    }
  };
  const send = (method, params = {}) => new Promise((r, j) => { pending.set(++id, { r, j }); ws.send(JSON.stringify({ id, method, params })); });
  const close = async () => {
    ws.close();
    const exited = new Promise(r => proc.once("exit", r));
    proc.kill();
    await exited;
    // Windows keeps the profile locked for a moment after Chrome exits.
    try { rmSync(profile, { recursive: true, force: true, maxRetries: 10, retryDelay: 200 }); } catch { /* temp folder; the OS clears it */ }
  };
  return { send, close };
}

async function evaluate(send, expression) {
  const out = await send("Runtime.evaluate", { expression, awaitPromise: true, returnByValue: true });
  if (out.exceptionDetails) throw new Error(out.exceptionDetails.exception?.description ?? out.exceptionDetails.text);
  return out.result.value;
}

async function openFilm(send, url, scale) {
  await send("Emulation.setDeviceMetricsOverride", { width: W, height: H, deviceScaleFactor: scale, mobile: false });
  await send("Page.enable");
  await send("Runtime.enable");
  await send("Page.navigate", { url });
  for (let i = 0; i < 200; i++) {
    const state = await evaluate(send, "window.__film?.ready ? 'ok' : (window.__filmError ?? '')").catch(() => "");
    if (state === "ok") return evaluate(send, "({ total: __film.total, scenes: __film.scenes })");
    if (state) fail(`film page error: ${state}`);
    await new Promise(r => setTimeout(r, 50));
  }
  fail("film page never became ready (check the browser console with: render.mjs <dir> preview)");
}

async function shot(send, format) {
  const { data } = await send("Page.captureScreenshot", { format, ...(format === "jpeg" ? { quality: 92 } : {}),
    clip: { x: 0, y: 0, width: W, height: H, scale: 1 }, captureBeyondViewport: false });
  return Buffer.from(data, "base64");
}

function run(cmd, args) {
  const r = spawnSync(cmd, args, { stdio: ["ignore", "inherit", "inherit"] });
  if (r.status !== 0) fail(`${cmd} failed (${r.status ?? r.error?.message})`);
}

async function render(server) {
  if (spawnSync("ffmpeg", ["-version"]).error) fail("ffmpeg not found on PATH (on Windows, open a new shell after winget install)");
  const draft = mode === "draft";
  const fps = draft ? 15 : 30;
  const chrome = await launchChrome();
  try {
    const url = `http://127.0.0.1:${server.address().port}/film.html?render`;
    const timing = await openFilm(chrome.send, url, draft ? 0.5 : 1);
    writeFileSync(join(root, "timing.json"), JSON.stringify(timing, null, 2) + "\n");
    const silent = join(root, `${mode}.video.mp4`);
    const ff = spawn("ffmpeg", ["-loglevel", "error", "-y", "-f", "image2pipe", "-framerate", String(fps), "-i", "-",
      "-c:v", "libx264", "-pix_fmt", "yuv420p", "-vf", "pad=ceil(iw/2)*2:ceil(ih/2)*2", silent],
      { stdio: ["pipe", "inherit", "inherit"] });
    const done = new Promise(r => ff.on("close", r));
    const frames = Math.round(timing.total * fps);
    for (let i = 0; i < frames; i++) {
      await evaluate(chrome.send, `__film.seek(${i / fps})`);
      const img = await shot(chrome.send, draft ? "jpeg" : "png");
      if (!ff.stdin.write(img)) await new Promise(r => ff.stdin.once("drain", r));
    }
    ff.stdin.end();
    if ((await done) !== 0) fail("ffmpeg could not encode the frames");

    const out = join(root, `${mode}.mp4`);
    // Sound: the score (if any) plus each scene's narration at its start. Under a voice the
    // score drops to 35%, so the words stay clear.
    const inputs = [], labels = [];
    const voices = timing.scenes.filter(s => s.voice);
    if (film.score?.events?.length) {
      run(process.platform === "win32" ? "python" : "python3", [join(HERE, "mix.py"), root]);
      inputs.push("-i", join(root, "score.wav"));
      labels.push(`[1:a]volume=${voices.length ? 0.35 : 1}[a0]`);
    }
    voices.forEach(s => {
      const n = inputs.length / 2 + 1;
      inputs.push("-i", join(root, s.voice.file));
      const ms = Math.round(s.voice.at * 1000);
      labels.push(`[${n}:a]aresample=44100,adelay=${ms}:all=1[a${n - 1}]`);
    });
    if (labels.length) {
      const mix = `${labels.join(";")};${labels.map((_, i) => `[a${i}]`).join("")}amix=inputs=${labels.length}:normalize=0:duration=longest,apad[aout]`;
      run("ffmpeg", ["-loglevel", "error", "-y", "-i", silent, ...inputs, "-filter_complex", mix, "-map", "0:v", "-map", "[aout]",
        "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", out]);
    } else {
      run("ffmpeg", ["-loglevel", "error", "-y", "-i", silent, "-c", "copy", "-movflags", "+faststart", out]);
    }
    rmSync(silent, { force: true });
    if (!draft) {
      await chrome.send("Emulation.setDeviceMetricsOverride", { width: W, height: H, deviceScaleFactor: 1, mobile: false });
      await evaluate(chrome.send, `__film.seek(${Math.max(0, timing.total - 1)})`);
      writeFileSync(join(root, "poster.png"), await shot(chrome.send, "png"));
    }
    console.log(`${out} (${timing.total.toFixed(1)}s, ${draft ? W / 2 : W}x${draft ? H / 2 : H} ${fps}fps, ${frames} frames)`);
    for (const s of timing.scenes) console.log(`  ${s.name.padEnd(12)} ${s.start.toFixed(1).padStart(5)}s → ${s.end.toFixed(1).padStart(5)}s`);
  } finally {
    await chrome.close();
  }
}

async function still(server) {
  const [sec, outPath] = rest;
  if (sec === undefined || !outPath) fail("usage: node render.mjs <film_dir> still <sec> <out.png>");
  const chrome = await launchChrome();
  try {
    await openFilm(chrome.send, `http://127.0.0.1:${server.address().port}/film.html?render`, 1);
    await evaluate(chrome.send, `__film.seek(${Number(sec)})`);
    writeFileSync(resolve(outPath), await shot(chrome.send, "png"));
  } finally {
    await chrome.close();
  }
}

const server = await serve({ allowSave: mode === "edit" });
if (mode === "edit" || mode === "preview") {
  console.log(`Open http://127.0.0.1:${server.address().port}/film.html${mode === "edit" ? "?edit" : ""}  (Ctrl+C to stop)`);
} else {
  try { mode === "still" ? await still(server) : await render(server); }
  finally { server.close(); }
}
