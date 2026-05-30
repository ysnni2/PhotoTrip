/**
 * PhotoTrip — category mini-worlds (Three.js, no external models).
 */
import * as THREE from "https://esm.sh/three@0.160.0";

const VALID_CATEGORIES = new Set([
  "nature",
  "beach",
  "city",
  "culture",
  "food",
  "festival",
]);

const ORBIT_RADIUS = 22;
const ORBIT_HEIGHT = 14;
const ORBIT_SPEED = 0.35;

/** @type {Record<string, { radius?: number, height?: number, speed?: number, lookAtY?: number }>} */
const ORBIT_BY_CATEGORY = {
  nature:    { mode: 'sway', height: 2.2, z: 10,  swayX: 0.35, swaySpeed: 0.18, lookAtY: 1.5,  lookAtZ: 0  },
  beach:     { mode: 'sway', height: 2.8, z: 9,   swayX: 0.22, swaySpeed: 0.14, lookAtY: 1.5,  lookAtZ: -3 },
  food:      { mode: 'sway', height: 2.5, z: 8,   swayX: 0.25, swaySpeed: 0.18, lookAtY: 1.8,  lookAtZ: 0  },
  culture:   { mode: 'sway', height: 1.85, z: 9.5, swayX: 0.40, swaySpeed: 0.22, lookAtY: 1.6, lookAtZ: 0  },
  festival:  { mode: 'sway', height: 3.2, z: 12,  swayX: 0.35, swaySpeed: 0.25, lookAtY: 2.5,  lookAtZ: -3 },
  cityDay:   { mode: 'sway', height: 3.0, z: 14,  swayX: 0.30, swaySpeed: 0.15, lookAtY: 2.0,  lookAtZ: -2 },
  cityNight: { mode: 'sway', height: 3.0, z: 14,  swayX: 0.30, swaySpeed: 0.15, lookAtY: 2.0,  lookAtZ: -2 },
};

/** @type {THREE.WebGLRenderer | null} */
let renderer = null;
/** @type {THREE.Scene | null} */
let scene = null;
/** @type {THREE.PerspectiveCamera | null} */
let camera = null;
/** @type {HTMLCanvasElement | null} */
let canvas = null;
/** @type {THREE.Group | null} */
let contentGroup = null;
/** @type {number | null} */
let animationId = null;
let orbitAngle = 0;
let lastFrameTime = 0;
let currentCategory = null;
/** @type {'day' | 'night'} */
let citySceneMode = "day";

/** @type {THREE.Points | null} */
let fireworksPoints = null;
/** @type {Float32Array | null} */
let fireworksVelocities = null;
/** @type {THREE.Mesh[]} */
let lanternMeshes = [];
/** @type {THREE.Mesh[]} */
let beachWaves = [];
/** @type {THREE.Mesh | null} */
let beachOceanMesh = null;
/** @type {THREE.Points | null} */
let natureParticles = null;
/** @type {{ mesh: THREE.Group, dir: number, speed: number }[]} */
let cityCars = [];
/** @type {THREE.CanvasTexture | null} */
let bgTexture = null;

function normalizeCategory(input) {
  if (typeof input === "string") {
    const key = input.toLowerCase().trim();
    return VALID_CATEGORIES.has(key) ? key : "nature";
  }
  if (input && typeof input === "object") {
    const raw = input.topCategory ?? input.top_category ?? input.category ?? "nature";
    return normalizeCategory(String(raw));
  }
  return "nature";
}

function disposeGroup(group) {
  if (!group) return;
  group.traverse((child) => {
    if (child.geometry) child.geometry.dispose();
    const mat = child.material;
    if (mat) {
      if (Array.isArray(mat)) mat.forEach((m) => m.dispose());
      else mat.dispose();
    }
  });
  group.clear();
}

function setBackground(color, fogNear, fogFar, fogColor) {
  scene.background = new THREE.Color(color);
  if (fogNear != null && fogFar != null) {
    scene.fog = new THREE.Fog(fogColor || color, fogNear, fogFar);
  } else {
    scene.fog = null;
  }
}

function setFogExp2(color, density) {
  scene.background = new THREE.Color(color);
  scene.fog = new THREE.FogExp2(color, density);
}

function addGround(color, size = 80) {
  const mesh = new THREE.Mesh(
    new THREE.PlaneGeometry(size, size),
    new THREE.MeshStandardMaterial({ color, roughness: 0.92 })
  );
  mesh.rotation.x = -Math.PI / 2;
  mesh.receiveShadow = true;
  contentGroup.add(mesh);
  return mesh;
}

function addLights({ ambient = 0.45, sun = 1.2, sunColor = 0xffffff, sunPos = [12, 24, 8] }) {
  contentGroup.add(new THREE.AmbientLight(0xffffff, ambient));
  const dir = new THREE.DirectionalLight(sunColor, sun);
  dir.position.set(sunPos[0], sunPos[1], sunPos[2]);
  dir.castShadow = true;
  dir.shadow.mapSize.set(1024, 1024);
  contentGroup.add(dir);
}

function addDirectionalSun(intensity, sunPos = [20, 35, 15]) {
  contentGroup.add(new THREE.AmbientLight(0xffffff, 0.38));
  const dir = new THREE.DirectionalLight(0xfff5e6, intensity);
  dir.position.set(sunPos[0], sunPos[1], sunPos[2]);
  dir.castShadow = true;
  dir.shadow.mapSize.set(2048, 2048);
  dir.shadow.bias = -0.0002;
  const cam = dir.shadow.camera;
  cam.near = 0.5;
  cam.far = 140;
  cam.left = -50;
  cam.right = 50;
  cam.top = 50;
  cam.bottom = -50;
  contentGroup.add(dir);
}

function getCityBrightness() {
  if (typeof window !== "undefined" && window.__cityBrightness != null) {
    const value = Number(window.__cityBrightness);
    return Number.isFinite(value) ? value : 0.6;
  }
  return 0.6;
}

function addCityRoads(mainColor, crossColor, mainEmissive = 0x000000, mainEmissiveIntensity = 0) {
  const mainRoad = new THREE.Mesh(
    new THREE.PlaneGeometry(10, 85),
    new THREE.MeshStandardMaterial({
      color: mainColor,
      roughness: 0.88,
      emissive: mainEmissive,
      emissiveIntensity: mainEmissiveIntensity,
    })
  );
  mainRoad.rotation.x = -Math.PI / 2;
  mainRoad.position.set(0, 0.04, 0);
  mainRoad.receiveShadow = true;
  contentGroup.add(mainRoad);

  const crossRoad = new THREE.Mesh(
    new THREE.PlaneGeometry(85, 8),
    new THREE.MeshStandardMaterial({ color: crossColor, roughness: 0.9 })
  );
  crossRoad.rotation.x = -Math.PI / 2;
  crossRoad.position.set(0, 0.035, 0);
  crossRoad.receiveShadow = true;
  contentGroup.add(crossRoad);
}

function randomRange(min, max) {
  return min + Math.random() * (max - min);
}

function buildTree(x, z, scale = 1) {
  const g = new THREE.Group();
  const trunk = new THREE.Mesh(
    new THREE.CylinderGeometry(0.25 * scale, 0.35 * scale, 2.2 * scale, 8),
    new THREE.MeshStandardMaterial({ color: 0x5c3d2e, roughness: 0.9 })
  );
  trunk.position.y = 1.1 * scale;
  g.add(trunk);

  const greens = [0x2d6a2e, 0x3d8b3d, 0x4caf50];
  for (let i = 0; i < 3; i++) {
    const leaf = new THREE.Mesh(
      new THREE.SphereGeometry((1.1 - i * 0.15) * scale, 10, 10),
      new THREE.MeshStandardMaterial({ color: greens[i % greens.length], roughness: 0.85 })
    );
    leaf.position.y = (2.4 + i * 0.9) * scale;
    g.add(leaf);
  }
  g.position.set(x, 0, z);
  contentGroup.add(g);
  return g;
}

function buildPalm(x, z, lean = 0.15) {
  const g = new THREE.Group();
  const trunk = new THREE.Mesh(
    new THREE.CylinderGeometry(0.2, 0.32, 5, 8),
    new THREE.MeshStandardMaterial({ color: 0x8b6914, roughness: 0.9 })
  );
  trunk.position.y = 2.5;
  trunk.rotation.z = lean;
  g.add(trunk);

  const crown = new THREE.Group();
  crown.position.set(lean * 2, 5.2, 0);
  for (let i = 0; i < 6; i++) {
    const leaf = new THREE.Mesh(
      new THREE.SphereGeometry(0.55, 8, 8),
      new THREE.MeshStandardMaterial({ color: 0x228b22, roughness: 0.8 })
    );
    const a = (i / 6) * Math.PI * 2;
    leaf.position.set(Math.cos(a) * 1.4, Math.sin(i) * 0.2, Math.sin(a) * 1.4);
    leaf.scale.set(1.6, 0.5, 1);
    crown.add(leaf);
  }
  g.add(crown);
  g.position.set(x, 0, z);
  contentGroup.add(g);
}

function buildBuilding(x, z, w, h, d, color) {
  const mesh = new THREE.Mesh(
    new THREE.BoxGeometry(w, h, d),
    new THREE.MeshStandardMaterial({ color, roughness: 0.65, metalness: 0.1 })
  );
  mesh.position.set(x, h / 2, z);
  mesh.castShadow = true;
  contentGroup.add(mesh);
}

