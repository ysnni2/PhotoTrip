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
  nature: { radius: 8, height: 4, speed: 0.12, lookAtY: 3.5, lookAtZ: 24 },
  beach: { radius: 5, height: 30, speed: 0.1, lookAtY: 0 },
  food: { radius: 30, height: 25, speed: 0.2, lookAtY: 0 },
  culture: { radius: 25, height: 20, speed: 0.2, lookAtY: 5 },
  festival: { radius: 25, height: 15, speed: 0.2, lookAtY: 4 },
  cityDay: { radius: 30, height: 25, speed: 0.2, lookAtY: 3 },
  cityNight: { radius: 35, height: 28, speed: 0.2, lookAtY: 3 },
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
  setFogExp2(0x87ceeb, 0.035);
  addLights({ ambient: 0.42, sun: 1.1, sunColor: 0xfff8e7, sunPos: [6, 28, 18] });

  const matTrunk = new THREE.MeshStandardMaterial({ color: 0x5c3d2e, roughness: 0.92 });
  const matRock = new THREE.MeshStandardMaterial({ color: 0x7a7a7a, roughness: 0.95 });
  const matGrass = new THREE.MeshStandardMaterial({ color: 0x3d8b37, roughness: 0.9 });
  const greens = [0x2d6a2e, 0x3d8b3d, 0x4caf50, 0x388e3c];

  const ground = new THREE.Mesh(
    new THREE.PlaneGeometry(70, 90),
    new THREE.MeshStandardMaterial({ color: 0x3d8b37, roughness: 0.95 })
  );
  ground.rotation.x = -Math.PI / 2;
  ground.receiveShadow = true;
  contentGroup.add(ground);

  function buildPathTree(x, z) {
    const tree = new THREE.Group();
    const scale = randomRange(0.9, 1.25);
    const trunkH = randomRange(5.5, 7.8) * scale;

    const trunk = new THREE.Mesh(
      new THREE.CylinderGeometry(0.1 * scale, 0.15 * scale, trunkH, 5),
      matTrunk
    );
    trunk.position.y = trunkH / 2;
    trunk.castShadow = true;
    tree.add(trunk);

    const foliageCount = 5 + Math.floor(Math.random() * 3);
    for (let i = 0; i < foliageCount; i++) {
      const mat = new THREE.MeshStandardMaterial({
        color: greens[i % greens.length],
        roughness: 0.88,
      });
      const useIco = Math.random() > 0.35;
      let foliage;
      if (useIco) {
        foliage = new THREE.Mesh(
          new THREE.IcosahedronGeometry(randomRange(0.55, 1.05) * scale, 0),
          mat
        );
      } else {
        foliage = new THREE.Mesh(
          new THREE.SphereGeometry(randomRange(0.65, 1.1) * scale, 5, 5),
          mat
        );
        foliage.scale.set(1.25, 0.4, 1.25);
      }
      const y = trunkH * randomRange(0.5, 0.92);
      foliage.position.set(
        randomRange(-0.55, 0.55),
        y,
        randomRange(-0.55, 0.55)
      );
      foliage.rotation.set(
        randomRange(-0.5, 0.5),
        randomRange(0, Math.PI * 2),
        randomRange(-0.5, 0.5)
      );
      foliage.castShadow = true;
      tree.add(foliage);
    }

    tree.position.set(x, 0, z);
    tree.rotation.y = randomRange(-0.15, 0.15);
    contentGroup.add(tree);
  }

  for (let i = 0; i < 10; i++) {
    const z = 3 + i * 3.8;
    buildPathTree(-randomRange(3.8, 5.5), z + randomRange(-0.6, 0.6));
    buildPathTree(randomRange(3.8, 5.5), z + randomRange(-0.6, 0.6));
  }

  for (let i = 0; i < 10; i++) {
    const rock = new THREE.Mesh(
      new THREE.DodecahedronGeometry(randomRange(0.22, 0.42), 0),
      matRock
    );
    rock.position.set(
      randomRange(-0.35, 0.35),
      randomRange(0.12, 0.28),
      2 + i * 3.2 + randomRange(-0.4, 0.4)
    );
    rock.rotation.set(Math.random(), Math.random(), Math.random());
    rock.castShadow = true;
    contentGroup.add(rock);
  }

  for (let i = 0; i < 110; i++) {
    const gx = randomRange(-28, 28);
    const gz = randomRange(-2, 42);
    if (Math.abs(gx) < 1.2 && gz > 0 && gz < 38) continue;

    const grass = new THREE.Mesh(
      new THREE.SphereGeometry(randomRange(0.08, 0.18), 4, 4),
      matGrass
    );
    grass.position.set(gx, randomRange(0.06, 0.14), gz);
    grass.scale.y = 0.55;
    contentGroup.add(grass);
  }

  const sunGaps = [
    [4.5, 11, 6],
    [-3.5, 13, 12],
    [3, 10, 18],
    [-4, 12, 24],
    [2.5, 11, 30],
    [-2, 14, 8],
  ];
  sunGaps.forEach(([x, y, z]) => {
    const ray = new THREE.PointLight(0xfff0c8, 3.0, 22);
    ray.position.set(x, y, z);
    ray.castShadow = false;
    contentGroup.add(ray);
  });
}

