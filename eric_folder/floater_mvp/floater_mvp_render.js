// Rendering module for MVP scene + floater overlay.

export function getFovRect(w, h, shape, widthPct, heightPct) {
  const fw = w * (widthPct / 100);
  const fh = h * (heightPct / 100);
  return {
    shape,
    x: (w - fw) * 0.5,
    y: (h - fh) * 0.5,
    w: fw,
    h: fh,
    cx: w * 0.5,
    cy: h * 0.5,
    rx: fw * 0.5,
    ry: fh * 0.5,
  };
}

function drawBackground(ctx, w, h) {
  const g = ctx.createLinearGradient(0, 0, 0, h);
  g.addColorStop(0, "#b9e2ff");
  g.addColorStop(1, "#e8f4ff");
  ctx.fillStyle = g;
  ctx.fillRect(0, 0, w, h);
}

function drawWorldBackdrop(ctx) {
  const worldW = 5000;
  const skyTop = -2200;
  const horizonY = -30;
  const groundBottom = 2200;

  const sky = ctx.createLinearGradient(0, skyTop, 0, horizonY);
  sky.addColorStop(0, "#9bd4ff");
  sky.addColorStop(1, "#dff2ff");
  ctx.fillStyle = sky;
  ctx.fillRect(-worldW, skyTop, worldW * 2, horizonY - skyTop);

  const ground = ctx.createLinearGradient(0, horizonY, 0, groundBottom);
  ground.addColorStop(0, "#75b85d");
  ground.addColorStop(1, "#4f8f3f");
  ctx.fillStyle = ground;
  ctx.fillRect(-worldW, horizonY, worldW * 2, groundBottom - horizonY);

  ctx.strokeStyle = "rgba(62, 107, 52, 0.85)";
  ctx.lineWidth = 5;
  ctx.beginPath();
  ctx.moveTo(-worldW, horizonY);
  ctx.lineTo(worldW, horizonY);
  ctx.stroke();
}

function drawSceneObjects(ctx, sceneObjects, zoom) {
  for (const obj of sceneObjects) {
    const size = obj.size;
    ctx.lineWidth = 2 / Math.max(0.6, zoom);

    if (obj.type === "tree") {
      const trunkW = size * 0.22;
      const trunkH = size * 0.7;
      const baseY = obj.y + 10;
      ctx.fillStyle = "#5e4631";
      ctx.fillRect(obj.x - trunkW * 0.5, baseY - trunkH, trunkW, trunkH);

      ctx.fillStyle = "#2f7f43";
      ctx.strokeStyle = "#225f33";
      ctx.beginPath();
      ctx.arc(obj.x, baseY - trunkH, size * 0.55, 0, Math.PI * 2);
      ctx.fill();
      ctx.stroke();
    } else if (obj.type === "house") {
      const w = size * 0.95;
      const h = size * 0.65;
      const baseY = obj.y + 18;
      ctx.fillStyle = "#e2d8c8";
      ctx.strokeStyle = "#8f7a66";
      ctx.beginPath();
      ctx.rect(obj.x - w * 0.5, baseY - h, w, h);
      ctx.fill();
      ctx.stroke();

      ctx.fillStyle = "#af5c48";
      ctx.strokeStyle = "#7f3f31";
      ctx.beginPath();
      ctx.moveTo(obj.x - w * 0.58, baseY - h);
      ctx.lineTo(obj.x, baseY - h - size * 0.42);
      ctx.lineTo(obj.x + w * 0.58, baseY - h);
      ctx.closePath();
      ctx.fill();
      ctx.stroke();
    } else {
      const baseY = obj.y + 18;
      ctx.strokeStyle = "#5a6977";
      ctx.beginPath();
      ctx.moveTo(obj.x, baseY);
      ctx.lineTo(obj.x, baseY - size * 1.2);
      ctx.stroke();

      ctx.fillStyle = "#f0f3f6";
      ctx.strokeStyle = "#95a0ab";
      ctx.beginPath();
      ctx.rect(
        obj.x - size * 0.3,
        baseY - size * 1.08,
        size * 0.6,
        size * 0.16,
      );
      ctx.fill();
      ctx.stroke();
    }
  }
}