function buildSceneNature() {
  setBackground(0x87ceeb, 10, 34, 0x87ceeb);

  contentGroup.add(new THREE.AmbientLight(0xc8e8c0, 2.0));
  const sun = new THREE.DirectionalLight(0xfff8e0, 2.8);
  sun.position.set(8, 18, 12);
  contentGroup.add(sun);

  const lmat = (c) => new THREE.MeshLambertMaterial({ color: c });
  const flat = (c) => new THREE.MeshLambertMaterial({ color: c, flatShading: true });

  // Ground + beige path
  const grass = new THREE.Mesh(new THREE.PlaneGeometry(60, 55), lmat(0x4a8c3a));
  grass.rotation.x = -Math.PI / 2;
  contentGroup.add(grass);
  const path = new THREE.Mesh(new THREE.PlaneGeometry(3.6, 55), lmat(0xd4c88a));
  path.rotation.x = -Math.PI / 2;
  path.position.y = 0.005;
  contentGroup.add(path);

  // Low-poly 3-tier cone tree
  function buildTree() {
    const g = new THREE.Group();
    const trunk = new THREE.Mesh(new THREE.BoxGeometry(0.28, 1.2, 0.28), lmat(0x6b3820));
    trunk.position.y = 0.6;
    g.add(trunk);
    [[1.50, 2.2, 1.90, 0x2d5c28], [1.10, 1.8, 3.10, 0x3a6f32], [0.72, 1.5, 4.10, 0x3a6f32]].forEach(([r, h, y, c]) => {
      const cone = new THREE.Mesh(new THREE.ConeGeometry(r, h, 6), flat(c));
      cone.position.y = y;
      g.add(cone);
    });
    return g;
  }

  // Hero trees near camera
  [[-4.0, 8.5, 1.85], [-8.5, 7.0, 1.70], [-5.8, 7.8, 1.55], [-12.0, 6.5, 1.80],
   [4.0, 8.5, 1.85], [8.5, 7.0, 1.70], [5.8, 7.8, 1.55], [12.0, 6.5, 1.80]].forEach(([x, z, sc]) => {
    const t = buildTree(); t.scale.setScalar(sc); t.position.set(x, 0, z); contentGroup.add(t);
  });

  // Background forest — 5 rows per side
  let srng = 42;
  const rng = () => { srng ^= srng << 13; srng ^= srng >>> 17; srng ^= srng << 5; return (srng >>> 0) / 0x100000000; };
  for (let row = 0; row < 5; row++) {
    const baseX = 3.6 + row * 2.6;
    const baseSc = 1.05 - row * 0.04;
    for (let col = 0; col < 10; col++) {
      const z = -14 + col * 2.6 + rng() * 1.6 - 0.8;
      const xOff = rng() * 1.4 - 0.7;
      const sc = baseSc * (0.72 + rng() * 0.48);
      const tL = buildTree(); tL.scale.setScalar(sc); tL.position.set(-(baseX + xOff), 0, z);
      const tR = buildTree(); tR.scale.setScalar(sc); tR.position.set(baseX + xOff, 0, z);
      contentGroup.add(tL, tR);
    }
  }

  // Clouds
  [[-5.0, 9.0, -5.0, 1.00], [4.0, 8.2, -9.5, 0.85], [0.5, 10.5, 2.0, 0.72]].forEach(([cx, cy, cz, sc]) => {
    const g = new THREE.Group();
    const m = lmat(0xf2f2f2);
    [[0,0,0,1.0],[-1.35,-0.2,0,0.80],[1.35,-0.2,0,0.85],[0.5,0.45,0,0.70],[-0.5,0.4,0,0.65]].forEach(([bx,by,bz,br]) => {
      const s = new THREE.Mesh(new THREE.SphereGeometry(br*sc, 8, 6), m);
      s.position.set(bx*sc, by*sc, bz*sc);
      g.add(s);
    });
    g.position.set(cx, cy, cz);
    contentGroup.add(g);
  });

  // Rocks on path
  [[0.8,2.2,0.45,0.30],[-0.6,0.3,0.40,1.10],[1.3,-2.0,0.38,0.70],[-1.1,-3.5,0.52,2.00],[0.4,-5.2,0.42,0.40]].forEach(([x,z,sc,ry]) => {
    const r = new THREE.Mesh(new THREE.DodecahedronGeometry(sc*0.55, 0), flat(0x636b7a));
    r.scale.set(1.0, 0.55, 1.1); r.rotation.y = ry; r.position.set(x, sc*0.18, z);
    contentGroup.add(r);
  });

  // Sparkle particles
  const count = 320;
  const pPos = new Float32Array(count * 3);
  const pCol = new Float32Array(count * 3);
  for (let i = 0; i < count; i++) {
    pPos[i*3]=(rng()-0.5)*38; pPos[i*3+1]=4+rng()*11; pPos[i*3+2]=-22+rng()*34;
    if (rng()>0.62) { pCol[i*3]=0.75+rng()*0.25; pCol[i*3+1]=0.85+rng()*0.15; pCol[i*3+2]=0.05; }
    else { const v=0.88+rng()*0.12; pCol[i*3]=pCol[i*3+1]=pCol[i*3+2]=v; }
  }
  const pGeo = new THREE.BufferGeometry();
  pGeo.setAttribute('position', new THREE.BufferAttribute(pPos, 3));
  pGeo.setAttribute('color', new THREE.BufferAttribute(pCol, 3));
  natureParticles = new THREE.Points(pGeo, new THREE.PointsMaterial({
    size: 0.20, vertexColors: true, transparent: true, opacity: 0.88, sizeAttenuation: true,
  }));
  contentGroup.add(natureParticles);
}

function buildSceneBeach() {
  // Camera: ORBIT_BY_CATEGORY.beach = { z:9, height:2.8, lookAtZ:-3 }
  // → camera sits at z=9. ALL objects must be at z < 8 to be VISIBLE.
  setBackground(0xBDE7FF);

  contentGroup.add(new THREE.AmbientLight(0xffffff, 0.65));
  const sunLight = new THREE.DirectionalLight(0xfff8e0, 2.0);
  sunLight.position.set(6, 16, 10);
  sunLight.castShadow = true;
  sunLight.shadow.mapSize.set(1024, 1024);
  sunLight.shadow.camera.near = 0.5;
  sunLight.shadow.camera.far = 50;
  sunLight.shadow.camera.left = -14;
  sunLight.shadow.camera.right = 14;
  sunLight.shadow.camera.top = 14;
  sunLight.shadow.camera.bottom = -14;
  contentGroup.add(sunLight);

  const lmat = (color) => new THREE.MeshLambertMaterial({ color });
  const bmat = (color) => new THREE.MeshBasicMaterial({ color });
  const fmat = (color) => new THREE.MeshLambertMaterial({ color, flatShading: true });

  const beachGroup = new THREE.Group();

  // ── helpers ──────────────────────────────────────────────────────────────────
  function createCloud(cx, cy, cz, sc) {
    const g = new THREE.Group();
    const m = lmat(0xf2f2f2);
    const blobs = [
      [0, 0, 0, 1.0], [-1.3, -0.2, 0, 0.78], [1.3, -0.2, 0, 0.82],
      [0.5, 0.45, 0, 0.68], [-0.5, 0.4, 0, 0.62], [0, -0.3, 0.45, 0.60],
    ];
    for (const [bx, by, bz, br] of blobs) {
      const s = new THREE.Mesh(new THREE.SphereGeometry(br * sc, 8, 6), m);
      s.position.set(bx * sc, by * sc, bz * sc);
      g.add(s);
    }
    g.position.set(cx, cy, cz);
    return g;
  }

  function createPalmTree(x, z, lean) {
    const g = new THREE.Group();
    const trunkH = 5.0;
    const trunk = new THREE.Mesh(
      new THREE.CylinderGeometry(0.14, 0.28, trunkH, 9),
      lmat(0x6b3a20)
    );
    trunk.position.y = trunkH / 2;
    trunk.rotation.z = lean;
    trunk.castShadow = true;
    g.add(trunk);

    const crownX = -Math.sin(lean) * trunkH;
    const crownY = Math.cos(lean) * trunkH;
    const frondMat = fmat(0x2d5e28);
    for (let i = 0; i < 8; i++) {
      const az = (i / 8) * Math.PI * 2;
      const el = i % 2 === 0 ? 0.38 : 0.06;
      const dir = new THREE.Vector3(Math.sin(az), el, Math.cos(az)).normalize();
      const halfH = 1.0;
      const frond = new THREE.Mesh(new THREE.ConeGeometry(0.38, 2.4, 6), frondMat);
      frond.quaternion.copy(
        new THREE.Quaternion().setFromUnitVectors(new THREE.Vector3(0, 1, 0), dir)
      );
      frond.position.set(crownX + dir.x * halfH, crownY + dir.y * halfH, dir.z * halfH);
      g.add(frond);
    }

    const shadowBlob = new THREE.Mesh(new THREE.CircleGeometry(0.55, 16), bmat(0xd4b46a));
    shadowBlob.rotation.x = -Math.PI / 2;
    shadowBlob.scale.set(2.0, 1, 1.2);
    shadowBlob.position.set(crownX * 0.35, 0.006, 0.3);
    g.add(shadowBlob);

    g.position.set(x, 0, z);
    return g;
  }

  function createUmbrella() {
    const g = new THREE.Group();
    const canopy = new THREE.Mesh(new THREE.ConeGeometry(1.8, 0.8, 6), fmat(0xf0c020));
    canopy.position.y = 2.4;
    canopy.rotation.y = Math.PI / 6;
    canopy.castShadow = true;
    g.add(canopy);
    // Pole: r=0.035 — thin so it never blocks the camera view
    const pole = new THREE.Mesh(new THREE.CylinderGeometry(0.035, 0.035, 2.2, 10), bmat(0xb8b8b8));
    pole.position.y = 1.1;
    g.add(pole);
    const shadow = new THREE.Mesh(new THREE.CircleGeometry(1.6, 24), bmat(0xc4a040));
    shadow.rotation.x = -Math.PI / 2;
    shadow.rotation.z = Math.PI / 7;
    shadow.position.set(0.3, 0.007, 0.6);
    g.add(shadow);
    return g;
  }

  function createRock(rx, rz, sc, ry) {
    const r = new THREE.Mesh(new THREE.DodecahedronGeometry(sc, 0), fmat(0x7a8090));
    r.scale.y = 0.55;
    r.rotation.y = ry;
    r.castShadow = true;
    r.position.set(rx, sc * 0.28, rz);
    return r;
  }

  function createTowel(x, z, color) {
    const t = new THREE.Mesh(new THREE.BoxGeometry(1.6, 0.022, 1.05), lmat(color));
    t.position.set(x, 0.011, z);
    t.receiveShadow = true;
    return t;
  }

  // ── ground ────────────────────────────────────────────────────────────────────
  // Sand: camera at z=9 → sand spans z=-5 to z=9 (center z=2). Visible in front.
  const sand = new THREE.Mesh(new THREE.PlaneGeometry(50, 14), lmat(0xEEDC9A));
  sand.rotation.x = -Math.PI / 2;
  sand.position.set(0, 0.005, 2);
  sand.receiveShadow = true;
  beachGroup.add(sand);

  // Ocean: teal-blue, fills horizon behind shoreline
  beachOceanMesh = new THREE.Mesh(
    new THREE.PlaneGeometry(60, 36, 1, 24),
    new THREE.MeshBasicMaterial({ color: 0x1E9DB3 })
  );
  beachOceanMesh.rotation.x = -Math.PI / 2;
  beachOceanMesh.position.set(0, 0.0, -9);
  beachGroup.add(beachOceanMesh);

  // Shore line at water's edge
  const shore = new THREE.Mesh(new THREE.PlaneGeometry(50, 0.35), bmat(0xe0f8ff));
  shore.rotation.x = -Math.PI / 2;
  shore.position.set(0, 0.018, -4);
  beachGroup.add(shore);

  // ── shore waves (static, 3 lines near waterline only) ────────────────────────
  beachWaves = [];
  const waveMat = new THREE.MeshBasicMaterial({ color: 0xb8ecf5, transparent: true, opacity: 0.7 });
  [-4.2, -4.7, -5.1].forEach((wz) => {
    const w = new THREE.Mesh(new THREE.PlaneGeometry(50, 0.09), waveMat);
    w.rotation.x = -Math.PI / 2;
    w.position.set(0, 0.018, wz);
    beachGroup.add(w);
  });

  // ── sun disc ──────────────────────────────────────────────────────────────────
  const sunDisc = new THREE.Mesh(
    new THREE.CircleGeometry(1.2, 32),
    new THREE.MeshBasicMaterial({ color: 0xffe550 })
  );
  sunDisc.position.set(1.5, 7.5, -22);
  beachGroup.add(sunDisc);

  // ── clouds ────────────────────────────────────────────────────────────────────
  beachGroup.add(createCloud(-5.5, 6.8, -18, 0.88));
  beachGroup.add(createCloud(4.5, 7.5, -20, 0.78));
  beachGroup.add(createCloud(0.5, 8.2, -22, 0.65));

  // ── palm trees (z=2 → 7 units in front of camera at z=9) ─────────────────────
  beachGroup.add(createPalmTree(-7.5, 2, 0.05));
  beachGroup.add(createPalmTree(7.5, 2, -0.05));

  // ── umbrella (z=1.5 → 7.5 units in front of camera; thin pole r=0.035) ───────
  const umbrella = createUmbrella();
  umbrella.position.set(0, 0, 1.5);
  beachGroup.add(umbrella);

  // ── towels ────────────────────────────────────────────────────────────────────
  beachGroup.add(createTowel(-1.8, 2.2, 0xc8a8a0));
  beachGroup.add(createTowel(1.6, 2.6, 0x90a8c8));

  // ── sunbeds ───────────────────────────────────────────────────────────────────
  [[-1.9, 0.8, 0xd4b896, -0.2], [1.9, 0.8, 0x8aaac4, 0.2]].forEach(([sx, sz, sc, sry]) => {
    const sb = new THREE.Group();
    const bed = new THREE.Mesh(new THREE.BoxGeometry(1.4, 0.08, 0.52), lmat(sc));
    bed.position.y = 0.12;
    sb.add(bed);
    const back = new THREE.Mesh(new THREE.BoxGeometry(0.52, 0.08, 0.52), lmat(sc));
    back.position.set(-0.48, 0.32, 0);
    back.rotation.z = -0.5;
    sb.add(back);
    for (let li = 0; li < 4; li++) {
      const leg = new THREE.Mesh(new THREE.BoxGeometry(0.05, 0.22, 0.05), lmat(0x9a7040));
      leg.position.set(li < 2 ? -0.5 : 0.5, 0.01, li % 2 === 0 ? -0.2 : 0.2);
      sb.add(leg);
    }
    sb.position.set(sx, 0.02, sz);
    sb.rotation.y = sry;
    beachGroup.add(sb);
  });

  // ── rocks (z=1~3 → on visible sand) ──────────────────────────────────────────
  beachGroup.add(createRock(-2.8, 1.0, 0.46, 0.30));
  beachGroup.add(createRock(2.4, 1.5, 0.41, 1.10));
  beachGroup.add(createRock(-0.4, 3.0, 0.34, 0.70));
  beachGroup.add(createRock(2.8, 3.2, 0.38, 2.00));

  // ── shells (z=0.5~6 → on visible sand) ───────────────────────────────────────
  let srng = 73;
  const rng = () => { srng ^= srng << 13; srng ^= srng >>> 17; srng ^= srng << 5; return (srng >>> 0) / 0x100000000; };
  const shellMat = bmat(0xf2ece0);
  for (let i = 0; i < 22; i++) {
    const sh = new THREE.Mesh(new THREE.SphereGeometry(0.08 + rng() * 0.07, 6, 4), shellMat);
    sh.scale.y = 0.34;
    sh.position.set((rng() - 0.5) * 14, 0.026, 0.5 + rng() * 5.5);
    beachGroup.add(sh);
  }

  contentGroup.add(beachGroup);
}