function buildSceneBeach() {
  setBackground(0x40e0d0, 40, 110, 0x40e0d0);
  addLights({ ambient: 0.72, sun: 1.5, sunColor: 0xffffff, sunPos: [0, 35, 5] });

  const matSea = new THREE.MeshStandardMaterial({
    color: 0x2ec4b6,
    roughness: 0.25,
    metalness: 0.08,
  });
  const matSand = new THREE.MeshStandardMaterial({ color: 0xf5f0e8, roughness: 0.95 });
  const matFoam = new THREE.MeshStandardMaterial({ color: 0xffffff, roughness: 0.4 });
  const matTrunk = new THREE.MeshStandardMaterial({ color: 0x8b6914, roughness: 0.9 });
  const matLeaf = new THREE.MeshStandardMaterial({ color: 0x4caf50, roughness: 0.85 });
  const matUmbrella = new THREE.MeshStandardMaterial({ color: 0xe74c3c, roughness: 0.7 });
  const matUmbrellaAlt = new THREE.MeshStandardMaterial({ color: 0xf39c12, roughness: 0.7 });
  const matSunbed = new THREE.MeshStandardMaterial({ color: 0xffffff, roughness: 0.6 });
  const matTurtle = new THREE.MeshStandardMaterial({ color: 0xc4a574, roughness: 0.88 });

  const sea = new THREE.Mesh(new THREE.PlaneGeometry(95, 95), matSea);
  sea.rotation.x = -Math.PI / 2;
  sea.position.y = 0.02;
  sea.receiveShadow = true;
  contentGroup.add(sea);

  const sand = new THREE.Mesh(
    new THREE.CircleGeometry(38, 48, Math.PI, Math.PI),
    matSand
  );
  sand.rotation.x = -Math.PI / 2;
  sand.position.set(0, 0.07, 16);
  sand.receiveShadow = true;
  contentGroup.add(sand);

  for (let i = 0; i < 30; i++) {
    const t = i / 29;
    const angle = Math.PI * (1.12 + t * 0.76);
    const r = 35 + randomRange(-2, 2);
    const foam = new THREE.Mesh(
      new THREE.IcosahedronGeometry(randomRange(0.12, 0.3), 0),
      matFoam
    );
    foam.position.set(
      Math.cos(angle) * r,
      0.12,
      16 - Math.sin(angle) * r + randomRange(-0.4, 0.4)
    );
    foam.rotation.set(Math.random(), Math.random(), Math.random());
    contentGroup.add(foam);
  }

  function buildLowPolyPalm(x, z) {
    const palm = new THREE.Group();
    const trunk = new THREE.Mesh(
      new THREE.CylinderGeometry(0.16, 0.24, 2.4, 6),
      matTrunk
    );
    trunk.position.y = 1.2;
    palm.add(trunk);

    const crownY = 2.45;
    for (let i = 0; i < 6; i++) {
      const leaf = new THREE.Mesh(new THREE.SphereGeometry(0.7, 6, 6), matLeaf);
      const a = (i / 6) * Math.PI * 2;
      leaf.position.set(Math.cos(a) * 1.15, crownY, Math.sin(a) * 1.15);
      leaf.scale.set(1.5, 0.32, 1.5);
      palm.add(leaf);
    }

    palm.position.set(x, 0, z);
    palm.rotation.y = randomRange(0, Math.PI * 2);
    contentGroup.add(palm);
  }

  const palmSpots = [
    [-14, 22], [-8, 26], [-2, 24], [6, 28], [14, 22],
    [18, 16], [12, 14], [-12, 14], [-18, 18], [0, 30],
    [22, 24], [-22, 26], [4, 18], [-6, 32], [10, 12],
  ];
  palmSpots.forEach(([x, z]) => buildLowPolyPalm(x, z));

  function buildParasol(x, z, colorMat) {
    const g = new THREE.Group();
    const pole = new THREE.Mesh(
      new THREE.CylinderGeometry(0.06, 0.07, 1.6, 6),
      new THREE.MeshStandardMaterial({ color: 0xdddddd })
    );
    pole.position.y = 0.8;
    g.add(pole);
    const canopy = new THREE.Mesh(new THREE.ConeGeometry(1.6, 0.9, 8), colorMat);
    canopy.position.y = 1.55;
    g.add(canopy);
    g.position.set(x, 0, z);
    contentGroup.add(g);
  }

  buildParasol(-5, 20, matUmbrella);
  buildParasol(8, 24, matUmbrellaAlt);
  buildParasol(2, 14, matUmbrella);

  function buildSunbed(x, z, rotY = 0) {
    const bed = new THREE.Mesh(
      new THREE.BoxGeometry(2.2, 0.1, 0.85),
      matSunbed
    );
    bed.position.set(x, 0.14, z);
    bed.rotation.y = rotY;
    bed.castShadow = true;
    contentGroup.add(bed);
  }

  buildSunbed(-6.5, 19, 0.35);
  buildSunbed(7, 23, -0.5);
  buildSunbed(1.5, 13.5, 0.1);

  const turtleSpots = [
    [-3, 10, 0.4],
    [11, 11, -0.6],
  ];
  turtleSpots.forEach(([x, z, rot]) => {
    const turtle = new THREE.Mesh(
      new THREE.DodecahedronGeometry(0.55, 0),
      matTurtle
    );
    turtle.position.set(x, 0.2, z);
    turtle.rotation.set(-Math.PI / 2, rot, 0);
    turtle.scale.set(1.2, 0.45, 1.5);
    turtle.castShadow = true;
    contentGroup.add(turtle);
  });
}

