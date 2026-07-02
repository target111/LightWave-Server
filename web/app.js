/* LightWave control panel — talks to the FastAPI backend over REST and
   receives live pixel frames over /ws. No build step, no dependencies. */

"use strict";

const $ = (id) => document.getElementById(id);

const els = {
  linkStatus: $("link-status"),
  linkLabel: $("link-label"),
  strip: $("strip"),
  stripGlow: $("strip-glow"),
  stripMeta: $("strip-meta"),
  stripBrightness: $("strip-brightness"),
  stripFps: $("strip-fps"),
  nowPlaying: $("now-playing"),
  npName: $("np-name"),
  npElapsed: $("np-elapsed"),
  btnStop: $("btn-stop"),
  presetGrid: $("preset-grid"),
  presetCount: $("preset-count"),
  presetConfig: $("preset-config"),
  configTitle: $("config-title"),
  configDesc: $("config-desc"),
  configForm: $("config-form"),
  configClose: $("config-close"),
  btnStart: $("btn-start"),
  manualBody: $("manual-body"),
  manualLock: $("manual-lock"),
  colorInput: $("color-input"),
  colorHex: $("color-hex"),
  btnColor: $("btn-color"),
  swatches: $("swatches"),
  brightness: $("brightness"),
  brightnessVal: $("brightness-val"),
  btnClear: $("btn-clear"),
  toast: $("toast"),
};

const state = {
  running: null, // name of the running preset, or null
  runningStart: null, // ms timestamp used for the elapsed readout
  selected: null, // preset selected in the config panel
  schemas: new Map(), // preset name -> {description, args}
  ledCount: 0,
};

/* ---------- toast ---------- */

let toastTimer = null;
function toast(msg, isError = false) {
  els.toast.textContent = msg;
  els.toast.classList.toggle("error", isError);
  els.toast.hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => (els.toast.hidden = true), 3500);
}

/* ---------- REST helpers ---------- */

async function api(path, options = {}) {
  const res = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      if (body.detail) detail = body.detail;
    } catch (_) { /* not JSON */ }
    throw new Error(detail);
  }
  return res.status === 204 ? null : res.json();
}

/* ---------- live strip rendering ---------- */

const ctx = els.strip.getContext("2d");
const glowCtx = els.stripGlow.getContext("2d");
let offscreen = null;
let offscreenCtx = null;
let stripImage = null;
let frameCount = 0;

function renderStrip(pixels, brightness) {
  const n = pixels.length / 3;
  if (!n) return;

  if (state.ledCount !== n) {
    state.ledCount = n;
    els.stripMeta.textContent = `${n} LEDS`;
    offscreen = document.createElement("canvas");
    offscreen.width = n;
    offscreen.height = 1;
    offscreenCtx = offscreen.getContext("2d");
    stripImage = offscreenCtx.createImageData(n, 1);
  }

  const data = stripImage.data;
  for (let i = 0; i < n; i++) {
    data[i * 4] = pixels[i * 3] * brightness;
    data[i * 4 + 1] = pixels[i * 3 + 1] * brightness;
    data[i * 4 + 2] = pixels[i * 3 + 2] * brightness;
    data[i * 4 + 3] = 255;
  }
  offscreenCtx.putImageData(stripImage, 0, 0);

  for (const c of [ctx, glowCtx]) {
    c.clearRect(0, 0, c.canvas.width, c.canvas.height);
    c.drawImage(offscreen, 0, 0, c.canvas.width, c.canvas.height);
  }

  els.stripBrightness.textContent = `${Math.round(brightness * 100)}%`;
  frameCount++;
}

function sizeCanvases() {
  const rect = els.strip.parentElement.getBoundingClientRect();
  for (const canvas of [els.strip, els.stripGlow]) {
    canvas.width = Math.max(1, Math.round(rect.width));
    canvas.height = Math.max(1, Math.round(rect.height));
    // Resizing resets context state, so re-apply here, not per frame.
    canvas.getContext("2d").imageSmoothingEnabled = false;
  }
}
window.addEventListener("resize", sizeCanvases);

setInterval(() => {
  els.stripFps.textContent = `${frameCount} FPS`;
  frameCount = 0;
}, 1000);

/* ---------- websocket with auto-reconnect ---------- */

let reconnectDelay = 500;

function setLink(stateName, label) {
  els.linkStatus.dataset.state = stateName;
  els.linkLabel.textContent = label;
}

function connect() {
  const proto = location.protocol === "https:" ? "wss:" : "ws:";
  const ws = new WebSocket(`${proto}//${location.host}/ws`);
  ws.binaryType = "arraybuffer";

  ws.onopen = () => {
    reconnectDelay = 500;
    setLink("open", "LIVE");
  };

  // Binary messages are pixel frames (1 brightness byte + 3 bytes/LED);
  // text messages are JSON status events (running preset changed).
  ws.onmessage = (event) => {
    if (typeof event.data === "string") {
      const msg = JSON.parse(event.data);
      if (msg.type === "status" && msg.running !== state.running) {
        setRunning(msg.running);
      }
      return;
    }
    const data = new Uint8Array(event.data);
    renderStrip(data.subarray(1), data[0] / 255);
  };

  ws.onclose = () => {
    setLink("closed", "OFFLINE");
    setTimeout(() => {
      setLink("connecting", "LINKING…");
      connect();
    }, reconnectDelay);
    reconnectDelay = Math.min(reconnectDelay * 2, 5000);
  };

  ws.onerror = () => ws.close();
}