function buildSceneCityDay() {
  setBackground(0x87ceeb, 60, 130, 0x87ceeb);

  contentGroup.add(new THREE.AmbientLight(0xffffff, 0.8));
  const sun = new THREE.DirectionalLight(0xfff5e0, 2.2);
  sun.position.set(8, 20, 14); sun.castShadow = true;
  contentGroup.add(sun);

  const lmat = (c) => new THREE.MeshLambertMaterial({ color: c });

  // Ground + road
  const ground = new THREE.Mesh(new THREE.PlaneGeometry(40, 60), lmat(0x888888));
  ground.rotation.x = -Math.PI / 2; contentGroup.add(ground);
  const road = new THREE.Mesh(new THREE.PlaneGeometry(6, 60), lmat(0x555555));
  road.rotation.x = -Math.PI / 2; road.position.y = 0.01; contentGroup.add(road);
  const stripe = new THREE.Mesh(new THREE.PlaneGeometry(0.28, 60), lmat(0xffff99));
  stripe.rotation.x = -Math.PI / 2; stripe.position.y = 0.02; contentGroup.add(stripe);

  // Buildings on both sides
  const bColors = [0xd4cbc0, 0xc8c0b4, 0xe0d8cc, 0xb8b0a4, 0xdcd4c8];
  const wColors = [0x6a8cb8, 0x8cb8a0, 0xb8a06a, 0xa06ab8, 0x6ab8b8];
  const spots = [
    [-6,0,3.5,10,3],[-6,-7,3,14,3.5],[-6,-15,4,8,3.5],[-6,-23,3.5,18,3],
    [-11,0,4,7,4],[-11,-10,5,12,5],[-11,-22,4,9,4],
    [6,0,3.5,12,3],[6,-7,3,9,3.5],[6,-15,4,15,3.5],[6,-24,3.5,7,3],
    [11,0,4,8,4],[11,-10,5,16,5],[11,-22,4,11,4],
  ];
  spots.forEach(([x, z, w, h, d], i) => {
    const bld = new THREE.Mesh(new THREE.BoxGeometry(w, h, d), lmat(bColors[i%5]));
    bld.position.set(x, h/2, z); contentGroup.add(bld);
    const rows = Math.floor(h/1.5), cols = Math.floor(w/1.2);
    for (let r = 0; r < rows; r++) for (let c = 0; c < cols; c++) {
      if (Math.random() < 0.25) continue;
      const win = new THREE.Mesh(new THREE.PlaneGeometry(0.5, 0.6), lmat(wColors[i%5]));
      win.position.set(x-w/2+0.7+c*1.1, 1.2+r*1.5, z+d/2+0.01);
      contentGroup.add(win);
    }
  });

  // Street trees
  function streetTree(x, z) {
    const g = new THREE.Group();
    const trunk = new THREE.Mesh(new THREE.CylinderGeometry(0.10,0.14,2.2,6), lmat(0x5c3d2e));
    trunk.position.y = 1.1; g.add(trunk);
    const crown = new THREE.Mesh(new THREE.SphereGeometry(1.0, 8, 6), lmat(0x3d8b3d));
    crown.position.y = 2.8; g.add(crown);
    g.position.set(x, 0, z); contentGroup.add(g);
  }
  for (let z = 0; z >= -22; z -= 5) { streetTree(-3.8, z); streetTree(3.8, z); }
}

function buildNightBuilding(x, z, w, h, d) {
  const building = new THREE.Group();
  const body = new THREE.Mesh(
    new THREE.BoxGeometry(w, h, d),
    new THREE.MeshStandardMaterial({ color: 0x141422, roughness: 0.88 })
  );
  body.position.y = h / 2;
  body.castShadow = true;
  building.add(body);

  const rows = Math.max(2, Math.floor(h / 1.1));
  const cols = Math.max(2, Math.floor(w / 0.85));
  for (let r = 0; r < rows; r++) {
    for (let c = 0; c < cols; c++) {
      if (Math.random() > 0.62) continue;
      const lit = Math.random() > 0.35;
      const winColor = lit ? 0xfff9c4 : 0xffffff;
      const win = new THREE.Mesh(
        new THREE.BoxGeometry(0.32, 0.48, 0.06),
        new THREE.MeshStandardMaterial({
          color: winColor,
          emissive: lit ? 0xffd54f : 0xffffff,
          emissiveIntensity: lit ? randomRange(0.7, 1.3) : randomRange(0.25, 0.5),
        })
      );
      win.position.set(-w / 2 + 0.55 + c * 0.85, 0.9 + r * 1.1, d / 2 + 0.04);
      building.add(win);
    }
  }

  building.position.set(x, 0, z);
  contentGroup.add(building);
}

