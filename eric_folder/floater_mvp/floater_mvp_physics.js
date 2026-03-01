/*
Physics model for floater retinal motion.

State assumptions:
- Each floater is rendered in retinal/screen coordinates.
- `base` is the baseline position in screen space.
- Dynamics are applied to displacement `offset` from baseline and velocity `vel`.

Per-axis equations (x and y independently):
- offset' = vel
- vel' = a_input + a_core + a_return

Where:
- a_input  = driveInput * parallax * gazeCoupling * kick * lagScale
- a_core   = -spring*(offset - micro) - damping*vel
- a_return = -returnSpring*e*(offset - micro)*returnScale
             -returnDamping*e*vel*returnScale

Input assumptions:
- raw view velocity (`rawViewVel`) comes from pointer movement events.
- smoothed velocity is dt-correct low-pass filtered:
  viewVel += (1 - exp(-dt/tau)) * (rawViewVel - viewVel)
- view acceleration is finite difference on smoothed velocity:
  viewAcc = (viewVel - prevViewVel) / dt
- driveInput blends velocity and acceleration:
  driveInput = velBlend*viewVel + accBlend*(accScale*viewAcc)
- very small driveInput is suppressed with a radial deadzone threshold
  so micro camera jitter does not move the floater.

`micro` is a tiny sinusoidal drift to avoid perfectly uniform motion.
`e` is return ease in [0,1], ramped by smoothstep after gaze becomes stationary.

Integration:
- Semi-implicit Euler:
  vel += vel' * dt
  offset += vel * dt
*/

export const PHYSICS_CONSTANTS = {
  BASE_PARALLAX: 1.0,
  GAZE_COUPLING: 20,
};

export function makeFloaterFromImage(img, rng = Math.random) {
  const sprite = document.createElement("canvas");
  sprite.width = img.width;
  sprite.height = img.height;
  const sctx = sprite.getContext("2d");
  sctx.clearRect(0, 0, img.width, img.height);
  sctx.drawImage(img, 0, 0);

  const depth = rng();
  const parAmount = PHYSICS_CONSTANTS.BASE_PARALLAX;
  const parallax = (0.35 + 1.15 * (1 - depth)) * (0.75 + 0.5 * parAmount);

  return {
    id: "f0",
    sprite,
    w: img.width,
    h: img.height,
    base: { x: 0, y: 0 },
    offset: { x: 0, y: 0 },
    vel: { x: 0, y: 0 },
    depth,
    parallax,
    lagScale: 0.85 + rng() * 0.35,
    returnScale: 0.82 + rng() * 0.36,
    microAmp: 0.02 + rng() * 0.06,
    microFreqX: 0.5 + rng() * 1.1,
    microFreqY: 0.5 + rng() * 1.1,
    microPhase: rng() * Math.PI * 2,
  };
}

export function getLagModel(lagPercent) {
  const t = (Number(lagPercent) / 100) * 0.5;
  return {
    spring: 13 - 7 * t,
    damping: 6 - 3.5 * t,
    kick: 24 + 20 * t,
    settleDelay: 0.02 + 0.05 * t,
    returnRamp: 0.18 + 0.16 * t,
    returnSpring: 20 + 16 * t,
    returnDamping: 10 + 8 * t,

    // Input model parameters
    velBlend: 0.35,
    accBlend: 0.65,
    accScale: 0.015,
    inputTau: 0.06,
    inputDeadzone: 1.25,
  };
}

function smoothViewVelocity(state, dt, tau) {
  const a = 1 - Math.exp(-dt / Math.max(1e-4, tau));
  state.viewVel.x += a * (state.rawViewVel.x - state.viewVel.x);
  state.viewVel.y += a * (state.rawViewVel.y - state.viewVel.y);

  // Event-driven velocity: consume once per frame to avoid stale forcing.
  state.rawViewVel.x = 0;
  state.rawViewVel.y = 0;
}

function computeViewAcceleration(state, dt) {
  const invDt = 1 / Math.max(1e-4, dt);
  const acc = {
    x: (state.viewVel.x - state.prevViewVel.x) * invDt,
    y: (state.viewVel.y - state.prevViewVel.y) * invDt,
  };
  state.prevViewVel.x = state.viewVel.x;
  state.prevViewVel.y = state.viewVel.y;
  return acc;
}

