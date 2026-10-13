// Film runtime for motion-web-video. A film page calls film({ scenes }) once.
//
// Each scene is { name, duration, play(duration) } and has a <section data-scene="<name>"> on the page.
// play(duration) gets the final scene length (stretched to fit narration) and returns Motion sequence segments [target, keyframes, options]; options.at is seconds
// from the start of the scene. The runtime builds one paused Motion timeline from all scenes,
// so any time can be shown exactly: that is what makes a render repeat frame for frame.
//
// Page modes, from the query string:
//   ?render  no controls; the renderer calls window.__film.seek(t) for each frame
//   ?edit    controls plus a panel for the words and colours, saved back to film.json
//   (none)   a preview with play, pause and a scrubber
const { animate } = window.Motion;

const mode = new URLSearchParams(location.search).has("render") ? "render"
  : new URLSearchParams(location.search).has("edit") ? "edit" : "preview";

async function loadJson(name) {
  try {
    const res = await fetch(name, { cache: "no-store" });
    return res.ok ? await res.json() : {};
  } catch { return {}; }
}

// Narration starts this long into its scene, and the scene runs this long after it ends.
const VOICE_LEAD = 0.2, VOICE_TAIL = 0.4;

function applyLook(data) {
  for (const [k, v] of Object.entries(data.colors ?? {})) document.documentElement.style.setProperty(k, v);
  for (const el of document.querySelectorAll("[data-text]")) {
    const v = data.text?.[el.dataset.text];
    if (v != null) el.textContent = v;
  }
}

function fitStage(stage, w, h) {
  stage.style.width = `${w}px`;
  stage.style.height = `${h}px`;
  if (mode === "render") return;
  const fit = () => {
    const box = stage.parentElement.getBoundingClientRect();
    const s = Math.min(box.width / w, box.height / h);
    stage.style.transform = `translate(${(box.width - w * s) / 2}px, ${(box.height - h * s) / 2}px) scale(${s})`;
  };
  fit();
  addEventListener("resize", fit);
}

const nextFrame = () => new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)));

export function film(spec) {
  // The renderer reads __filmError, so a broken scene fails the render with its message.
  return buildFilm(spec).catch(err => { window.__filmError = err.message; console.error(err); });
}

async function buildFilm({ scenes, shape = "16:9", beforeSeek }) {
  const data = await loadJson("film.json");
  const voice = await loadJson("voice.json"); // written by scripts/voice.py; empty when there is no narration
  applyLook(data);
  const [w, h] = { "16:9": [1920, 1080], "1:1": [1080, 1080], "9:16": [1080, 1920] }[data.shape ?? shape];
  const stage = document.getElementById("stage");
  document.body.dataset.mode = mode;
  fitStage(stage, w, h);
  await document.fonts.ready;

  const times = [];
  const segments = [];
  let t = 0;
  for (const s of scenes) {
    const section = document.querySelector(`[data-scene="${s.name}"]`);
    if (!section) throw new Error(`no <section data-scene="${s.name}">`);
    // A scene is never shorter than its narration.
    const said = voice[s.name];
    const duration = said ? Math.max(s.duration, VOICE_LEAD + said.seconds + VOICE_TAIL) : s.duration;
    times.push({ name: s.name, start: t, end: t + duration, section,
      ...(said ? { voice: { file: said.file, at: t + VOICE_LEAD } } : {}) });
    for (const [target, keyframes, options = {}] of s.play(duration)) {
      segments.push([target, keyframes, { ...options, at: t + (options.at ?? 0) }]);
    }
    t += duration;
  }
  const total = t;
  // Before its first segment starts, an element would show its CSS value (a title at full
  // opacity before it fades in). Pin each property's first "from" value at time 0.
  const pinned = new Set();
  for (const [target, keyframes] of [...segments].sort((a, b) => a[2].at - b[2].at)) {
    for (const [prop, value] of Object.entries(keyframes)) {
      const key = `${typeof target === "string" ? target : target.id}|${prop}`;
      if (pinned.has(key) || !Array.isArray(value)) continue;
      pinned.add(key);
      segments.unshift([target, { [prop]: value[0] }, { duration: 0, at: 0 }]);
    }
  }
  // A zero-length hold at the end makes the timeline as long as the film.
  segments.push([stage, { opacity: 1 }, { duration: 0, at: total }]);
  const timeline = animate(segments);
  timeline.pause();

  let now = 0;
  function show(time) {
    now = Math.min(Math.max(time, 0), total);
    timeline.time = now;
    for (const s of times) s.section.hidden = !(now >= s.start && (now < s.end || (s === times.at(-1) && now <= total)));
    document.dispatchEvent(new CustomEvent("film:time", { detail: now }));
  }
  show(0);

  window.__film = {
    total,
    scenes: times.map(({ name, start, end, voice }) => ({ name, start, end, ...(voice ? { voice } : {}) })),
    // beforeSeek runs after the scene is shown, so a page can sync its visible media (video clips) before the frame is taken.
    async seek(time) { show(time); if (beforeSeek) await beforeSeek(time); await nextFrame(); return now; },
    ready: true,
  };
  if (mode !== "render") mountControls({ total, times, show, getNow: () => now, data });
}