function buildSceneCityDay() {
  setBackground(0x87ceeb, 40, 120, 0x87ceeb);
  addDirectionalSun(2.5, [22, 38, 18]);

  const ground = new THREE.Mesh(
    new THREE.PlaneGeometry(95, 95),
    new THREE.MeshStandardMaterial({ color: 0x6e6e6e, roughness: 0.92 })
  );
  ground.rotation.x = -Math.PI / 2;
  ground.receiveShadow = true;
  contentGroup.add(ground);

  addCityRoads(0xf5f5f5, 0x555555);

  const colors = [0xd8d0c4, 0xe8e0d4, 0xcfc7bb, 0xe5ddd0, 0xbcb4a8, 0xf0ebe3];
  let placed = 0;
  let attempts = 0;
  while (placed < 30 && attempts < 120) {
    attempts += 1;
    const x = randomRange(-38, 38);
    const z = randomRange(-38, 38);
    if (Math.abs(x) < 6 && Math.abs(z) < 5) continue;

    const w = randomRange(2.2, 5);
    const d = randomRange(2.2, 5);
    const h = randomRange(5, 18);
    const building = new THREE.Mesh(
      new THREE.BoxGeometry(w, h, d),
      new THREE.MeshStandardMaterial({
        color: colors[placed % colors.length],
        roughness: 0.72,
        metalness: 0.05,
      })
    );
    building.position.set(x, h / 2, z);
    building.castShadow = true;
    building.receiveShadow = true;
    contentGroup.add(building);
    placed += 1;
  }
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
  setBackground(0x050510, 15, 80, 0x050510);
  addLights({ ambient: 0.12, sun: 0.08, sunColor: 0x334466, sunPos: [0, 20, 0] });

  const ground = new THREE.Mesh(
    new THREE.PlaneGeometry(95, 95),
    new THREE.MeshStandardMaterial({ color: 0x0a0a14, roughness: 0.95 })
  );
  ground.rotation.x = -Math.PI / 2;
  contentGroup.add(ground);

  addCityRoads(0xff8c42, 0x1a1a28, 0xff6b35, 0.55);

  let placed = 0;
  let attempts = 0;
  while (placed < 50 && attempts < 200) {
    attempts += 1;
    const x = randomRange(-36, 36);
    const z = randomRange(-36, 36);
    if (Math.abs(x) < 5.5 && Math.abs(z) < 4.5) continue;

    const w = randomRange(1.8, 4.2);
    const d = randomRange(1.8, 4.2);
    const h = randomRange(6, 22);
    buildNightBuilding(x, z, w, h, d);
    placed += 1;
  }

  const lightColors = [
    0xff9800, 0xffc107, 0xfff59d, 0xff7043, 0xffeb3b,
    0xffa726, 0xffd54f, 0xffffff, 0xff8a65, 0xffcc80, 0xffe082, 0xffab40,
  ];
  lightColors.forEach((color, i) => {
    const angle = (i / lightColors.length) * Math.PI * 2;
    const r = randomRange(8, 28);
    const light = new THREE.PointLight(color, randomRange(1.4, 2.4), randomRange(18, 32));
    light.position.set(
      Math.cos(angle) * r,
      randomRange(4, 14),
      Math.sin(angle) * r
    );
    contentGroup.add(light);
  });
}