function clipToFov(ctx, fov) {
  ctx.save();
  if (fov.shape === "box") {
    ctx.beginPath();
    ctx.rect(fov.x, fov.y, fov.w, fov.h);
  } else {
    ctx.beginPath();
    ctx.ellipse(fov.cx, fov.cy, fov.rx, fov.ry, 0, 0, Math.PI * 2);
  }
  ctx.clip();
}

function drawFloatersRetinal(ctx, floaters, w, h) {
  const cx = w * 0.5;
  const cy = h * 0.5;
  ctx.globalCompositeOperation = "multiply";
  for (const f of floaters) {
    const sx = cx + f.base.x + f.offset.x;
    const sy = cy + f.base.y + f.offset.y;
    const x = sx - f.w / 2;
    const y = sy - f.h / 2;

    const a = 0.55 + 0.35 * (1 - f.depth);
    ctx.globalAlpha = a;
    ctx.drawImage(f.sprite, x, y);
  }
  ctx.globalAlpha = 1;
  ctx.globalCompositeOperation = "source-over";
}

function drawFovOverlay(ctx, fov, widthPct, heightPct) {
  ctx.save();
  ctx.strokeStyle = "rgba(255,255,255,0.9)";
  ctx.lineWidth = 2;
  ctx.setLineDash([8, 6]);

  if (fov.shape === "box") {
    ctx.strokeRect(fov.x, fov.y, fov.w, fov.h);
  } else {
    ctx.beginPath();
    ctx.ellipse(fov.cx, fov.cy, fov.rx, fov.ry, 0, 0, Math.PI * 2);
    ctx.stroke();
  }

  ctx.setLineDash([]);
  ctx.fillStyle = "rgba(0, 0, 0, 0.45)";
  ctx.fillRect(10, 78, 360, 28);
  ctx.fillStyle = "#fff";
  ctx.font = "14px system-ui, -apple-system, Segoe UI, Roboto, sans-serif";
  ctx.fillText(`FOV: ${fov.shape} ${widthPct}% x ${heightPct}%`, 18, 97);
  ctx.restore();
}

function drawHud(ctx, floatersCount, lagValue) {
  ctx.fillStyle = "rgba(0,0,0,0.6)";
  ctx.fillRect(10, 10, 360, 62);
  ctx.fillStyle = "#fff";
  ctx.font = "14px system-ui, -apple-system, Segoe UI, Roboto, sans-serif";
  ctx.fillText("Drag to pan (camera motion). Zoom disabled.", 18, 32);
  ctx.fillText(`Objects: ${floatersCount}   Lag: ${lagValue}%`, 18, 54);
}

export function drawFrame(ctx, canvas, state, ui) {
  const w = canvas.clientWidth;
  const h = canvas.clientHeight;
  ctx.clearRect(0, 0, w, h);
  drawBackground(ctx, w, h);

  const fov = getFovRect(w, h, ui.fovShape, ui.fovWidthPct, ui.fovHeightPct);

  clipToFov(ctx, fov);

  // World layer: camera-relative content.
  ctx.save();
  ctx.translate(state.view.offsetX, state.view.offsetY);
  ctx.scale(state.view.zoom, state.view.zoom);
  drawWorldBackdrop(ctx);
  drawSceneObjects(ctx, state.sceneObjects, state.view.zoom);
  ctx.restore();

  // Floater layer: retinal overlay, still clipped to FOV.
  drawFloatersRetinal(ctx, state.floaters, w, h);
  ctx.restore();

  drawFovOverlay(ctx, fov, ui.fovWidthPct, ui.fovHeightPct);
  drawHud(ctx, state.floaters.length, ui.lagValue);
}