/* ---------- running preset state ---------- */

function setRunning(name) {
  state.running = name;
  els.nowPlaying.hidden = !name;
  els.btnStop.disabled = !name;
  els.manualLock.hidden = !name;
  els.manualBody.classList.toggle("locked", !!name);
  els.manualBody
    .querySelectorAll("input, button")
    .forEach((el) => (el.disabled = !!name));

  for (const tile of els.presetGrid.querySelectorAll(".preset-tile")) {
    const isRunning = tile.dataset.name === name;
    tile.classList.toggle("running", isRunning);
    tile.querySelector(".preset-tile-live").hidden = !isRunning;
  }

  if (name) {
    els.npName.textContent = name;
    state.runningStart = Date.now();
    // The websocket only says *what* runs; ask the API since when so the
    // elapsed readout survives page reloads.
    api("/presets/running")
      .then((info) => {
        state.runningStart = Date.now() - info.duration_seconds * 1000;
      })
      .catch(() => {});
  } else {
    state.runningStart = null;
  }
}

setInterval(() => {
  if (state.runningStart === null) return;
  const secs = Math.max(0, Math.floor((Date.now() - state.runningStart) / 1000));
  const m = String(Math.floor(secs / 60)).padStart(2, "0");
  const s = String(secs % 60).padStart(2, "0");
  els.npElapsed.textContent = `${m}:${s}`;
}, 1000);

els.btnStop.addEventListener("click", async () => {
  try {
    await api("/presets/stop", { method: "POST" });
  } catch (err) {
    toast(`Stop failed: ${err.message}`, true);
  }
});

/* ---------- presets ---------- */

async function loadPresets() {
  try {
    const data = await api("/presets");
    els.presetGrid.innerHTML = "";
    els.presetCount.textContent = `${data.presets.length}`;
    for (const preset of data.presets) {
      const tile = document.createElement("button");
      tile.type = "button";
      tile.className = "preset-tile";
      tile.dataset.name = preset.name;
      tile.innerHTML = `
        <span class="preset-tile-live" hidden>● LIVE</span>
        <span class="preset-tile-name"></span>
        <span class="preset-tile-desc"></span>`;
      tile.querySelector(".preset-tile-name").textContent = preset.name;
      tile.querySelector(".preset-tile-desc").textContent = preset.description;
      tile.addEventListener("click", () => selectPreset(preset.name));
      els.presetGrid.appendChild(tile);
    }
    if (state.running) setRunning(state.running); // re-mark the live tile
  } catch (err) {
    els.presetGrid.innerHTML =
      '<div class="empty-note">failed to load presets — is the server up?</div>';
  }
}

async function selectPreset(name) {
  if (state.selected === name) {
    closeConfig(); // clicking the selected preset again collapses it
    return;
  }
  state.selected = name;
  for (const tile of els.presetGrid.querySelectorAll(".preset-tile")) {
    tile.classList.toggle("selected", tile.dataset.name === name);
  }

  if (!state.schemas.has(name)) {
    try {
      state.schemas.set(name, await api(`/presets/${name}`));
    } catch (err) {
      toast(`Failed to load ${name}: ${err.message}`, true);
      return;
    }
  }
  const info = state.schemas.get(name);

  els.configTitle.textContent = name;
  els.configDesc.textContent = info.description;
  buildConfigForm(info.args);
  els.presetConfig.hidden = false;
  els.presetConfig.scrollIntoView({ behavior: "smooth", block: "nearest" });
}

function closeConfig() {
  els.presetConfig.hidden = true;
  state.selected = null;
  for (const tile of els.presetGrid.querySelectorAll(".preset-tile")) {
    tile.classList.remove("selected");
  }
}

els.configClose.addEventListener("click", closeConfig);

/* Build one control per option in the effect's schema. */
function buildConfigForm(args) {
  els.configForm.innerHTML = "";
  for (const opt of args) {
    const wrap = document.createElement("div");
    wrap.className = "opt";
    wrap.dataset.name = opt.name;
    wrap.dataset.type = opt.type;

    const head = document.createElement("div");
    head.className = "opt-head";
    const label = document.createElement("span");
    label.className = "opt-name";
    label.textContent = opt.name;
    const value = document.createElement("span");
    value.className = "opt-value";
    head.append(label, value);

    const desc = document.createElement("div");
    desc.className = "opt-desc";
    desc.textContent = opt.description;

    wrap.append(head, desc, buildOptionInput(opt, value));
    els.configForm.appendChild(wrap);
  }
}