function buildSceneCulture() {
  setBackground(0xc1693a, 28, 90, 0xc1693a);
  addLights({ ambient: 0.58, sun: 1.45, sunColor: 0xffe0c8, sunPos: [18, 28, 14] });

  const matGround = new THREE.MeshStandardMaterial({ color: 0xb85c38, roughness: 0.95 });
  const matPlatform = new THREE.MeshStandardMaterial({ color: 0xb5651d, roughness: 0.9 });
  const matWall = new THREE.MeshStandardMaterial({ color: 0x9a5a32, roughness: 0.92 });
  const matStone = new THREE.MeshStandardMaterial({ color: 0xa86840, roughness: 0.88 });
  const matRoof = new THREE.MeshStandardMaterial({ color: 0xa0522d, roughness: 0.82 });
  const matSmall = new THREE.MeshStandardMaterial({ color: 0x9a6340, roughness: 0.9 });
  const matStair = new THREE.MeshStandardMaterial({ color: 0x8f5e3a, roughness: 0.93 });
  const matColumn = new THREE.MeshStandardMaterial({ color: 0xc48a5a, roughness: 0.75 });

  const desert = new THREE.Mesh(
    new THREE.PlaneGeometry(100, 100),
    matGround
  );
  desert.rotation.x = -Math.PI / 2;
  desert.receiveShadow = true;
  contentGroup.add(desert);

  const platformTop = 0.55;
  const platform = new THREE.Mesh(
    new THREE.BoxGeometry(42, 0.5, 42),
    matPlatform
  );
  platform.position.y = platformTop / 2;
  platform.castShadow = true;
  platform.receiveShadow = true;
  contentGroup.add(platform);

  const wallH = 2.8;
  const wallY = platformTop + wallH / 2;
  const wallSpan = 42;
  const wallThick = 1.1;
  const half = wallSpan / 2;

  [
    [0, -half, wallSpan, wallThick],
    [0, half, wallSpan, wallThick],
    [-half, 0, wallThick, wallSpan],
    [half, 0, wallThick, wallSpan],
  ].forEach(([x, z, w, d]) => {
    const wall = new THREE.Mesh(new THREE.BoxGeometry(w, wallH, d), matWall);
    wall.position.set(x, wallY, z);
    wall.castShadow = true;
    contentGroup.add(wall);
  });

  function buildMainTemple(x, z, scale = 1) {
    const temple = new THREE.Group();
    let y = platformTop;

    const tiers = [
      { w: 11, d: 11, h: 0.65 },
      { w: 9, d: 9, h: 0.55 },
      { w: 7.2, d: 7.2, h: 0.5 },
    ];
    tiers.forEach((t) => {
      const tier = new THREE.Mesh(
        new THREE.BoxGeometry(t.w * scale, t.h * scale, t.d * scale),
        matStone
      );
      tier.position.y = y + (t.h * scale) / 2;
      tier.castShadow = true;
      temple.add(tier);
      y += t.h * scale;
    });

    const bodyH = 4.2 * scale;
    const body = new THREE.Mesh(
      new THREE.BoxGeometry(5.2 * scale, bodyH, 5.2 * scale),
      matStone
    );
    body.position.y = y + bodyH / 2;
    body.castShadow = true;
    temple.add(body);
    y += bodyH;

    const roofBoxH = 0.9 * scale;
    const roofBox = new THREE.Mesh(
      new THREE.BoxGeometry(5.8 * scale, roofBoxH, 5.8 * scale),
      matRoof
    );
    roofBox.position.y = y + roofBoxH / 2;
    temple.add(roofBox);
    y += roofBoxH;

    const coneH = 3.2 * scale;
    const cone = new THREE.Mesh(
      new THREE.ConeGeometry(4.2 * scale, coneH, 4),
      matRoof
    );
    cone.position.y = y + coneH / 2;
    cone.rotation.y = Math.PI / 4;
    cone.castShadow = true;
    temple.add(cone);
    y += coneH;

    const spireH = 2.8 * scale;
    const spire = new THREE.Mesh(
      new THREE.CylinderGeometry(0.12 * scale, 0.28 * scale, spireH, 8),
      matRoof
    );
    spire.position.y = y + spireH / 2;
    temple.add(spire);

    temple.position.set(x, 0, z);
    contentGroup.add(temple);
  }

  buildMainTemple(-9, -6, 1);
  buildMainTemple(10, 7, 0.92);

  const smallBuildings = [
    [-16, 12, 3.5, 2.2, 3],
    [-14, -14, 2.8, 2.5, 2.4],
    [15, -10, 3, 2, 2.8],
    [16, 14, 2.5, 2.8, 2.2],
    [-5, 15, 2.2, 1.8, 2],
    [6, -15, 2.4, 2.1, 2.6],
    [0, 12, 2, 1.6, 1.8],
    [-12, 0, 2.6, 2, 2.2],
    [13, 2, 2.3, 2.4, 2],
  ];
  smallBuildings.forEach(([x, z, w, h, d]) => {
    const hut = new THREE.Mesh(new THREE.BoxGeometry(w, h, d), matSmall);
    hut.position.set(x, platformTop + h / 2, z);
    hut.castShadow = true;
    contentGroup.add(hut);
  });

  const stairCount = 9;
  for (let i = 0; i < stairCount; i++) {
    const step = new THREE.Mesh(
      new THREE.BoxGeometry(10 + i * 1.1, 0.38, 2.4),
      matStair
    );
    step.position.set(0, 0.19 + i * 0.38, half + 2.5 + i * 2.1);
    step.castShadow = true;
    contentGroup.add(step);
  }

  const columnRows = [
    { z: half - 4, count: 8, spacing: 2.2 },
    { z: half - 7.5, count: 6, spacing: 2.4 },
  ];
  columnRows.forEach(({ z, count, spacing }) => {
    const startX = -((count - 1) * spacing) / 2;
    for (let i = 0; i < count; i++) {
      const col = new THREE.Mesh(
        new THREE.CylinderGeometry(0.22, 0.28, 3.6, 8),
        matColumn
      );
      col.position.set(startX + i * spacing, platformTop + 1.8, z);
      col.castShadow = true;
      contentGroup.add(col);
    }
  });

  const innerColumns = [
    [-7, -2],
    [-7, 2],
    [8, -1],
    [8, 3],
    [0, -8],
    [0, 8],
  ];
  innerColumns.forEach(([x, z]) => {
    const col = new THREE.Mesh(
      new THREE.CylinderGeometry(0.18, 0.24, 2.8, 8),
      matColumn
    );
    col.position.set(x, platformTop + 1.4, z);
    contentGroup.add(col);
  });
}

