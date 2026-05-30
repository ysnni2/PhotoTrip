/**
 * PhotoTrip — festival scene (carnival: stage, LED screen, ferris wheel, fireworks, crowd, food trucks).
 */
import * as THREE from "three";

const CONFETTI_COUNT = 160;
const LANTERN_COLORS = [0xff4fb8, 0xffdd44, 0xff7a45, 0x66e3ff, 0xb85cff];
const FIREWORK_COLORS = [0xffe04b, 0xff4fb8, 0x66e3ff, 0xff7a45, 0xb85cff];

/** @type {import("three").PerspectiveCamera | null} */
let activeCamera = null;
/** @type {import("three").Group | null} */
let contentRoot = null;
/** @type {import("three").Group | null} */
let stringGroup = null;
/** @type {import("three").Points | null} */
let confetti = null;
/** @type {{ speed: number; sway: number }[]} */
let confettiData = [];
/** @type {import("three").CanvasTexture | null} */
let bgTexture = null;
/** @type {{ points: import("three").Points; velocities: import("three").Vector3[]; life: number; age: number; }[]} */
let fireworks = [];

let spawnTimer = 0;
let animTime = 0;

/** @type {import("three").Group | null} */
let ferrisWheelGroup = null;
/** @type {import("three").Group[]} */
let staticFireworks = [];
/** @type {import("three").Group[]} */
let crowdPeople = [];
/** @type {import("three").Mesh[]} */
let lanternList = [];

// ─── material helpers ─────────────────────────────────────────────────────────
function basicMat(color) {
  return new THREE.MeshBasicMaterial({ color });
}
function lmat(color) {
  return new THREE.MeshLambertMaterial({ color });
}
function fmat(color) {
  return new THREE.MeshLambertMaterial({ color, flatShading: true });
}

// ─── gradient sky ─────────────────────────────────────────────────────────────
function createGradientBackground() {
  const canvas = document.createElement("canvas");
  canvas.width = 32;
  canvas.height = 512;
  const ctx = canvas.getContext("2d");
  const grad = ctx.createLinearGradient(0, 0, 0, 512);
  grad.addColorStop(0.0, "#0d011a");
  grad.addColorStop(0.3, "#2d0a5a");
  grad.addColorStop(0.65, "#7a1f9e");
  grad.addColorStop(1.0, "#ff77b7");
  ctx.fillStyle = grad;
  ctx.fillRect(0, 0, 32, 512);
  bgTexture = new THREE.CanvasTexture(canvas);
  bgTexture.colorSpace = THREE.SRGBColorSpace;
  return bgTexture;
}

// ─── particle fireworks (original system, kept intact) ────────────────────────
function createFirework(parent, x, y, z, color) {
  const count = 130;
  const positions = new Float32Array(count * 3);
  const velocities = [];
  for (let i = 0; i < count; i++) {
    positions[i * 3] = x; positions[i * 3 + 1] = y; positions[i * 3 + 2] = z;
    const theta = Math.random() * Math.PI * 2;
    const phi   = Math.random() * Math.PI;
    const speed = 0.03 + Math.random() * 0.08;
    velocities.push(new THREE.Vector3(
      Math.sin(phi) * Math.cos(theta) * speed,
      Math.cos(phi) * speed,
      Math.sin(phi) * Math.sin(theta) * speed
    ));
  }
  const geo = new THREE.BufferGeometry();
  geo.setAttribute("position", new THREE.BufferAttribute(positions, 3));
  const mat = new THREE.PointsMaterial({
    color, size: 0.08, transparent: true, opacity: 1,
    depthWrite: false, blending: THREE.AdditiveBlending,
  });
  const points = new THREE.Points(geo, mat);
  parent.add(points);
  fireworks.push({ points, velocities, life: 1, age: 0 });
}

function updateFireworks() {
  for (let f = fireworks.length - 1; f >= 0; f--) {
    const fw = fireworks[f];
    const pos = fw.points.geometry.attributes.position;
    fw.age += 0.015; fw.life -= 0.012;
    fw.points.material.opacity = Math.max(fw.life, 0);
    for (let i = 0; i < pos.count; i++) {
      pos.setX(i, pos.getX(i) + fw.velocities[i].x);
      pos.setY(i, pos.getY(i) + fw.velocities[i].y);
      pos.setZ(i, pos.getZ(i) + fw.velocities[i].z);
      fw.velocities[i].y -= 0.0006;
    }
    pos.needsUpdate = true;
    if (fw.life <= 0) {
      fw.points.removeFromParent();
      fw.points.geometry.dispose(); fw.points.material.dispose();
      fireworks.splice(f, 1);
    }
  }
}