function computeReturnEase(state, dt, settleThreshold, settleDelay, returnRamp) {
  const inputMag = Math.hypot(state.viewVel.x, state.viewVel.y);
  if (inputMag < settleThreshold) {
    state.stationaryTime += dt;
  } else {
    state.stationaryTime = 0;
  }

  const stationaryOver = Math.max(0, state.stationaryTime - settleDelay);
  const returnBlend = Math.min(1, stationaryOver / returnRamp);
  const returnEase = returnBlend * returnBlend * (3 - 2 * returnBlend);

  // Smoothly fade input as return ramps in, avoiding hard discontinuity.
  state.viewVel.x *= 1 - returnEase;
  state.viewVel.y *= 1 - returnEase;

  return returnEase;
}

function getClampedInput(v, maxInput) {
  return {
    vx: Math.max(-maxInput, Math.min(maxInput, v.x)),
    vy: Math.max(-maxInput, Math.min(maxInput, v.y)),
  };
}

function blendDriveInput(velInput, accInput, lag) {
  return {
    vx: lag.velBlend * velInput.vx + lag.accBlend * (accInput.vx * lag.accScale),
    vy: lag.velBlend * velInput.vy + lag.accBlend * (accInput.vy * lag.accScale),
  };
}

function applyInputDeadzone(input, threshold) {
  const mag = Math.hypot(input.vx, input.vy);
  if (mag <= threshold) {
    return { vx: 0, vy: 0 };
  }
  // Radial deadzone: preserve direction and smooth onset above threshold.
  const scaledMag = (mag - threshold) / Math.max(1e-4, mag);
  return {
    vx: input.vx * scaledMag,
    vy: input.vy * scaledMag,
  };
}

function getMicroMotion(floater, tSec) {
  return {
    microX:
      Math.sin(tSec * floater.microFreqX + floater.microPhase) * floater.microAmp,
    microY:
      Math.cos(tSec * floater.microFreqY + floater.microPhase * 1.7) *
      floater.microAmp,
  };
}

function computeFloaterAcceleration(floater, lag, input, returnEase, micro) {
  const axInput =
    input.vx *
    floater.parallax *
    PHYSICS_CONSTANTS.GAZE_COUPLING *
    lag.kick *
    floater.lagScale;
  const ayInput =
    input.vy *
    floater.parallax *
    PHYSICS_CONSTANTS.GAZE_COUPLING *
    lag.kick *
    floater.lagScale;

  const axReturn =
    -lag.returnSpring *
      returnEase *
      (floater.offset.x - micro.microX) *
      floater.returnScale -
    lag.returnDamping * returnEase * floater.vel.x * floater.returnScale;
  const ayReturn =
    -lag.returnSpring *
      returnEase *
      (floater.offset.y - micro.microY) *
      floater.returnScale -
    lag.returnDamping * returnEase * floater.vel.y * floater.returnScale;

  const ax =
    axInput -
    lag.spring * (floater.offset.x - micro.microX) -
    lag.damping * floater.vel.x +
    axReturn;
  const ay =
    ayInput -
    lag.spring * (floater.offset.y - micro.microY) -
    lag.damping * floater.vel.y +
    ayReturn;

  return { ax, ay };
}

function integrateFloater(floater, accel, dt) {
  floater.vel.x += accel.ax * dt;
  floater.vel.y += accel.ay * dt;
  floater.offset.x += floater.vel.x * dt;
  floater.offset.y += floater.vel.y * dt;
}

export function stepPhysics(state, lagPercent, dt, nowSec) {
  const lag = getLagModel(lagPercent);

  smoothViewVelocity(state, dt, lag.inputTau);
  const viewAcc = computeViewAcceleration(state, dt);

  const settleThreshold = 0.6;
  const returnEase = computeReturnEase(
    state,
    dt,
    settleThreshold,
    lag.settleDelay,
    lag.returnRamp,
  );

  const velInput = getClampedInput(state.viewVel, 120);
  const accInput = getClampedInput(viewAcc, 800);
  const blendedInput = blendDriveInput(velInput, accInput, lag);
  const input = applyInputDeadzone(blendedInput, lag.inputDeadzone);

  for (const floater of state.floaters) {
    const micro = getMicroMotion(floater, nowSec);
    const accel = computeFloaterAcceleration(
      floater,
      lag,
      input,
      returnEase,
      micro,
    );
    integrateFloater(floater, accel, dt);
  }
}