function buildSceneFood() {
  setBackground(0xf4c2c2, 35, 120, 0xf4c2c2);
  addLights({ ambient: 0.7, sun: 1.6, sunColor: 0xffffff, sunPos: [0, 40, 8] });

  const ocean = new THREE.Mesh(
    new THREE.PlaneGeometry(100, 70),
    new THREE.MeshStandardMaterial({ color: 0xa8d4e6, roughness: 0.75, metalness: 0.05 })
  );
  ocean.rotation.x = -Math.PI / 2;
  ocean.receiveShadow = true;
  contentGroup.add(ocean);

  function addContinent(x, z, w, d, color) {
    const land = new THREE.Mesh(
      new THREE.BoxGeometry(w, 0.35, d),
      new THREE.MeshStandardMaterial({ color, roughness: 0.88 })
    );
    land.position.set(x, 0.18, z);
    land.castShadow = true;
    land.receiveShadow = true;
    contentGroup.add(land);
    return { x, z };
  }

  const northAmerica = addContinent(-22, 10, 14, 11, 0xe8a87c);
  const southAmerica = addContinent(-16, -14, 7, 16, 0xe07b54);
  const europe = addContinent(2, 12, 9, 7, 0xc0392b);
  const africa = addContinent(6, -4, 9, 14, 0xd4875c);
  const asia = addContinent(24, 8, 20, 14, 0xe8c547);
  addContinent(30, -16, 9, 6, 0xc9a96e);

  function buildFoodBowl(x, z, bowlColor, foods) {
    const dish = new THREE.Group();

    const plate = new THREE.Mesh(
      new THREE.CylinderGeometry(1.15, 0.85, 0.28, 18),
      new THREE.MeshStandardMaterial({ color: bowlColor, roughness: 0.65 })
    );
    plate.position.y = 0.5;
    plate.castShadow = true;
    dish.add(plate);

    const rim = new THREE.Mesh(
      new THREE.CylinderGeometry(1.2, 1.15, 0.12, 18),
      new THREE.MeshStandardMaterial({ color: 0x6b2d1f, roughness: 0.7 })
    );
    rim.position.y = 0.62;
    dish.add(rim);

    let stackY = 0.78;
    foods.forEach((food) => {
      let mesh;
      const mat = new THREE.MeshStandardMaterial({
        color: food.color,
        roughness: food.roughness ?? 0.55,
        metalness: food.metalness ?? 0,
      });
      if (food.type === "sphere") {
        mesh = new THREE.Mesh(new THREE.SphereGeometry(food.size, 12, 12), mat);
        mesh.position.y = stackY + food.size;
        stackY += food.size * 2;
      } else if (food.type === "cylinder") {
        mesh = new THREE.Mesh(
          new THREE.CylinderGeometry(food.rTop, food.rBottom, food.height, 12),
          mat
        );
        mesh.position.y = stackY + food.height / 2;
        stackY += food.height;
      } else if (food.type === "cone") {
        mesh = new THREE.Mesh(new THREE.ConeGeometry(food.size, food.height, 10), mat);
        mesh.position.y = stackY + food.height / 2;
        stackY += food.height;
      }
      if (mesh) {
        mesh.castShadow = true;
        dish.add(mesh);
      }
    });

    dish.position.set(x, 0, z);
    contentGroup.add(dish);
  }

  // 북미 — 버거 스택
  buildFoodBowl(northAmerica.x, northAmerica.z, 0x8b4513, [
    { type: "cylinder", rTop: 0.75, rBottom: 0.8, height: 0.22, color: 0xd4a574 },
    { type: "cylinder", rTop: 0.7, rBottom: 0.75, height: 0.18, color: 0x5d4037 },
    { type: "sphere", size: 0.42, color: 0xc0392b },
    { type: "cylinder", rTop: 0.72, rBottom: 0.78, height: 0.2, color: 0xf4d03f },
  ]);

  // 남미 — 옥수수·타코 느낌
  buildFoodBowl(southAmerica.x, southAmerica.z, 0xa93226, [
    { type: "cylinder", rTop: 0.9, rBottom: 0.95, height: 0.15, color: 0xf5deb3 },
    { type: "cylinder", rTop: 0.35, rBottom: 0.35, height: 0.55, color: 0xf1c40f },
    { type: "sphere", size: 0.38, color: 0x27ae60 },
    { type: "sphere", size: 0.32, color: 0xe74c3c },
  ]);

  // 유럽 — 파스타·치즈
  buildFoodBowl(europe.x, europe.z, 0x922b21, [
    { type: "cylinder", rTop: 1.0, rBottom: 0.9, height: 0.2, color: 0xecf0f1 },
    { type: "cylinder", rTop: 0.55, rBottom: 0.6, height: 0.35, color: 0xf39c12 },
    { type: "sphere", size: 0.4, color: 0xf1c40f },
    { type: "cylinder", rTop: 0.25, rBottom: 0.25, height: 0.5, color: 0xe67e22 },
  ]);

  // 아프리카 — 스튜·곡물
  buildFoodBowl(africa.x, africa.z, 0x7b241c, [
    { type: "cylinder", rTop: 1.05, rBottom: 0.88, height: 0.22, color: 0x5d4037 },
    { type: "cone", size: 0.7, height: 0.55, color: 0xd35400 },
    { type: "sphere", size: 0.35, color: 0x2ecc71 },
    { type: "sphere", size: 0.28, color: 0xf39c12 },
  ]);

  // 아시아 — 밥·초밥
  buildFoodBowl(asia.x, asia.z, 0x922b21, [
    { type: "cylinder", rTop: 1.1, rBottom: 0.95, height: 0.18, color: 0x2c3e50 },
    { type: "sphere", size: 0.5, color: 0xfafafa },
    { type: "cylinder", rTop: 0.45, rBottom: 0.5, height: 0.25, color: 0x2ecc71 },
    { type: "sphere", size: 0.3, color: 0xe74c3c },
  ]);

}