function disposeFireworks() {
  fireworks.forEach(fw => { fw.points.geometry.dispose(); fw.points.material.dispose(); });
  fireworks = [];
}

// ─── confetti (original system, kept intact) ──────────────────────────────────
function buildConfetti(parent) {
  const geo = new THREE.BufferGeometry();
  const positions = new Float32Array(CONFETTI_COUNT * 3);
  const colors    = new Float32Array(CONFETTI_COUNT * 3);
  confettiData = [];
  for (let i = 0; i < CONFETTI_COUNT; i++) {
    positions[i * 3]     = (Math.random() - 0.5) * 18;
    positions[i * 3 + 1] = Math.random() * 7 + 1.5;
    positions[i * 3 + 2] = Math.random() * 7 - 1;
    const c = new THREE.Color(LANTERN_COLORS[i % LANTERN_COLORS.length]);
    colors[i * 3] = c.r; colors[i * 3 + 1] = c.g; colors[i * 3 + 2] = c.b;
    confettiData.push({ speed: 0.01 + Math.random() * 0.018, sway: Math.random() * Math.PI * 2 });
  }
  geo.setAttribute("position", new THREE.BufferAttribute(positions, 3));
  geo.setAttribute("color",    new THREE.BufferAttribute(colors, 3));
  confetti = new THREE.Points(geo, new THREE.PointsMaterial({
    size: 0.07, vertexColors: true, transparent: true, opacity: 0.9,
  }));
  parent.add(confetti);
}

// ─── stage + LED screen + spotlights ─────────────────────────────────────────
function buildStage(parent) {
  // Platform
  const platform = new THREE.Mesh(new THREE.BoxGeometry(7.2, 0.52, 1.85), lmat(0x10001e));
  platform.position.set(0, 0.26, -2.85);
  parent.add(platform);

  // Left / right truss poles
  [-3.25, 3.25].forEach(x => {
    const pole = new THREE.Mesh(new THREE.BoxGeometry(0.16, 4.0, 0.16), lmat(0x0a000f));
    pole.position.set(x, 2.2, -2.95);
    parent.add(pole);
  });

  // Top cross-bar
  const topBar = new THREE.Mesh(new THREE.BoxGeometry(7.4, 0.16, 0.16), lmat(0x0a000f));
  topBar.position.set(0, 4.25, -2.95);
  parent.add(topBar);

  // LED screen frame
  const frame = new THREE.Mesh(new THREE.BoxGeometry(4.8, 1.90, 0.10), lmat(0x040006));
  frame.position.set(0, 2.85, -2.98);
  parent.add(frame);

  // Screen base (dark background)
  const screenBg = new THREE.Mesh(new THREE.PlaneGeometry(4.4, 1.60), basicMat(0x0b0018));
  screenBg.position.set(0, 2.85, -2.92);
  parent.add(screenBg);

  // LED pixel blocks — deterministic positions (no Math.random so layout is stable)
  const ledColors = [0xff4fa3, 0x62f3ff, 0xb85cff, 0xfff46b, 0xff6c20];
  const ledMats   = ledColors.map(c => basicMat(c));
  for (let i = 0; i < 32; i++) {
    const pw = 0.14 + (i * 7919 % 100) / 350;
    const ph = 0.06 + (i * 6271 % 100) / 550;
    const block = new THREE.Mesh(new THREE.PlaneGeometry(pw, ph), ledMats[i % ledMats.length]);
    block.position.set(
      -1.95 + (i * 3533 % 1000) / 248,
      2.15 + (i * 2617 % 1000) / 588,
      -2.91
    );
    parent.add(block);
  }

  // Spotlight beams (ConeGeometry, transparent) — 4 beams from top bar
  const beamColors = [0xff4fa3, 0x62f3ff, 0xfff46b, 0xb85cff];
  beamColors.forEach((col, i) => {
    const beamMat = new THREE.MeshBasicMaterial({
      color: col, transparent: true, opacity: 0.14, depthWrite: false, side: THREE.DoubleSide,
    });
    const beam = new THREE.Mesh(new THREE.ConeGeometry(0.70, 6.0, 20, 1, true), beamMat);
    beam.position.set(-1.8 + i * 1.2, 4.0, -2.8);
    beam.rotation.x = Math.PI * 0.60;
    beam.rotation.z = (i - 1.5) * 0.20;
    parent.add(beam);

    const bulb = new THREE.Mesh(new THREE.SphereGeometry(0.08, 8, 8), basicMat(col));
    bulb.position.set(-1.8 + i * 1.2, 4.1, -2.8);
    parent.add(bulb);

    const pl = new THREE.PointLight(col, 0.8, 7);
    pl.position.copy(bulb.position);
    parent.add(pl);
  });

  // Stage bulbs on top bar
  for (let i = -2; i <= 2; i++) {
    const col  = i % 2 === 0 ? 0xffdd44 : 0xff4fb8;
    const bulb = new THREE.Mesh(new THREE.SphereGeometry(0.10, 10, 10), basicMat(col));
    bulb.position.set(i * 1.3, 4.05, -2.6);
    parent.add(bulb);
    const pl = new THREE.PointLight(col, 1.0, 8);
    pl.position.copy(bulb.position);
    parent.add(pl);
  }

  // Speaker stacks
  [-3.05, 3.05].forEach(x => {
    const spk = new THREE.Mesh(new THREE.BoxGeometry(0.50, 1.25, 0.50), lmat(0x040006));
    spk.position.set(x, 0.88, -2.3);
    parent.add(spk);
    [0.72, 1.10].forEach(sy => {
      const cone = new THREE.Mesh(new THREE.CylinderGeometry(0.13, 0.13, 0.04, 12), lmat(0x1a1a2e));
      cone.rotation.x = Math.PI / 2;
      cone.position.set(x, sy, -2.04);
      parent.add(cone);
    });
  });
}

