import { initSceneObjects } from "./floater_mvp_scene.js";
import { makeFloaterFromImage, stepPhysics } from "./floater_mvp_physics.js";
import { drawFrame } from "./floater_mvp_render.js";

const FOV_WIDTH_PCT = 84;
const FOV_HEIGHT_PCT = 84;

const canvas = document.getElementById("cv");
const ctx = canvas.getContext("2d");

const fileInput = document.getElementById("file");
const lagSlider = document.getElementById("lag");
const lagVal = document.getElementById("lagVal");
const fovShape = document.getElementById("fovShape");
const info = document.getElementById("info");

const state = {
  view: { offsetX: 0, offsetY: 0, zoom: 1 },
  rawViewVel: { x: 0, y: 0 },
  viewVel: { x: 0, y: 0 },
  prevViewVel: { x: 0, y: 0 },
  stationaryTime: 0,
  floaters: [],
  loadedImage: null,
  sceneObjects: initSceneObjects(),
};

let dragging = false;
let lastMouse = { x: 0, y: 0 };
let lastT = performance.now();

function updateLabels() {
  lagVal.textContent = `${lagSlider.value}%`;
}

function resizeCanvasToDevicePixels() {
  const dpr = window.devicePixelRatio || 1;
  canvas.width = Math.floor(canvas.clientWidth * dpr);
  canvas.height = Math.floor(canvas.clientHeight * dpr);
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
}

function resetViewToCenter() {
  state.view.offsetX = canvas.clientWidth / 2;
  state.view.offsetY = canvas.clientHeight / 2;
  state.view.zoom = 1;
}

function rebuildFloater() {
  if (!state.loadedImage) return;
  state.floaters = [makeFloaterFromImage(state.loadedImage)];
  state.stationaryTime = 0;
  state.rawViewVel.x = 0;
  state.rawViewVel.y = 0;
  state.viewVel.x = 0;
  state.viewVel.y = 0;
  state.prevViewVel.x = 0;
  state.prevViewVel.y = 0;
  resetViewToCenter();
  info.textContent = "Loaded: 1 entity (full image)";
}

function handleImageUpload(file) {
  if (!file) return;
  const url = URL.createObjectURL(file);
  const img = new Image();
  img.onload = () => {
    state.loadedImage = img;
    rebuildFloater();
    URL.revokeObjectURL(url);
  };
  img.src = url;
}

function installInputHandlers() {
  lagSlider.addEventListener("input", updateLabels);

  window.addEventListener("resize", resizeCanvasToDevicePixels);

  canvas.addEventListener("mousedown", (e) => {
    dragging = true;
    lastMouse = { x: e.clientX, y: e.clientY };
  });

  window.addEventListener("mouseup", () => {
    dragging = false;
  });

  window.addEventListener("mousemove", (e) => {
    if (!dragging) return;

    const dx = e.clientX - lastMouse.x;
    const dy = e.clientY - lastMouse.y;
    lastMouse = { x: e.clientX, y: e.clientY };

    state.view.offsetX += dx;
    state.view.offsetY += dy;
    state.rawViewVel.x = dx;
    state.rawViewVel.y = dy;
  });

  canvas.addEventListener(
    "wheel",
    (e) => {
      // Keep this prevented so the page does not scroll while dragging/testing.
      e.preventDefault();
    },
    { passive: false },
  );

  fileInput.addEventListener("change", (e) => {
    handleImageUpload(e.target.files?.[0]);
  });
}

function animationLoop(nowMs) {
  const dt = Math.min(0.03, (nowMs - lastT) / 1000);
  lastT = nowMs;

  stepPhysics(state, Number(lagSlider.value), dt, nowMs / 1000);
  drawFrame(ctx, canvas, state, {
    lagValue: Number(lagSlider.value),
    fovShape: fovShape.value,
    fovWidthPct: FOV_WIDTH_PCT,
    fovHeightPct: FOV_HEIGHT_PCT,
  });

  requestAnimationFrame(animationLoop);
}

function init() {
  updateLabels();
  resizeCanvasToDevicePixels();
  resetViewToCenter();
  installInputHandlers();
  requestAnimationFrame(animationLoop);
}

init();