function buildSceneCityNight() {
  setBackground(0x050810, 15, 72, 0x050810);

  contentGroup.add(new THREE.AmbientLight(0x223366, 0.5));
  contentGroup.add(new THREE.HemisphereLight(0x334466, 0x111827, 0.35));

  const lmat = (c) => new THREE.MeshLambertMaterial({ color: c });
  const bmat = (c) => new THREE.MeshBasicMaterial({ color: c });
  const fmat = (c) => new THREE.MeshLambertMaterial({ color: c, flatShading: true });

  // Seeded RNG for deterministic layout
  let _s = 97;
  const rng = () => { _s ^= _s << 13; _s ^= _s >>> 17; _s ^= _s << 5; return (_s >>> 0) / 0xffffffff; };

  // Stars
  const sPos = new Float32Array(100 * 3);
  for (let i = 0; i < 100; i++) {
    sPos[i * 3]     = (rng() - 0.5) * 80;
    sPos[i * 3 + 1] = 8 + rng() * 18;
    sPos[i * 3 + 2] = -4 - rng() * 40;
  }
  const sGeo = new THREE.BufferGeometry();
  sGeo.setAttribute('position', new THREE.BufferAttribute(sPos, 3));
  contentGroup.add(new THREE.Points(sGeo, new THREE.PointsMaterial({ color: 0xffffff, size: 0.14, sizeAttenuation: true })));

  const cityGroup = new THREE.Group();

  // ── Ground + road ─────────────────────────────────────────────────────────
  const ground = new THREE.Mesh(new THREE.PlaneGeometry(60, 70), lmat(0x0e0e18));
  ground.rotation.x = -Math.PI / 2; cityGroup.add(ground);

  const road = new THREE.Mesh(new THREE.PlaneGeometry(7.0, 70), lmat(0x111827));
  road.rotation.x = -Math.PI / 2; road.position.y = 0.01; cityGroup.add(road);

  // Sidewalks + curbs
  [-6, 6].forEach(x => {
    const sw = new THREE.Mesh(new THREE.PlaneGeometry(5.0, 70), lmat(0x161b2e));
    sw.rotation.x = -Math.PI / 2; sw.position.set(x, 0.005, 0); cityGroup.add(sw);
    const curb = new THREE.Mesh(new THREE.BoxGeometry(0.18, 0.12, 70), lmat(0x252a3e));
    curb.position.set(x - Math.sign(x) * 2.6, 0.06, 0); cityGroup.add(curb);
  });

  // Center yellow dashes
  for (let z = 10; z >= -30; z -= 3.5) {
    const dash = new THREE.Mesh(new THREE.PlaneGeometry(0.18, 2.0), bmat(0xffa030));
    dash.rotation.x = -Math.PI / 2; dash.position.set(0, 0.02, z); cityGroup.add(dash);
  }

  // ── Buildings ─────────────────────────────────────────────────────────────
  const BCOLS = [0x111827, 0x1f2937, 0x1e1b4b, 0x27272a, 0x1a2038, 0x0f172a, 0x1c1c35];
  const winOn   = bmat(0xfff1a8);
  const winWarm = bmat(0xffd36a);
  const winOff  = bmat(0x26324f);

  function createBuilding(x, z, w, h, d) {
    const g = new THREE.Group();
    const body = new THREE.Mesh(new THREE.BoxGeometry(w, h, d),
      lmat(BCOLS[Math.floor(rng() * BCOLS.length)]));
    body.position.y = h / 2; g.add(body);
    const roof = new THREE.Mesh(new THREE.BoxGeometry(w + 0.2, 0.12, d + 0.2), lmat(0x0d1020));
    roof.position.y = h + 0.06; g.add(roof);
    const rows = Math.max(2, Math.floor(h / 1.5));
    const cols = Math.max(1, Math.floor(w / 1.1));
    for (let r = 0; r < rows; r++) {
      for (let c = 0; c < cols; c++) {
        if (rng() > 0.62) continue;
        const lit = rng() > 0.28;
        const wm = lit ? (rng() > 0.45 ? winOn : winWarm) : winOff;
        const win = new THREE.Mesh(new THREE.PlaneGeometry(0.38, 0.45), wm);
        win.position.set(-w / 2 + 0.6 + c * 1.1, 0.9 + r * 1.5, d / 2 + 0.01); g.add(win);
      }
    }
    g.position.set(x, 0, z); cityGroup.add(g);
  }

  [[-6,2,3.5,10,3.2],[-6,-6,3.2,14,3.0],[-6,-14,3.8,8,3.5],[-6,-22,3.5,18,3.0],
   [-11,0,4.5,7,4.2],[-11,-9,5.0,12,5.0],[-11,-18,4.2,9,4.0],
   [-17,-4,5.5,5,5.5],[-17,-14,5.0,8,5.5]].forEach(([x,z,w,h,d]) => createBuilding(x,z,w,h,d));

  [[6,2,3.5,12,3.0],[6,-6,3.0,9,3.5],[6,-14,3.8,15,3.5],[6,-22,3.5,11,3.0],
   [11,0,4.5,8,4.2],[11,-9,5.0,16,5.0],[11,-18,4.2,10,4.0],
   [17,-4,5.5,6,5.5],[17,-14,5.0,9,5.0]].forEach(([x,z,w,h,d]) => createBuilding(x,z,w,h,d));

  // Distant silhouettes
  [[-22,8],[-18,6],[-14,5],[14,7],[18,5],[22,9],[-26,4],[26,6]].forEach(([x,sh]) => {
    const h = sh + rng() * 6;
    const sil = new THREE.Mesh(new THREE.BoxGeometry(3.5 + rng() * 3, h, 2.5), lmat(0x0a0c18));
    sil.position.set(x, h / 2, -30); cityGroup.add(sil);
  });

  // ── Street lamps ──────────────────────────────────────────────────────────
  function createStreetLight(x, z) {
    const g = new THREE.Group();
    const side = Math.sign(x);
    const pole = new THREE.Mesh(new THREE.CylinderGeometry(0.055, 0.08, 4.2, 6), lmat(0x7a8899));
    pole.position.y = 2.1; g.add(pole);
    const arm = new THREE.Mesh(new THREE.CylinderGeometry(0.04, 0.04, 1.0, 5), lmat(0x7a8899));
    arm.rotation.z = Math.PI / 2; arm.position.set(-side * 0.5, 4.15, 0); g.add(arm);
    const housing = new THREE.Mesh(new THREE.BoxGeometry(0.28, 0.18, 0.28), lmat(0x4a4a5a));
    housing.position.set(-side * 1.0, 4.06, 0); g.add(housing);
    const glow = new THREE.Mesh(new THREE.SphereGeometry(0.11, 7, 6), bmat(0xffd080));
    glow.position.set(-side * 1.0, 4.0, 0); g.add(glow);
    const pl = new THREE.PointLight(0xffa040, 3.5, 14);
    pl.position.set(-side * 1.0, 3.9, 0); g.add(pl);
    g.position.set(x, 0, z); cityGroup.add(g);
  }

  for (let z = 9; z >= -22; z -= 7) {
    createStreetLight(-4.0, z);
    createStreetLight( 4.0, z);
  }

  // ── Trees ─────────────────────────────────────────────────────────────────
  function createTree(x, z, sc) {
    const g = new THREE.Group();
    const trunk = new THREE.Mesh(new THREE.CylinderGeometry(0.08, 0.12, 1.0, 6), lmat(0x3d2b1f));
    trunk.position.y = 0.5; g.add(trunk);
    [[0.60, 1.55], [0.42, 2.20], [0.26, 2.75]].forEach(([r, y]) => {
      const cone = new THREE.Mesh(new THREE.ConeGeometry(r, 0.75, 6), fmat(0x1a3d25));
      cone.position.y = y; g.add(cone);
    });
    g.scale.setScalar(sc); g.position.set(x, 0, z); cityGroup.add(g);
  }

  [[-7.5,5],[-7.5,-2],[-7.5,-10],[-7.5,-18],[7.5,3],[7.5,-5],[7.5,-13],[7.5,-21]]
    .forEach(([x, z]) => createTree(x, z, 0.8 + rng() * 0.25));

  // ── Benches ───────────────────────────────────────────────────────────────
  function createBench(x, z, rotY) {
    const g = new THREE.Group();
    const seat = new THREE.Mesh(new THREE.BoxGeometry(1.1, 0.08, 0.42), lmat(0x4a3222));
    seat.position.y = 0.50; g.add(seat);
    const back = new THREE.Mesh(new THREE.BoxGeometry(1.1, 0.38, 0.07), lmat(0x4a3222));
    back.position.set(0, 0.73, -0.18); g.add(back);
    [[-0.42,-0.15],[0.42,-0.15],[-0.42,0.15],[0.42,0.15]].forEach(([lx,lz]) => {
      const leg = new THREE.Mesh(new THREE.BoxGeometry(0.07, 0.50, 0.07), lmat(0x6a6a7a));
      leg.position.set(lx, 0.25, lz); g.add(leg);
    });
    g.rotation.y = rotY; g.position.set(x, 0, z); cityGroup.add(g);
  }

  createBench(-4.8,  4.5, -Math.PI / 2);
  createBench(-4.8, -4.0, -Math.PI / 2);
  createBench( 4.8,  1.0,  Math.PI / 2);

  // ── Neon signs ────────────────────────────────────────────────────────────
  function createNeonSign(x, y, z, color, w, h) {
    const g = new THREE.Group();
    g.add(new THREE.Mesh(new THREE.BoxGeometry(w, h, 0.08), lmat(0x1a1a2e)));
    const face = new THREE.Mesh(new THREE.PlaneGeometry(w - 0.1, h - 0.08), bmat(color));
    face.position.z = 0.05; g.add(face);
    const pl = new THREE.PointLight(color, 1.0, 5);
    pl.position.set(0, 0, 0.5); g.add(pl);
    g.position.set(x, y, z); cityGroup.add(g);
  }

  createNeonSign(-4.3, 3.8,  1.8, 0xff3366, 1.4, 0.38);
  createNeonSign( 4.3, 3.2,  1.8, 0x00c8ff, 1.2, 0.34);
  createNeonSign(-4.3, 2.5, -3.5, 0xff8c00, 0.95, 0.32);

  // ── Trash cans ────────────────────────────────────────────────────────────
  [[-4.5, 2.0], [4.5, -2.5]].forEach(([x, z]) => {
    const body = new THREE.Mesh(new THREE.CylinderGeometry(0.14, 0.11, 0.55, 8), lmat(0x3a3a4a));
    body.position.set(x, 0.275, z); cityGroup.add(body);
    const lid = new THREE.Mesh(new THREE.CylinderGeometry(0.16, 0.14, 0.06, 8), lmat(0x4a4a5a));
    lid.position.set(x, 0.58, z); cityGroup.add(lid);
  });

  // ── Awnings ───────────────────────────────────────────────────────────────
  [[-5.2, 3.0, 0xa01830], [5.2, 0.0, 0x1e3a6e]].forEach(([x, z, col]) => {
    const awn = new THREE.Mesh(new THREE.BoxGeometry(2.5, 0.12, 1.0), lmat(col));
    awn.position.set(x, 2.8, z + 0.5); cityGroup.add(awn);
    [-0.9, 0.9].forEach(dx => {
      const p = new THREE.Mesh(new THREE.CylinderGeometry(0.04, 0.04, 2.8, 5), lmat(0x888898));
      p.position.set(x + dx, 1.4, z + 1.0); cityGroup.add(p);
    });
  });

  // ── Cars ──────────────────────────────────────────────────────────────────
  function createCar(x, z, dir, bodyColor) {
    const g = new THREE.Group();
    const body = new THREE.Mesh(new THREE.BoxGeometry(1.6, 0.55, 3.4), lmat(bodyColor));
    body.position.y = 0.55; g.add(body);
    const cabin = new THREE.Mesh(new THREE.BoxGeometry(1.2, 0.42, 1.8), lmat(0x111827));
    cabin.position.set(0, 1.02, -0.1); g.add(cabin);
    [[-0.72, 1.1],[0.72, 1.1],[-0.72,-1.1],[0.72,-1.1]].forEach(([wx, wz]) => {
      const wh = new THREE.Mesh(new THREE.CylinderGeometry(0.22, 0.22, 0.20, 8), lmat(0x111111));
      wh.rotation.z = Math.PI / 2; wh.position.set(wx, 0.33, wz); g.add(wh);
    });
    const headPL = new THREE.PointLight(0xfffadc, 3.0, 10);
    headPL.position.set(0, 0.62, 1.7); g.add(headPL);
    const tailPL = new THREE.PointLight(0xff1515, 1.2, 5);
    tailPL.position.set(0, 0.62, -1.7); g.add(tailPL);
    [-0.5, 0.5].forEach(hx => {
      const hm = new THREE.Mesh(new THREE.SphereGeometry(0.075, 6, 4), bmat(0xfffadc));
      hm.position.set(hx, 0.62, 1.72); g.add(hm);
      const tm = new THREE.Mesh(new THREE.SphereGeometry(0.065, 6, 4), bmat(0xff2020));
      tm.position.set(hx, 0.62, -1.72); g.add(tm);
    });
    g.position.set(x, 0, z);
    if (dir < 0) g.rotation.y = Math.PI;
    return g;
  }

  const carDefs = [
    { x: 1.8, z:  3.0, dir:  1, speed: 0.068, color: 0x1a3a5c },
    { x:-1.8, z: -6.0, dir: -1, speed: 0.055, color: 0x3a1212 },
    { x: 1.8, z:-16.0, dir:  1, speed: 0.082, color: 0x2a2a3e },
    { x:-1.8, z: 11.0, dir: -1, speed: 0.073, color: 0x1e4a22 },
    { x: 1.8, z:-26.0, dir:  1, speed: 0.060, color: 0x3a2510 },
    { x:-1.8, z:-20.0, dir: -1, speed: 0.090, color: 0x251a3a },
  ];
  carDefs.forEach(({ x, z, dir, speed, color }) => {
    const mesh = createCar(x, z, dir, color);
    cityGroup.add(mesh);
    cityCars.push({ mesh, dir, speed });
  });

  contentGroup.add(cityGroup);
}