// ─── ferris wheel ─────────────────────────────────────────────────────────────
function buildFerrisWheel(parent) {
  const outerGroup = new THREE.Group();

  // spinGroup is centered at the wheel hub — everything inside it rotates together
  const spinGroup = new THREE.Group();
  spinGroup.position.set(0, 2.1, 0);
  outerGroup.add(spinGroup);

  const rimMat = lmat(0xffd166);

  // Torus rim
  spinGroup.add(new THREE.Mesh(new THREE.TorusGeometry(1.85, 0.055, 8, 48), rimMat));

  // 4 full-diameter spokes (each spans the full width, giving an 8-arm star look)
  for (let i = 0; i < 4; i++) {
    const spoke = new THREE.Mesh(new THREE.BoxGeometry(0.045, 3.70, 0.045), rimMat);
    spoke.rotation.z = (Math.PI / 4) * i;
    spinGroup.add(spoke);
  }

  // 8 cabins on rim
  const cabinColors = [0xff4fa3, 0x62f3ff, 0xfff46b, 0xb85cff];
  for (let i = 0; i < 8; i++) {
    const angle = (Math.PI * 2 * i) / 8;
    const cabin = new THREE.Mesh(
      new THREE.BoxGeometry(0.30, 0.22, 0.22),
      basicMat(cabinColors[i % cabinColors.length])
    );
    cabin.position.set(Math.cos(angle) * 1.85, Math.sin(angle) * 1.85, 0);
    spinGroup.add(cabin);
  }

  // Support legs (static, not in spinGroup)
  const legMat = lmat(0x180d2e);
  [-0.72, 0.72].forEach((lx, idx) => {
    const leg = new THREE.Mesh(new THREE.BoxGeometry(0.09, 2.5, 0.09), legMat);
    leg.position.set(lx, 0.85, 0);
    leg.rotation.z = idx === 0 ? -0.30 : 0.30;
    outerGroup.add(leg);
  });
  const base = new THREE.Mesh(new THREE.BoxGeometry(2.0, 0.16, 0.38), legMat);
  base.position.set(0, -0.10, 0);
  outerGroup.add(base);

  outerGroup.position.set(-6.8, 0.18, -5.0);
  outerGroup.scale.setScalar(0.88);
  parent.add(outerGroup);

  ferrisWheelGroup = spinGroup;
}