function buildOptionInput(opt, valueEl) {
  if (opt.type === "bool") {
    const holder = document.createElement("label");
    holder.className = "toggle";
    const input = document.createElement("input");
    input.type = "checkbox";
    input.checked = !!opt.default;
    const track = document.createElement("span");
    track.className = "toggle-track";
    valueEl.textContent = input.checked ? "on" : "off";
    input.addEventListener("change", () => {
      valueEl.textContent = input.checked ? "on" : "off";
    });
    holder.append(input, track);
    return holder;
  }

  if (opt.type === "color") {
    const input = document.createElement("input");
    input.type = "color";
    input.value = rgbToHex(opt.default);
    valueEl.textContent = input.value;
    input.addEventListener("input", () => (valueEl.textContent = input.value));
    return input;
  }

  // int / float — slider when the range is bounded, number box otherwise
  const bounded = opt.min !== undefined && opt.max !== undefined;
  const input = document.createElement("input");
  input.type = bounded ? "range" : "number";
  if (opt.min !== undefined) input.min = opt.min;
  if (opt.max !== undefined) input.max = opt.max;
  input.step =
    opt.type === "int"
      ? 1
      : bounded
        ? Math.max((opt.max - opt.min) / 100, 0.01)
        : "any";
  input.value = opt.default;
  valueEl.textContent = formatNum(opt.default);
  input.addEventListener("input", () => {
    valueEl.textContent = formatNum(input.value);
  });
  return input;
}

function formatNum(v) {
  const n = Number(v);
  return Number.isInteger(n) ? String(n) : n.toFixed(2);
}

function collectArgs() {
  const args = {};
  for (const wrap of els.configForm.querySelectorAll(".opt")) {
    const type = wrap.dataset.type;
    const input = wrap.querySelector("input");
    if (type === "bool") args[wrap.dataset.name] = input.checked;
    else if (type === "color") args[wrap.dataset.name] = hexToRgb(input.value);
    else if (input.value !== "") args[wrap.dataset.name] = Number(input.value);
  }
  return args;
}

els.btnStart.addEventListener("click", async () => {
  if (!state.selected) return;
  els.btnStart.disabled = true;
  try {
    await api("/presets/start", {
      method: "POST",
      body: JSON.stringify({
        preset_name: state.selected,
        args: collectArgs(),
      }),
    });
    toast(`${state.selected} started`);
  } catch (err) {
    toast(`Start failed: ${err.message}`, true);
  } finally {
    els.btnStart.disabled = false;
  }
});

/* ---------- manual controls ---------- */

const SWATCHES = [
  "#ffffff", "#20d5ff", "#7e80ff", "#e928ff",
  "#ff2f6d", "#ff7a1a", "#ffd21e", "#3aff8f",
];

function hexToRgb(hex) {
  return [
    parseInt(hex.slice(1, 3), 16),
    parseInt(hex.slice(3, 5), 16),
    parseInt(hex.slice(5, 7), 16),
  ];
}

function rgbToHex(rgb) {
  if (!Array.isArray(rgb)) return "#000000";
  return "#" + rgb.map((c) => c.toString(16).padStart(2, "0")).join("");
}

for (const hex of SWATCHES) {
  const btn = document.createElement("button");
  btn.type = "button";
  btn.className = "swatch";
  btn.style.background = hex;
  btn.title = hex;
  btn.addEventListener("click", () => {
    els.colorInput.value = hex;
    els.colorHex.textContent = hex.toUpperCase();
    setColor(hex);
  });
  els.swatches.appendChild(btn);
}

els.colorInput.addEventListener("input", () => {
  els.colorHex.textContent = els.colorInput.value.toUpperCase();
});

async function setColor(hex) {
  try {
    await api("/leds/color/set", {
      method: "POST",
      body: JSON.stringify({ color: hex }),
    });
  } catch (err) {
    toast(`Color failed: ${err.message}`, true);
  }
}

els.btnColor.addEventListener("click", () => setColor(els.colorInput.value));

els.btnClear.addEventListener("click", async () => {
  try {
    await api("/leds/color/clear", { method: "POST" });
  } catch (err) {
    toast(`Clear failed: ${err.message}`, true);
  }
});

// Brightness: update the label live, but rate-limit the POSTs so dragging
// the slider doesn't flood the API.
let brightnessTimer = null;
els.brightness.addEventListener("input", () => {
  els.brightnessVal.textContent = `${els.brightness.value}%`;
  clearTimeout(brightnessTimer);
  brightnessTimer = setTimeout(async () => {
    try {
      await api("/leds/brightness", {
        method: "POST",
        body: JSON.stringify({ brightness: els.brightness.value / 100 }),
      });
    } catch (err) {
      toast(`Brightness failed: ${err.message}`, true);
    }
  }, 120);
});

/* ---------- boot ---------- */

sizeCanvases();
connect();
loadPresets();