function buildSceneFestival() {
  setBackground(0x1a0a2e, 18, 95, 0x1a0a2e);
  addLights({ ambient: 0.18, sun: 0.15, sunColor: 0x6a5acd, sunPos: [0, 20, 0] });

  const matGold = new THREE.MeshStandardMaterial({
    color: 0xffd700,
    metalness: 0.65,
    roughness: 0.35,
    emissive: 0xffa500,
    emissiveIntensity: 0.35,
  });
  const matPost = new THREE.MeshStandardMaterial({ color: 0x3d2b5a, roughness: 0.85 });
  const matCarousel = new THREE.MeshStandardMaterial({
    color: 0xff6b9d,
    roughness: 0.7,
    emissive: 0xff4081,
    emissiveIntensity: 0.2,
  });
  const matCarouselRoof = new THREE.MeshStandardMaterial({
    color: 0x7c4dff,
    roughness: 0.6,
    emissive: 0x536dfe,
    emissiveIntensity: 0.25,
  });

  const plaza = new THREE.Mesh(
    new THREE.CircleGeometry(30, 56),
    new THREE.MeshStandardMaterial({ color: 0x2c1654, roughness: 0.9 })
  );
  plaza.rotation.x = -Math.PI / 2;
  plaza.receiveShadow = true;
  contentGroup.add(plaza);

  const tower = new THREE.Group();
  const towerBase = new THREE.Mesh(
    new THREE.CylinderGeometry(1.4, 1.8, 5, 10),
    matGold
  );
  towerBase.position.y = 2.5;
  tower.add(towerBase);
  const towerSpire = new THREE.Mesh(
    new THREE.ConeGeometry(1.6, 4.5, 10),
    matGold
  );
  towerSpire.position.y = 6.8;
  tower.add(towerSpire);
  const towerCap = new THREE.Mesh(
    new THREE.SphereGeometry(0.55, 10, 10),
    matGold
  );
  towerCap.position.y = 9.4;
  tower.add(towerCap);
  contentGroup.add(tower);

  const carousel = new THREE.Group();
  carousel.position.set(11, 0, 6);
  const roof = new THREE.Mesh(
    new THREE.CylinderGeometry(4.5, 4.8, 0.7, 16),
    matCarouselRoof
  );
  roof.position.y = 5.2;
  carousel.add(roof);
  const carouselBase = new THREE.Mesh(
    new THREE.CylinderGeometry(4.2, 4.5, 0.5, 16),
    matCarousel
  );
  carouselBase.position.y = 0.25;
  carousel.add(carouselBase);
  for (let i = 0; i < 8; i++) {
    const a = (i / 8) * Math.PI * 2;
    const pillar = new THREE.Mesh(
      new THREE.CylinderGeometry(0.14, 0.18, 4.8, 6),
      matPost
    );
    pillar.position.set(Math.cos(a) * 3.2, 2.4, Math.sin(a) * 3.2);
    carousel.add(pillar);
  }
  contentGroup.add(carousel);

  lanternMeshes = [];
  for (let i = 0; i < 10; i++) {
    const angle = (i / 10) * Math.PI * 2;
    const x = Math.cos(angle) * 22;
    const z = Math.sin(angle) * 22;
    const post = new THREE.Group();

    const pole = new THREE.Mesh(
      new THREE.CylinderGeometry(0.12, 0.16, 3.6, 6),
      matPost
    );
    pole.position.y = 1.8;
    post.add(pole);

    const glowColor = i % 2 === 0 ? 0xffc107 : 0xff9800;
    const lamp = new THREE.Mesh(
      new THREE.SphereGeometry(0.42, 10, 10),
      new THREE.MeshStandardMaterial({
        color: glowColor,
        emissive: glowColor,
        emissiveIntensity: 1.4,
      })
    );
    lamp.position.y = 3.85;
    lamp.userData = {
      baseIntensity: 1.4,
      phase: Math.random() * Math.PI * 2,
      speed: randomRange(1.2, 2.2),
    };
    lanternMeshes.push(lamp);
    post.add(lamp);

    const lampLight = new THREE.PointLight(glowColor, 1.2, 10);
    lampLight.position.y = 3.85;
    post.add(lampLight);

    post.position.set(x, 0, z);
    contentGroup.add(post);
  }

  const festLights = [
    [0xff4081, 0, 8, 0],
    [0x40c4ff, -10, 6, 8],
    [0x69f0ae, 10, 6, -6],
    [0xffd740, -8, 5, -10],
    [0xb388ff, 8, 5, 10],
    [0xff5252, 0, 10, -12],
  ];
  festLights.forEach(([color, x, y, z]) => {
    const light = new THREE.PointLight(color, 2.2, 28);
    light.position.set(x, y, z);
    contentGroup.add(light);
  });

  const towerLight = new THREE.PointLight(0xffd54f, 3.0, 35);
  towerLight.position.set(0, 10, 0);
  contentGroup.add(towerLight);

  const count = 520;
  const positions = new Float32Array(count * 3);
  const colors = new Float32Array(count * 3);
  fireworksVelocities = new Float32Array(count * 3);
  const palette = [
    [1, 0.25, 0.35],
    [1, 0.9, 0.2],
    [0.35, 0.75, 1],
    [0.8, 0.35, 1],
    [1, 0.45, 0.75],
    [0.4, 1, 0.65],
  ];

  for (let i = 0; i < count; i++) {
    const i3 = i * 3;
    const burst = Math.floor(i / (count / 6));
    const bx = Math.cos((burst / 6) * Math.PI * 2) * randomRange(2, 8);
    const bz = Math.sin((burst / 6) * Math.PI * 2) * randomRange(2, 8);
    positions[i3] = bx + randomRange(-3, 3);
    positions[i3 + 1] = randomRange(4, 14);
    positions[i3 + 2] = bz + randomRange(-3, 3);
    fireworksVelocities[i3] = randomRange(-0.03, 0.03);
    fireworksVelocities[i3 + 1] = randomRange(0.04, 0.12);
    fireworksVelocities[i3 + 2] = randomRange(-0.03, 0.03);
    const c = palette[i % palette.length];
    colors[i3] = c[0];
    colors[i3 + 1] = c[1];
    colors[i3 + 2] = c[2];
  }

  const geo = new THREE.BufferGeometry();
  geo.setAttribute("position", new THREE.BufferAttribute(positions, 3));
  geo.setAttribute("color", new THREE.BufferAttribute(colors, 3));

  fireworksPoints = new THREE.Points(
    geo,
    new THREE.PointsMaterial({
      size: 0.42,
      vertexColors: true,
      transparent: true,
      opacity: 0.95,
      blending: THREE.AdditiveBlending,
      depthWrite: false,
    })
  );
  contentGroup.add(fireworksPoints);

  const peopleColors = [0xff5252, 0x40c4ff, 0xffca28, 0x69f0ae, 0xab47bc, 0xff8a65];
  for (let i = 0; i < 36; i++) {
    const angle = randomRange(0, Math.PI * 2);
    const r = randomRange(3, 24);
    const person = new THREE.Mesh(
      new THREE.CapsuleGeometry(0.22, 0.45, 4, 8),
      new THREE.MeshStandardMaterial({
        color: peopleColors[i % peopleColors.length],
        roughness: 0.75,
        emissive: peopleColors[i % peopleColors.length],
        emissiveIntensity: 0.15,
      })
    );
    person.position.set(Math.cos(angle) * r, 0.55, Math.sin(angle) * r);
    person.rotation.y = randomRange(0, Math.PI * 2);
    person.castShadow = true;
    contentGroup.add(person);
  }
}

const SCENE_BUILDERS = {
  nature: buildSceneNature,
  beach: buildSceneBeach,
  culture: buildSceneCulture,
  food: buildSceneFood,
  festival: buildSceneFestival,
};

function rebuildScene(category) {
  disposeGroup(contentGroup);
  fireworksPoints = null;
  fireworksVelocities = null;
  lanternMeshes = [];

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

  if (currentCategory === "festival") {
    updateFireworks(time);
    updateLanterns(time);
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