// ─── static radial fireworks (pulsing accent) ─────────────────────────────────
function buildStaticFirework(parent, x, y, z, color) {
  const g = new THREE.Group();
  const mat = new THREE.MeshBasicMaterial({ color, transparent: true, opacity: 0.92 });

  g.add(new THREE.Mesh(new THREE.SphereGeometry(0.055, 8, 8), mat));

  const count = 16;
  for (let i = 0; i < count; i++) {
    const angle  = (Math.PI * 2 * i) / count;
    const radius = 0.36 + (i * 2017 % 100) / 230;
    const p = new THREE.Mesh(new THREE.SphereGeometry(0.038, 8, 8), mat);
    p.position.set(Math.cos(angle) * radius, Math.sin(angle) * radius, 0);
    g.add(p);
    const trail = new THREE.Mesh(new THREE.BoxGeometry(0.022, radius * 0.52, 0.022), mat);
    trail.position.set(Math.cos(angle) * radius * 0.47, Math.sin(angle) * radius * 0.47, 0);
    trail.rotation.z = angle - Math.PI / 2;
    g.add(trail);
  }

  g.position.set(x, y, z);
  g.userData = {
    baseScale: 0.82 + Math.abs(x * 100 % 40) / 100,
    phase: (x + y) * 1.3,
  };
  parent.add(g);
  staticFireworks.push(g);
}

// ─── food trucks ──────────────────────────────────────────────────────────────
function buildFoodTruck(parent, x, z, color) {
  const g = new THREE.Group();

  const body = new THREE.Mesh(new THREE.BoxGeometry(1.75, 0.80, 0.80), lmat(color));
  body.position.set(0, 0.56, 0); g.add(body);

  const roof = new THREE.Mesh(new THREE.BoxGeometry(1.90, 0.13, 0.90), lmat(0x0a0010));
  roof.position.set(0, 1.02, 0); g.add(roof);

  // Service window (cyan glow)
  const win = new THREE.Mesh(new THREE.PlaneGeometry(0.50, 0.32), basicMat(0x5ee8ff));
  win.position.set(-0.38, 0.66, -0.41); g.add(win);

  // Sign panel (yellow)
  const sign = new THREE.Mesh(new THREE.PlaneGeometry(0.68, 0.24), basicMat(0xfff46b));
  sign.position.set(0.46, 0.89, -0.41); g.add(sign);

  // Decorative dots on sign
  [0xff4fa3, 0x62f3ff].forEach((c, ci) => {
    const dot = new THREE.Mesh(new THREE.SphereGeometry(0.055, 6, 4), basicMat(c));
    dot.position.set(0.24 + ci * 0.28, 0.89, -0.40); g.add(dot);
  });

  // Wheels
  [-0.60, 0.60].forEach(wx => {
    const wh = new THREE.Mesh(new THREE.CylinderGeometry(0.17, 0.17, 0.10, 14), lmat(0x080808));
    wh.rotation.z = Math.PI / 2; wh.position.set(wx, 0.19, -0.45); g.add(wh);
  });

  // Awning overhang
  const awn = new THREE.Mesh(new THREE.BoxGeometry(1.75, 0.09, 0.55), lmat(color));
  awn.position.set(0, 1.11, -0.65); g.add(awn);

  // Small point light to simulate glow
  const pl = new THREE.PointLight(color, 0.6, 4);
  pl.position.set(0, 1.5, -0.4); g.add(pl);

  g.position.set(x, 0, z);
  g.rotation.y = x < 0 ? -0.28 : 0.28;
  parent.add(g);
}

// ─── lantern strings ──────────────────────────────────────────────────────────
function buildLanternString(parent, y, z, colorOffset) {
  const colors = [0xfff46b, 0xff4fa3, 0x62f3ff, 0xb85cff, 0xff9f43];
  const count  = 16;

  // Wire
  const wire = new THREE.Mesh(new THREE.BoxGeometry(13.5, 0.024, 0.024), lmat(0x1a032a));
  wire.position.set(0, y, z); parent.add(wire);

  for (let i = 0; i < count; i++) {
    const col     = colors[(i + colorOffset) % colors.length];
    const lantern = new THREE.Mesh(new THREE.SphereGeometry(0.13, 10, 10), basicMat(col));
    lantern.scale.y = 1.30;
    lantern.position.set(-5.9 + i * 0.80, y - 0.11 - Math.sin(i * 0.65) * 0.07, z);
    parent.add(lantern);
    lanternList.push(lantern);

    const pl = new THREE.PointLight(col, 0.38, 3.5);
    pl.position.copy(lantern.position); parent.add(pl);
  }
}