function mountControls({ total, times, show, getNow, data }) {
  const bar = document.createElement("div");
  bar.id = "film-controls";
  bar.innerHTML = `
    <button type="button" id="film-play">Play</button>
    <input type="range" id="film-scrub" min="0" max="${total}" step="0.01" value="0" aria-label="Time">
    <output id="film-clock">0.00s</output>
    <div id="film-scenes">${times.map(s => `<button type="button" data-at="${Math.max(s.start, s.end - 0.05)}" title="Show the end of ${s.name}">${s.name}</button>`).join("")}</div>`;
  document.body.append(bar);
  const play = bar.querySelector("#film-play"), scrub = bar.querySelector("#film-scrub"), clock = bar.querySelector("#film-clock");
  let raf = 0, t0 = 0, from = 0;
  const stop = () => { cancelAnimationFrame(raf); raf = 0; play.textContent = "Play"; };
  const tick = ts => {
    const time = from + (ts - t0) / 1000;
    show(time);
    if (time >= total) return stop();
    raf = requestAnimationFrame(tick);
  };
  play.onclick = () => {
    if (raf) return stop();
    from = getNow() >= total ? 0 : getNow();
    t0 = performance.now();
    play.textContent = "Pause";
    raf = requestAnimationFrame(tick);
  };
  scrub.oninput = () => { stop(); show(Number(scrub.value)); };
  bar.querySelector("#film-scenes").onclick = e => {
    const b = e.target.closest("button"); if (!b) return;
    stop(); show(Number(b.dataset.at));
  };
  document.addEventListener("film:time", e => { scrub.value = e.detail; clock.textContent = `${e.detail.toFixed(2)}s`; });
  if (mode === "edit") mountEditor(bar, data, () => show(getNow()));
}

function mountEditor(bar, data, refresh) {
  const panel = document.createElement("form");
  panel.id = "film-editor";
  const texts = Object.entries(data.text ?? {});
  const colors = Object.entries(data.colors ?? {});
  panel.innerHTML = `
    <h2>Words</h2>
    ${texts.map(([k, v]) => `<label>${k}<input id="t-${k}" name="text.${k}" value="${String(v).replace(/"/g, "&quot;")}"></label>`).join("")}
    <h2>Colours</h2>
    ${colors.map(([k, v]) => `<label>${k}<input id="c-${k}" type="color" name="colors.${k}" value="${v}"></label>`).join("")}
    <button type="submit">Save to film.json</button>
    <p id="film-saved" role="status"></p>`;
  bar.after(panel);
  panel.oninput = e => {
    const [group, key] = e.target.name.split(".");
    data[group][key] = e.target.value;
    applyLook(data);
    refresh();
  };
  panel.onsubmit = async e => {
    e.preventDefault();
    const status = panel.querySelector("#film-saved");
    try {
      const res = await fetch("/save", { method: "POST", body: JSON.stringify(data, null, 2) });
      status.textContent = res.ok ? "Saved. Render again to update the MP4." : `Not saved: ${await res.text()}`;
    } catch (err) {
      status.textContent = `Not saved: ${err.message}. Is the edit server still running?`;
    }
  };
}