function buildSceneCulture() {
  setBackground(0xf5f0e8); // warm beige, no fog

  contentGroup.add(new THREE.AmbientLight(0xfff5e0, 1.8));
  const spot = new THREE.PointLight(0xfff0a0, 5, 24);
  spot.position.set(0, 4.0, 0);
  contentGroup.add(spot);
  const midPt = new THREE.PointLight(0xffe8a0, 2.5, 16);
  midPt.position.set(0, 3.8, -5);
  contentGroup.add(midPt);
  const paintL = new THREE.PointLight(0xfff0d0, 1.5, 8);
  paintL.position.set(-6.2, 2.8, 3.0);
  contentGroup.add(paintL);
  const paintR = new THREE.PointLight(0xfff0d0, 1.5, 8);
  paintR.position.set(6.2, 2.8, 3.0);
  contentGroup.add(paintR);

  const lmat = (c) => new THREE.MeshLambertMaterial({ color: c });
  const bmat = (c) => new THREE.MeshBasicMaterial({ color: c });

  // Room surfaces
  const floor = new THREE.Mesh(new THREE.PlaneGeometry(14, 32), lmat(0xe8dcc8));
  floor.rotation.x = -Math.PI / 2;
  contentGroup.add(floor);
  const walk = new THREE.Mesh(new THREE.PlaneGeometry(4, 32), lmat(0xf0e8d0));
  walk.rotation.x = -Math.PI / 2; walk.position.y = 0.002;
  contentGroup.add(walk);
  const ceil = new THREE.Mesh(new THREE.PlaneGeometry(14, 32), lmat(0xcfc3a8));
  ceil.rotation.x = Math.PI / 2; ceil.position.y = 4.2;
  contentGroup.add(ceil);
  const wallL = new THREE.Mesh(new THREE.PlaneGeometry(32, 4.2), lmat(0xd4c8ac));
  wallL.rotation.y = Math.PI / 2; wallL.position.set(-7, 2.1, 0);
  contentGroup.add(wallL);
  const wallR = new THREE.Mesh(new THREE.PlaneGeometry(32, 4.2), lmat(0xd4c8ac));
  wallR.rotation.y = -Math.PI / 2; wallR.position.set(7, 2.1, 0);
  contentGroup.add(wallR);
  const wallB = new THREE.Mesh(new THREE.PlaneGeometry(14, 4.2), lmat(0xd4c8ac));
  wallB.position.set(0, 2.1, -13);
  contentGroup.add(wallB);

  // Ceiling glow disc
  const glowDisc = new THREE.Mesh(new THREE.CircleGeometry(0.7, 32), bmat(0xfff8c0));
  glowDisc.rotation.x = Math.PI / 2; glowDisc.position.set(0, 4.18, 0);
  contentGroup.add(glowDisc);

  // Columns — 3 pairs
  function buildColumn(x, z) {
    const g = new THREE.Group();
    const m = lmat(0xf0ebe0);
    const base = new THREE.Mesh(new THREE.BoxGeometry(0.6, 0.15, 0.6), m); base.position.y = 0.075;
    const shaft = new THREE.Mesh(new THREE.CylinderGeometry(0.18, 0.20, 3.8, 14), m); shaft.position.y = 2.05;
    const capital = new THREE.Mesh(new THREE.CylinderGeometry(0.32, 0.22, 0.22, 14), m); capital.position.y = 4.06;
    const abacus = new THREE.Mesh(new THREE.BoxGeometry(0.72, 0.12, 0.72), m); abacus.position.y = 4.23;
    g.add(base, shaft, capital, abacus);
    g.position.set(x, 0, z);
    contentGroup.add(g);
  }
  [5.5, 1.2, -3.0].forEach(z => { buildColumn(-4.0, z); buildColumn(4.0, z); });

  // Framed paintings — 3 per wall
  function buildPainting(cx, cy, cz, rotY, w, h, artColor) {
    const g = new THREE.Group();
    const fm = lmat(0xb8922a);
    const ft = 0.1, fd = 0.08;
    const tb = new THREE.Mesh(new THREE.BoxGeometry(w+ft*2, ft, fd), fm); tb.position.y = h/2+ft/2;
    const bb = new THREE.Mesh(new THREE.BoxGeometry(w+ft*2, ft, fd), fm); bb.position.y = -(h/2+ft/2);
    const lb = new THREE.Mesh(new THREE.BoxGeometry(ft, h, fd), fm); lb.position.x = -(w/2+ft/2);
    const rb = new THREE.Mesh(new THREE.BoxGeometry(ft, h, fd), fm); rb.position.x = w/2+ft/2;
    const art = new THREE.Mesh(new THREE.PlaneGeometry(w, h), lmat(artColor)); art.position.z = fd/2+0.003;
    g.add(tb, bb, lb, rb, art);
    g.position.set(cx, cy, cz); g.rotation.y = rotY;
    contentGroup.add(g);
  }
  buildPainting(-6.96, 2.1,  4.0,  Math.PI/2, 1.30, 0.96, 0x5c3820);
  buildPainting(-6.96, 2.1,  0.2,  Math.PI/2, 0.90, 0.75, 0x3a5878);
  buildPainting(-6.96, 2.1, -3.8,  Math.PI/2, 0.78, 0.65, 0x6b2020);
  buildPainting( 6.96, 2.1,  4.0, -Math.PI/2, 1.30, 0.96, 0x5c3820);
  buildPainting( 6.96, 2.1,  0.2, -Math.PI/2, 0.90, 0.75, 0x3a5878);
  buildPainting( 6.96, 2.1, -3.8, -Math.PI/2, 0.78, 0.65, 0x6b2020);

  // Vase sculptures on pedestals
  function buildSculpture(x, z, sc) {
    const g = new THREE.Group();
    const pedH = 0.58;
    const ped = new THREE.Mesh(new THREE.BoxGeometry(0.55, pedH, 0.55), lmat(0xd4c8a8));
    ped.position.y = pedH / 2;
    const pts = [
      new THREE.Vector2(0,0), new THREE.Vector2(0.10,0.04), new THREE.Vector2(0.22,0.20),
      new THREE.Vector2(0.28,0.42), new THREE.Vector2(0.28,0.62), new THREE.Vector2(0.22,0.78),
      new THREE.Vector2(0.12,0.90), new THREE.Vector2(0.07,1.00), new THREE.Vector2(0.09,1.06), new THREE.Vector2(0.07,1.12),
    ];
    const vase = new THREE.Mesh(new THREE.LatheGeometry(pts, 24), lmat(0xc8a860));
    vase.scale.setScalar(0.45); vase.position.y = pedH;
    g.add(ped, vase); g.scale.setScalar(sc); g.position.set(x, 0, z);
    contentGroup.add(g);
  }
  buildSculpture(0, 3.8, 1.00);
  buildSculpture(0, 0.8, 0.82);
  buildSculpture(0, -2.2, 0.65);
}