// ─── crowd ────────────────────────────────────────────────────────────────────
function buildCrowd(parent) {
  const bodyMat = basicMat(0x06000b);
  for (let i = 0; i < 90; i++) {
    const person = new THREE.Group();
    const h = 0.30 + Math.random() * 0.28;

    const body = new THREE.Mesh(new THREE.CylinderGeometry(0.07, 0.10, h, 8), bodyMat);
    body.position.y = h * 0.5; person.add(body);

    const head = new THREE.Mesh(new THREE.SphereGeometry(0.09, 8, 8), bodyMat);
    head.position.y = h + 0.09; person.add(head);

    // Raised arm (~35% of crowd)
    if (Math.random() > 0.65) {
      const arm = new THREE.Mesh(new THREE.BoxGeometry(0.04, 0.27, 0.04), bodyMat);
      arm.position.set(0.12, h + 0.04, 0);
      arm.rotation.z = -0.55;
      person.add(arm);
    }

    const row    = Math.random();
    const spreadX = 1.8 + row * 5.2;
    person.position.set(
      (Math.random() - 0.5) * spreadX,
      0.02,
      -0.5 + row * 3.8
    );
    person.rotation.y = (Math.random() - 0.5) * 0.5;
    person.scale.setScalar(0.82 + Math.random() * 0.46);
    parent.add(person);
    crowdPeople.push(person);
  }
}

// ─── ground (festival plaza) ──────────────────────────────────────────────────
function buildGround(parent) {
  const ground = new THREE.Mesh(new THREE.PlaneGeometry(60, 30), lmat(0x190c35));
  ground.rotation.x = -Math.PI / 2; ground.position.set(0, -0.01, 0);
  parent.add(ground);

  // Subtle lighter strips for plaza feel
  for (let i = 0; i < 8; i++) {
    const strip = new THREE.Mesh(
      new THREE.PlaneGeometry(60, 0.045),
      new THREE.MeshBasicMaterial({ color: i % 2 === 0 ? 0x2c1256 : 0x190c35, transparent: true, opacity: 0.38 })
    );
    strip.rotation.x = -Math.PI / 2;
    strip.position.set(0, 0.003, -4.2 + i * 1.3);
    parent.add(strip);
  }
}

// ─── public API ───────────────────────────────────────────────────────────────
/**
 * @param {{
 *   scene: import("three").Scene,
 *   contentGroup: import("three").Group,
 *   randomRange?: (min: number, max: number) => number,
 *   camera?: import("three").PerspectiveCamera,
 * }} ctx
 */
function init(ctx) {
  dispose();

  const { scene, contentGroup } = ctx;
  activeCamera  = ctx.camera ?? null;
  contentRoot   = contentGroup;

  scene.background = createGradientBackground();

  // Reset new tracking vars
  ferrisWheelGroup = null;
  staticFireworks  = [];
  crowdPeople      = [];
  lanternList      = [];

  // Lighting
  contentGroup.add(new THREE.AmbientLight(0xffd1f0, 2.5));
  const frontLight = new THREE.PointLight(0xff5db1, 8, 35);
  frontLight.position.set(0, 5, 6);
  contentGroup.add(frontLight);
  const warmLight = new THREE.PointLight(0xffd36e, 5, 30);
  warmLight.position.set(-5, 4, 4);
  contentGroup.add(warmLight);
  const fillLight = new THREE.PointLight(0xffffff, 3, 25);
  fillLight.position.set(5, 3, 5);
  contentGroup.add(fillLight);

  // Scene objects
  buildGround(contentGroup);
  buildStage(contentGroup);
  buildFerrisWheel(contentGroup);
  buildFoodTruck(contentGroup, -7.2, -1.6, 0xcc3868);
  buildFoodTruck(contentGroup,  7.2, -1.4, 0x1e78c2);

  // Lantern strings (3 rows at different heights / depths)
  stringGroup = new THREE.Group();
  buildLanternString(stringGroup, 5.7, -2.0, 0);
  buildLanternString(stringGroup, 5.0, -3.6, 2);
  buildLanternString(stringGroup, 5.3, -5.2, 4);
  contentGroup.add(stringGroup);

  // Static radial firework decorations (sky background)
  buildStaticFirework(contentGroup, -4.5, 6.0, -7.2, 0xfff46b);
  buildStaticFirework(contentGroup,  0.6, 6.6, -7.8, 0xff4fa3);
  buildStaticFirework(contentGroup,  4.6, 5.6, -7.4, 0x62f3ff);
  buildStaticFirework(contentGroup, -1.5, 5.1, -6.9, 0xb85cff);

  // Initial particle firework bursts
  createFirework(contentGroup, -3,   5.8, -5,   0xff4fb8);
  createFirework(contentGroup,  2.5, 6.5, -6,   0xffe04b);
  createFirework(contentGroup,  0,   4.9, -4.5, 0x66e3ff);

  buildCrowd(contentGroup);
  buildConfetti(contentGroup);

  spawnTimer = 0;
  animTime   = 0;

  if (activeCamera) {
    activeCamera.position.set(0, 3.8, 12);
    activeCamera.fov = 55;
    activeCamera.lookAt(0, 2.5, -2);
    activeCamera.updateProjectionMatrix();
  }
}