function buildSceneFood() {
  setBackground(0xfff5e6); // warm interior

  contentGroup.add(new THREE.AmbientLight(0xffe8d0, 1.6));
  const overhead = new THREE.PointLight(0xffe0a0, 4, 20);
  overhead.position.set(0, 5, 0);
  contentGroup.add(overhead);
  const tableLight = new THREE.PointLight(0xffd080, 3, 12);
  tableLight.position.set(0, 3, 2);
  contentGroup.add(tableLight);

  const lmat = (c) => new THREE.MeshLambertMaterial({ color: c });
  const bmat = (c) => new THREE.MeshBasicMaterial({ color: c });
  const fmat = (c) => new THREE.MeshLambertMaterial({ color: c, flatShading: true });

  // Room
  const floor = new THREE.Mesh(new THREE.PlaneGeometry(20, 20), lmat(0xc4956a));
  floor.rotation.x = -Math.PI / 2;
  contentGroup.add(floor);
  const wallB = new THREE.Mesh(new THREE.PlaneGeometry(20, 6), lmat(0xfaf0e6));
  wallB.position.set(0, 3, -8);
  contentGroup.add(wallB);
  const wallL = new THREE.Mesh(new THREE.PlaneGeometry(16, 6), lmat(0xf5ede0));
  wallL.rotation.y = Math.PI / 2; wallL.position.set(-8, 3, 0);
  contentGroup.add(wallL);
  const wallR = new THREE.Mesh(new THREE.PlaneGeometry(16, 6), lmat(0xf5ede0));
  wallR.rotation.y = -Math.PI / 2; wallR.position.set(8, 3, 0);
  contentGroup.add(wallR);
  const ceil = new THREE.Mesh(new THREE.PlaneGeometry(20, 20), lmat(0xfaf5ef));
  ceil.rotation.x = Math.PI / 2; ceil.position.y = 6;
  contentGroup.add(ceil);

  // Hanging lamp
  const lampPole = new THREE.Mesh(new THREE.CylinderGeometry(0.04, 0.04, 1.2, 8), bmat(0x555555));
  lampPole.position.set(0, 5.4, 0);
  contentGroup.add(lampPole);
  const lampShade = new THREE.Mesh(new THREE.ConeGeometry(0.5, 0.6, 10), fmat(0xd4a040));
  lampShade.rotation.x = Math.PI; lampShade.position.set(0, 4.5, 0);
  contentGroup.add(lampShade);
  const lampBulb = new THREE.Mesh(new THREE.SphereGeometry(0.15, 8, 8), bmat(0xfffde0));
  lampBulb.position.set(0, 4.6, 0);
  contentGroup.add(lampBulb);

  // Table
  const tableTop = new THREE.Mesh(new THREE.BoxGeometry(3.5, 0.12, 2.0), lmat(0x8b5e3c));
  tableTop.position.set(0, 1.05, 1.0);
  contentGroup.add(tableTop);
  [[-1.4, 0.1], [1.4, 0.1], [-1.4, 1.9], [1.4, 1.9]].forEach(([x, z]) => {
    const leg = new THREE.Mesh(new THREE.CylinderGeometry(0.07, 0.07, 1.0, 8), lmat(0x7a4e30));
    leg.position.set(x, 0.5, z); contentGroup.add(leg);
  });

  // ── Food group ─────────────────────────────────────────────────────────────
  const TBL = 1.11;
  const PY  = 1.14;
  const PSF = 1.17;
  const foodGroup = new THREE.Group();

  function createSteakPlate(px, pz) {
    const g = new THREE.Group();
    const plate = new THREE.Mesh(new THREE.CylinderGeometry(0.44, 0.38, 0.06, 16), lmat(0xf5f5f5));
    plate.position.set(0, PY, 0); g.add(plate);
    const rim = new THREE.Mesh(new THREE.TorusGeometry(0.42, 0.028, 5, 16), lmat(0xe0e0e0));
    rim.rotation.x = Math.PI / 2; rim.position.set(0, PY + 0.02, 0); g.add(rim);
    const steak = new THREE.Mesh(new THREE.CylinderGeometry(0.22, 0.24, 0.065, 5), fmat(0x4a1e0a));
    steak.rotation.y = 0.5; steak.scale.set(1, 1, 0.72);
    steak.position.set(-0.03, PSF + 0.033, 0); g.add(steak);
    for (let i = 0; i < 3; i++) {
      const mark = new THREE.Mesh(new THREE.BoxGeometry(0.22, 0.007, 0.025), bmat(0x220a00));
      mark.rotation.y = 0.5; mark.position.set(-0.03, PSF + 0.068, -0.06 + i * 0.06); g.add(mark);
    }
    const brocHead = new THREE.Mesh(new THREE.SphereGeometry(0.075, 5, 4), fmat(0x2d6a20));
    brocHead.position.set(0.21, PSF + 0.075, -0.14); g.add(brocHead);
    const brocStem = new THREE.Mesh(new THREE.CylinderGeometry(0.022, 0.028, 0.06, 5), lmat(0x3d5a20));
    brocStem.position.set(0.21, PSF + 0.020, -0.14); g.add(brocStem);
    const carrot = new THREE.Mesh(new THREE.ConeGeometry(0.04, 0.16, 5), fmat(0xe85e10));
    carrot.rotation.z = -Math.PI / 2; carrot.rotation.y = 0.3;
    carrot.position.set(0.16, PSF + 0.04, 0.19); g.add(carrot);
    const potato = new THREE.Mesh(new THREE.BoxGeometry(0.10, 0.08, 0.10), fmat(0xd4b06a));
    potato.rotation.y = 0.6; potato.position.set(-0.22, PSF + 0.04, 0.14); g.add(potato);
    g.position.set(px, 0, pz); return g;
  }

  function createPastaPlate(px, pz) {
    const g = new THREE.Group();
    const plate = new THREE.Mesh(new THREE.CylinderGeometry(0.44, 0.38, 0.06, 16), lmat(0xf5f5f5));
    plate.position.set(0, PY, 0); g.add(plate);
    const rim = new THREE.Mesh(new THREE.TorusGeometry(0.42, 0.028, 5, 16), lmat(0xe0e0e0));
    rim.rotation.x = Math.PI / 2; rim.position.set(0, PY + 0.02, 0); g.add(rim);
    const sauce = new THREE.Mesh(new THREE.CylinderGeometry(0.30, 0.30, 0.020, 12), lmat(0xc03020));
    sauce.position.set(0, PSF + 0.010, 0); g.add(sauce);
    const pasta1 = new THREE.Mesh(new THREE.TorusGeometry(0.17, 0.042, 4, 8), fmat(0xe8c060));
    pasta1.rotation.x = Math.PI / 2; pasta1.position.set(0, PSF + 0.022, 0); g.add(pasta1);
    const pasta2 = new THREE.Mesh(new THREE.TorusGeometry(0.10, 0.038, 4, 6), fmat(0xddb850));
    pasta2.rotation.x = Math.PI / 2; pasta2.rotation.z = 0.6;
    pasta2.position.set(0.02, PSF + 0.050, 0.02); g.add(pasta2);
    const ball = new THREE.Mesh(new THREE.SphereGeometry(0.065, 5, 4), fmat(0x5c2a18));
    ball.position.set(0.06, PSF + 0.105, -0.06); g.add(ball);
    const basil = new THREE.Mesh(new THREE.SphereGeometry(0.04, 4, 3), fmat(0x2d5e20));
    basil.scale.set(1.4, 0.3, 1.2); basil.position.set(-0.07, PSF + 0.10, 0.05); g.add(basil);
    g.position.set(px, 0, pz); return g;
  }

  function createBurgerPlate(px, pz) {
    const g = new THREE.Group();
    const plate = new THREE.Mesh(new THREE.CylinderGeometry(0.44, 0.38, 0.06, 16), lmat(0xf5f5f5));
    plate.position.set(0, PY, 0); g.add(plate);
    const rim = new THREE.Mesh(new THREE.TorusGeometry(0.42, 0.028, 5, 16), lmat(0xe0e0e0));
    rim.rotation.x = Math.PI / 2; rim.position.set(0, PY + 0.02, 0); g.add(rim);
    const bx = -0.06;
    const bunB = new THREE.Mesh(new THREE.CylinderGeometry(0.175, 0.175, 0.07, 10), lmat(0xd4986a));
    bunB.position.set(bx, PSF + 0.035, 0); g.add(bunB);
    const lettuce = new THREE.Mesh(new THREE.CylinderGeometry(0.20, 0.20, 0.025, 8), lmat(0x4a8c3a));
    lettuce.position.set(bx, PSF + 0.085, 0); g.add(lettuce);
    const patty = new THREE.Mesh(new THREE.CylinderGeometry(0.185, 0.185, 0.06, 8), fmat(0x3d1c10));
    patty.position.set(bx, PSF + 0.125, 0); g.add(patty);
    const cheese = new THREE.Mesh(new THREE.BoxGeometry(0.26, 0.012, 0.26), lmat(0xffd040));
    cheese.rotation.y = 0.25; cheese.position.set(bx, PSF + 0.163, 0); g.add(cheese);
    const bunT = new THREE.Mesh(
      new THREE.SphereGeometry(0.175, 10, 6, 0, Math.PI * 2, 0, Math.PI / 2), lmat(0xd4986a));
    bunT.position.set(bx, PSF + 0.175, 0); g.add(bunT);
    for (let i = 0; i < 4; i++) {
      const seed = new THREE.Mesh(new THREE.SphereGeometry(0.015, 4, 3), lmat(0xf0e0a0));
      const a = (i / 4) * Math.PI * 2;
      seed.position.set(bx + Math.cos(a) * 0.10, PSF + 0.285, Math.sin(a) * 0.09); g.add(seed);
    }
    const friesMat = lmat(0xf0d050);
    for (let i = 0; i < 5; i++) {
      const fry = new THREE.Mesh(new THREE.CylinderGeometry(0.012, 0.012, 0.18, 5), friesMat);
      fry.rotation.z = (i - 2) * 0.10;
      fry.position.set(0.24 + (i % 2) * 0.04, PSF + 0.09, -0.08 + i * 0.04); g.add(fry);
    }
    g.position.set(px, 0, pz); return g;
  }

  function createSaladBowl(px, pz) {
    const g = new THREE.Group();
    const bowl = new THREE.Mesh(new THREE.CylinderGeometry(0.21, 0.14, 0.18, 8), lmat(0xf0ebe0));
    bowl.position.set(0, TBL + 0.09, 0); g.add(bowl);
    const greens = new THREE.Mesh(new THREE.SphereGeometry(0.15, 6, 4), fmat(0x4a8a30));
    greens.scale.set(1.0, 0.50, 1.0); greens.position.set(0, TBL + 0.215, 0); g.add(greens);
    [[-0.08, -0.06], [0.07, 0.07]].forEach(([dx, dz]) => {
      const tomato = new THREE.Mesh(new THREE.SphereGeometry(0.045, 5, 4), fmat(0xe83030));
      tomato.position.set(dx, TBL + 0.255, dz); g.add(tomato);
    });
    const cuke = new THREE.Mesh(new THREE.CylinderGeometry(0.040, 0.040, 0.013, 8), lmat(0x60a840));
    cuke.position.set(0.09, TBL + 0.265, -0.08); g.add(cuke);
    g.position.set(px, 0, pz); return g;
  }

  function createBreadBasket(px, pz) {
    const g = new THREE.Group();
    const basket = new THREE.Mesh(new THREE.CylinderGeometry(0.18, 0.13, 0.14, 8), lmat(0xc89650));
    basket.position.set(0, TBL + 0.07, 0); g.add(basket);
    [[0, 0.07, 0], [-0.07, 0.08, 0.06], [0.07, 0.06, -0.04]].forEach(([dx, dy, dz]) => {
      const roll = new THREE.Mesh(new THREE.SphereGeometry(0.065, 5, 4), fmat(0xe8c880));
      roll.scale.set(1.1, 0.75, 1.0); roll.position.set(dx, TBL + dy + 0.11, dz); g.add(roll);
    });
    g.position.set(px, 0, pz); return g;
  }

  function createDessert(px, pz) {
    const g = new THREE.Group();
    const dplate = new THREE.Mesh(new THREE.CylinderGeometry(0.21, 0.17, 0.04, 10), lmat(0xf5f5f5));
    dplate.position.set(0, TBL + 0.02, 0); g.add(dplate);
    const cake = new THREE.Mesh(new THREE.CylinderGeometry(0.14, 0.14, 0.22, 8), lmat(0xf08080));
    cake.position.set(0, TBL + 0.15, 0); g.add(cake);
    const frost = new THREE.Mesh(new THREE.CylinderGeometry(0.153, 0.153, 0.025, 8), lmat(0xfff0f0));
    frost.position.set(0, TBL + 0.273, 0); g.add(frost);
    const berry = new THREE.Mesh(new THREE.SphereGeometry(0.04, 5, 4), fmat(0xe82040));
    berry.scale.set(1, 1.1, 1); berry.position.set(0, TBL + 0.308, 0); g.add(berry);
    const candle = new THREE.Mesh(new THREE.CylinderGeometry(0.010, 0.010, 0.10, 6), lmat(0xffd0f0));
    candle.position.set(0, TBL + 0.345, 0); g.add(candle);
    const flame = new THREE.Mesh(new THREE.SphereGeometry(0.020, 4, 3), lmat(0xffcc00));
    flame.scale.set(1, 1.6, 1); flame.position.set(0, TBL + 0.412, 0); g.add(flame);
    g.position.set(px, 0, pz); return g;
  }

  function createDrink(px, pz, liquidColor) {
    const g = new THREE.Group();
    const glass = new THREE.Mesh(
      new THREE.CylinderGeometry(0.075, 0.055, 0.35, 10),
      new THREE.MeshLambertMaterial({ color: 0xc8ecf8, transparent: true, opacity: 0.38 })
    );
    glass.position.set(0, TBL + 0.175, 0); g.add(glass);
    const liquid = new THREE.Mesh(
      new THREE.CylinderGeometry(0.062, 0.046, 0.26, 10),
      new THREE.MeshLambertMaterial({ color: liquidColor, transparent: true, opacity: 0.80 })
    );
    liquid.position.set(0, TBL + 0.145, 0); g.add(liquid);
    const straw = new THREE.Mesh(new THREE.CylinderGeometry(0.009, 0.009, 0.50, 6), lmat(0xff7070));
    straw.position.set(0.036, TBL + 0.425, 0); g.add(straw);
    g.position.set(px, 0, pz); return g;
  }

  foodGroup.add(createSteakPlate(-1.0, 0.65));
  foodGroup.add(createPastaPlate( 0.0, 0.80));
  foodGroup.add(createBurgerPlate(1.0, 0.65));
  foodGroup.add(createSaladBowl(-0.55, 1.42));
  foodGroup.add(createBreadBasket(0.55, 1.42));
  foodGroup.add(createDessert(0.0, 1.62));
  foodGroup.add(createDrink(-1.55, 0.52, 0xb8dcf8));
  foodGroup.add(createDrink( 0.00, 0.44, 0xffb020));
  foodGroup.add(createDrink( 1.55, 0.52, 0xb8dcf8));
  contentGroup.add(foodGroup);

  // Chairs
  function buildChair(x, z, rotY) {
    const g = new THREE.Group();
    const seat = new THREE.Mesh(new THREE.BoxGeometry(0.8, 0.08, 0.8), lmat(0x8b5e3c));
    seat.position.y = 0.52; g.add(seat);
    const back = new THREE.Mesh(new THREE.BoxGeometry(0.8, 0.65, 0.06), lmat(0x7a4e30));
    back.position.set(0, 0.88, -0.37); g.add(back);
    [[-0.3,-0.35],[0.3,-0.35],[-0.3,0.35],[0.3,0.35]].forEach(([lx, lz]) => {
      const leg = new THREE.Mesh(new THREE.CylinderGeometry(0.04, 0.04, 0.52, 6), lmat(0x6a3d20));
      leg.position.set(lx, 0.26, lz); g.add(leg);
    });
    g.position.set(x, 0, z); g.rotation.y = rotY; contentGroup.add(g);
  }
  buildChair(-1.3, 3.3, Math.PI); buildChair(0, 3.3, Math.PI); buildChair(1.3, 3.3, Math.PI);
  buildChair(-1.3, -1.3, Math.PI); buildChair(0, -1.3, Math.PI); buildChair(1.3, -1.3, Math.PI);

  // Corner plants
  function buildPot(x, z) {
    const pot = new THREE.Mesh(new THREE.CylinderGeometry(0.25, 0.20, 0.4, 8), lmat(0xc87845));
    pot.position.set(x, 0.2, z); contentGroup.add(pot);
    const stem = new THREE.Mesh(new THREE.CylinderGeometry(0.04, 0.05, 0.8, 6), lmat(0x3d6b2a));
    stem.position.set(x, 0.8, z); contentGroup.add(stem);
    [0, 1, 2].forEach(i => {
      const leaf = new THREE.Mesh(new THREE.SphereGeometry(0.30, 6, 5), fmat(0x3a7d2c));
      leaf.scale.set(1.4, 0.4, 1.4);
      const a = (i / 3) * Math.PI * 2;
      leaf.position.set(x + Math.cos(a)*0.25, 1.1, z + Math.sin(a)*0.25); contentGroup.add(leaf);
    });
  }
  buildPot(-6.5, -5.5); buildPot(6.5, -5.5);

  // Wall art
  [[-2.5, 0x8b3a3a], [0, 0x2d5a8e], [2.5, 0x4a7a3a]].forEach(([x, ac]) => {
    const frame = new THREE.Mesh(new THREE.BoxGeometry(1.2, 0.9, 0.06), lmat(0x7a5530));
    frame.position.set(x, 3.2, -7.94); contentGroup.add(frame);
    const art = new THREE.Mesh(new THREE.PlaneGeometry(1.0, 0.7), lmat(ac));
    art.position.set(x, 3.2, -7.92); contentGroup.add(art);
  });
}

function buildSceneFestival() {
  // gradient sky via canvas texture
  const cvs = document.createElement('canvas');
  cvs.width = 32; cvs.height = 512;
  const ctx = cvs.getContext('2d');
  const grad = ctx.createLinearGradient(0, 0, 0, 512);
  grad.addColorStop(0.0, '#ff77b7'); grad.addColorStop(0.35, '#ffb347');
  grad.addColorStop(0.7, '#ffd36e'); grad.addColorStop(1.0, '#4a1a6e');
  ctx.fillStyle = grad; ctx.fillRect(0, 0, 32, 512);
  bgTexture = new THREE.CanvasTexture(cvs);
  bgTexture.colorSpace = THREE.SRGBColorSpace;
  scene.background = bgTexture;
  scene.fog = null;
  contentGroup.add(new THREE.AmbientLight(0xffd1f0, 2.8));
  const frontLight = new THREE.PointLight(0xff5db1, 8, 35);
  frontLight.position.set(0, 5, 6); contentGroup.add(frontLight);
  const warmLight = new THREE.PointLight(0xffd36e, 6, 35);
  warmLight.position.set(-5, 4, 4); contentGroup.add(warmLight);
  const fillLight = new THREE.PointLight(0xffffff, 3, 25);
  fillLight.position.set(5, 3, 5); contentGroup.add(fillLight);

  const bmat = (c) => new THREE.MeshBasicMaterial({ color: c });

  // Ground
  const ground = new THREE.Mesh(new THREE.PlaneGeometry(60, 25), bmat(0x3b1060));
  ground.rotation.x = -Math.PI / 2; ground.position.set(0, -0.2, 0);
  contentGroup.add(ground);

  // Stage frame
  const stageFloor = new THREE.Mesh(new THREE.BoxGeometry(7, 0.6, 1.8), bmat(0x16001f));
  stageFloor.position.set(0, 0.2, -2.8); contentGroup.add(stageFloor);
  const poleL = new THREE.Mesh(new THREE.BoxGeometry(0.25, 3.2, 0.25), bmat(0x120018));
  poleL.position.set(-3.2, 1.8, -2.8); contentGroup.add(poleL);
  const poleR = new THREE.Mesh(new THREE.BoxGeometry(0.25, 3.2, 0.25), bmat(0x120018));
  poleR.position.set(3.2, 1.8, -2.8); contentGroup.add(poleR);
  const topBar = new THREE.Mesh(new THREE.BoxGeometry(7, 0.25, 0.25), bmat(0x120018));
  topBar.position.set(0, 3.4, -2.8); contentGroup.add(topBar);

  // Stage bulbs with flicker (lanternMeshes)
  lanternMeshes = [];
  for (let i = -2; i <= 2; i++) {
    const bulbColor = i % 2 === 0 ? 0xffdd44 : 0xff4fb8;
    const bulbMat = new THREE.MeshStandardMaterial({
      color: bulbColor, emissive: bulbColor, emissiveIntensity: 1.4,
    });
    const bulb = new THREE.Mesh(new THREE.SphereGeometry(0.12, 16, 16), bulbMat);
    bulb.position.set(i * 1.2, 3.15, -2.55);
    bulb.userData = { baseIntensity: 1.4, phase: Math.random() * Math.PI * 2, speed: randomRange(1.5, 2.5) };
    lanternMeshes.push(bulb);
    contentGroup.add(bulb);
    const bl = new THREE.PointLight(bulbColor, 1.2, 8);
    bl.position.copy(bulb.position); contentGroup.add(bl);
  }

  // Lantern string
  const lanternColors = [0xff4fb8, 0xffdd44, 0xff7a45, 0x66e3ff];
  for (let i = 0; i < 18; i++) {
    const x = -8.5 + i;
    const y = 5.3 + Math.sin(i * 0.7) * 0.25;
    const lMat = new THREE.MeshStandardMaterial({ color: lanternColors[i%4], emissive: lanternColors[i%4], emissiveIntensity: 1.2 });
    const lantern = new THREE.Mesh(new THREE.SphereGeometry(0.16, 16, 16), lMat);
    lantern.scale.set(1, 1.25, 1); lantern.position.set(x, y, -1.5);
    lantern.userData = { baseIntensity: 1.2, phase: Math.random() * Math.PI * 2, speed: randomRange(1.0, 2.0) };
    lanternMeshes.push(lantern);
    contentGroup.add(lantern);
    const ll = new THREE.PointLight(lanternColors[i%4], 0.5, 4);
    ll.position.set(x, y, -1.5); contentGroup.add(ll);
  }

  // Crowd (silhouettes)
  for (let i = 0; i < 42; i++) {
    const person = new THREE.Group();
    const body = new THREE.Mesh(new THREE.CylinderGeometry(0.08, 0.11, 0.45, 8), bmat(0x09000e));
    body.position.y = 0.25;
    const head = new THREE.Mesh(new THREE.SphereGeometry(0.11, 8, 8), bmat(0x09000e));
    head.position.y = 0.55;
    person.add(body, head);
    person.position.set((Math.random()-0.5)*11, 0, 1.2+Math.random()*4.2);
    person.scale.setScalar(0.85 + Math.random() * 0.6);
    contentGroup.add(person);
  }

  // Fireworks + confetti particles
  const count = 520;
  const fPos = new Float32Array(count * 3);
  const fCol = new Float32Array(count * 3);
  fireworksVelocities = new Float32Array(count * 3);
  const palette = [[1,0.25,0.35],[1,0.9,0.2],[0.35,0.75,1],[0.8,0.35,1],[1,0.45,0.75],[0.4,1,0.65]];
  for (let i = 0; i < count; i++) {
    const i3 = i * 3;
    const burst = Math.floor(i / (count / 6));
    const bx = Math.cos((burst/6)*Math.PI*2) * randomRange(2, 8);
    const bz = Math.sin((burst/6)*Math.PI*2) * randomRange(2, 8);
    fPos[i3] = bx + randomRange(-3, 3);
    fPos[i3+1] = randomRange(2, 8);
    fPos[i3+2] = bz + randomRange(-5, 0);
    fireworksVelocities[i3] = randomRange(-0.03, 0.03);
    fireworksVelocities[i3+1] = randomRange(0.03, 0.10);
    fireworksVelocities[i3+2] = randomRange(-0.02, 0.02);
    const c = palette[i % palette.length];
    fCol[i3]=c[0]; fCol[i3+1]=c[1]; fCol[i3+2]=c[2];
  }
  const fGeo = new THREE.BufferGeometry();
  fGeo.setAttribute('position', new THREE.BufferAttribute(fPos, 3));
  fGeo.setAttribute('color', new THREE.BufferAttribute(fCol, 3));
  fireworksPoints = new THREE.Points(fGeo, new THREE.PointsMaterial({
    size: 0.38, vertexColors: true, transparent: true, opacity: 0.95,
    blending: THREE.AdditiveBlending, depthWrite: false,
  }));
  contentGroup.add(fireworksPoints);
}