/**
 * @param {number} t — elapsed seconds
 * @param {number} [delta] — frame delta seconds
 */
function animate(t, delta = 0.016) {
  animTime    = t;
  spawnTimer += delta;

  // Periodic particle firework spawning
  if (spawnTimer > 1.1) {
    spawnTimer = 0;
    const color = FIREWORK_COLORS[Math.floor(Math.random() * FIREWORK_COLORS.length)];
    if (contentRoot) {
      createFirework(
        contentRoot,
        (Math.random() - 0.5) * 7,
        4.5 + Math.random() * 2.8,
        -5 - Math.random() * 3,
        color
      );
    }
  }

  updateFireworks();

  // Ferris wheel rotation
  if (ferrisWheelGroup) {
    ferrisWheelGroup.rotation.z += delta * 0.30;
  }

  // Static radial firework pulse (scale + opacity)
  staticFireworks.forEach((fw, idx) => {
    const s = fw.userData.baseScale + Math.sin(t * 2.2 + fw.userData.phase) * 0.13;
    fw.scale.setScalar(s);
    fw.children.forEach(child => {
      if (child.material && child.material.opacity !== undefined) {
        child.material.opacity = 0.62 + Math.sin(t * 2.5 + idx) * 0.28;
      }
    });
  });

  // Confetti fall
  if (confetti) {
    const pos = confetti.geometry.attributes.position;
    for (let i = 0; i < CONFETTI_COUNT; i++) {
      let y = pos.getY(i) - confettiData[i].speed;
      let x = pos.getX(i) + Math.sin(animTime * 2 + confettiData[i].sway) * 0.006;
      if (y < -0.1) { y = 8; x = (Math.random() - 0.5) * 18; }
      pos.setX(i, x); pos.setY(i, y);
    }
    pos.needsUpdate = true;
  }

  // Lantern gentle sway
  lanternList.forEach((lantern, i) => {
    lantern.position.y += Math.sin(t * 2.0 + i * 0.40) * 0.0007;
  });

  // Crowd bob
  crowdPeople.forEach((p, i) => {
    p.position.y = 0.02 + Math.sin(t * 3.0 + i * 0.55) * 0.012;
  });

  // Camera gentle sway
  if (activeCamera) {
    activeCamera.position.x = Math.sin(t * 0.25) * 0.38;
    activeCamera.position.y = 3.8 + Math.sin(t * 0.18) * 0.06;
    activeCamera.position.z = 12;
    activeCamera.lookAt(0, 2.5, -2);
  }
}

function dispose() {
  disposeFireworks();

  if (confetti) {
    confetti.geometry.dispose(); confetti.material.dispose(); confetti = null;
  }
  if (bgTexture) { bgTexture.dispose(); bgTexture = null; }

  stringGroup      = null;
  contentRoot      = null;
  confettiData     = [];
  activeCamera     = null;
  ferrisWheelGroup = null;
  staticFireworks  = [];
  crowdPeople      = [];
  lanternList      = [];
  spawnTimer       = 0;
  animTime         = 0;
}

export default { init, animate, dispose };