const SCENE_BUILDERS = {
  nature: buildSceneNature,
  beach: buildSceneBeach,
  culture: buildSceneCulture,
  food: buildSceneFood,
  festival: buildSceneFestival,
};

function rebuildScene(category) {
  if (bgTexture) { bgTexture.dispose(); bgTexture = null; scene.background = new THREE.Color(0x000000); }
  disposeGroup(contentGroup);
  fireworksPoints = null;
  fireworksVelocities = null;
  lanternMeshes = [];
  beachWaves = [];
  beachOceanMesh = null;
  natureParticles = null;
  cityCars = [];

  if (category === "city") {
    citySceneMode = getCityBrightness() >= 0.5 ? "day" : "night";
    if (citySceneMode === "day") buildSceneCityDay();
    else buildSceneCityNight();
    return;
  }

  const builder = SCENE_BUILDERS[category] || buildSceneNature;
  builder();
}

function getOrbitKey() {
  if (currentCategory === "city") {
    return citySceneMode === "night" ? "cityNight" : "cityDay";
  }
  return currentCategory;
}

function updateFireworks(time) {
  if (!fireworksPoints || !fireworksVelocities) return;
  const pos = fireworksPoints.geometry.attributes.position;
  const arr = pos.array;
  for (let i = 0; i < arr.length; i += 3) {
    arr[i] += fireworksVelocities[i];
    arr[i + 1] += fireworksVelocities[i + 1];
    arr[i + 2] += fireworksVelocities[i + 2];
    if (arr[i + 1] > 32) {
      const burst = Math.floor(Math.random() * 6);
      const bx = Math.cos((burst / 6) * Math.PI * 2) * randomRange(2, 9);
      const bz = Math.sin((burst / 6) * Math.PI * 2) * randomRange(2, 9);
      arr[i] = bx + randomRange(-2.5, 2.5);
      arr[i + 1] = randomRange(3, 8);
      arr[i + 2] = bz + randomRange(-2.5, 2.5);
      fireworksVelocities[i] = randomRange(-0.03, 0.03);
      fireworksVelocities[i + 1] = randomRange(0.05, 0.13);
      fireworksVelocities[i + 2] = randomRange(-0.03, 0.03);
    }
  }
  pos.needsUpdate = true;
}

function updateLanterns(time) {
  lanternMeshes.forEach((lamp) => {
    const { baseIntensity, phase, speed } = lamp.userData;
    if (lamp.material && "emissiveIntensity" in lamp.material) {
      lamp.material.emissiveIntensity =
        baseIntensity + Math.sin(time * speed + phase) * 0.45;
    }
  });
}

function onResize() {
  if (!canvas || !camera || !renderer) return;
  const w = canvas.clientWidth || canvas.parentElement?.clientWidth || 640;
  const h = canvas.clientHeight || canvas.parentElement?.clientHeight || 360;
  camera.aspect = w / h;
  camera.updateProjectionMatrix();
  renderer.setSize(w, h, false);
}

function animate(timeMs) {
  animationId = requestAnimationFrame(animate);
  const time = timeMs * 0.001;
  const delta = lastFrameTime ? Math.min((timeMs - lastFrameTime) / 1000, 0.05) : 0.016;
  lastFrameTime = timeMs;

  const orbit = ORBIT_BY_CATEGORY[getOrbitKey()] || {};

  if (orbit.mode === 'sway') {
    camera.position.x = Math.sin(time * (orbit.swaySpeed ?? 0.14)) * (orbit.swayX ?? 0.22);
    camera.position.y = orbit.height ?? 2.8;
    camera.position.z = orbit.z ?? 9;
    camera.lookAt(orbit.lookAtX ?? 0, orbit.lookAtY ?? 1.5, orbit.lookAtZ ?? -3);
  } else {
    const radius = orbit.radius ?? ORBIT_RADIUS;
    const height = orbit.height ?? ORBIT_HEIGHT;
    const speed = orbit.speed ?? ORBIT_SPEED;
    const lookAtX = orbit.lookAtX ?? 0;
    const lookAtY = orbit.lookAtY ?? 2;
    const lookAtZ = orbit.lookAtZ ?? 0;
    orbitAngle += speed * delta;
    camera.position.x = Math.sin(orbitAngle) * radius;
    camera.position.z = Math.cos(orbitAngle) * radius;
    camera.position.y = height;
    camera.lookAt(lookAtX, lookAtY, lookAtZ);
  }

  if (currentCategory === "nature" && natureParticles) {
    const pos = natureParticles.geometry.attributes.position;
    for (let i = 0; i < pos.count; i++) {
      let y = pos.getY(i) - 0.004;
      let x = pos.getX(i) + Math.sin(time * 1.4 + i * 0.25) * 0.003;
      if (y < 2.5) { y = 13 + Math.random() * 3; x = (Math.random() - 0.5) * 38; }
      pos.setX(i, x); pos.setY(i, y);
    }
    pos.needsUpdate = true;
  }

  if (currentCategory === "beach") {
    // waves are static — no per-frame movement
  }

  if (currentCategory === "festival") {
    updateFireworks(time);
    updateLanterns(time);
  }

  if (currentCategory === "city" && citySceneMode === "night" && cityCars.length) {
    cityCars.forEach(({ mesh, dir, speed }) => {
      mesh.position.z += dir * speed;
      if (dir > 0 && mesh.position.z > 15)  mesh.position.z = -32;
      if (dir < 0 && mesh.position.z < -32) mesh.position.z = 15;
    });
  }

  renderer.render(scene, camera);
}

/**
 * @param {HTMLCanvasElement} canvasEl
 */
export function initScene(canvasEl) {
  if (!canvasEl) return;

  if (animationId != null) {
    cancelAnimationFrame(animationId);
    animationId = null;
  }
  lastFrameTime = 0;

  canvas = canvasEl;

  const w = canvas.clientWidth || 640;
  const h = canvas.clientHeight || 360;

  renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: false });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  renderer.setSize(w, h, false);
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFSoftShadowMap;

  scene = new THREE.Scene();
  contentGroup = new THREE.Group();
  scene.add(contentGroup);

  camera = new THREE.PerspectiveCamera(50, w / h, 0.1, 250);
  camera.position.set(0, ORBIT_HEIGHT, ORBIT_RADIUS);
  camera.lookAt(0, 2, 0);

  window.removeEventListener("resize", onResize);
  window.addEventListener("resize", onResize);

  if (currentCategory) {
    rebuildScene(currentCategory);
  } else {
    rebuildScene("nature");
    currentCategory = "nature";
  }

  animationId = requestAnimationFrame(animate);
}

/**
 * @param {string | { topCategory?: string, top_category?: string }} category
 */
export function updateScene(category) {
  const cat = normalizeCategory(category);

  if (!scene || !contentGroup || !renderer) {
    currentCategory = cat;
    if (cat === "city") {
      citySceneMode = getCityBrightness() >= 0.5 ? "day" : "night";
    }
    return;
  }

  if (cat === "city") {
    const nextMode = getCityBrightness() >= 0.5 ? "day" : "night";
    if (cat === currentCategory && nextMode === citySceneMode) return;
    currentCategory = cat;
    citySceneMode = nextMode;
    rebuildScene(cat);
    return;
  }

  if (cat === currentCategory) return;

  currentCategory = cat;
  rebuildScene(cat);
}
