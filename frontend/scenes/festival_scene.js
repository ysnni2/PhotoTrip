/**
 * PhotoTrip — festival stage (gradient sky, crowd, fireworks, confetti, lantern strings).
 */
import * as THREE from "three";

const CONFETTI_COUNT = 160;
const LANTERN_COLORS = [0xff4fb8, 0xffdd44, 0xff7a45, 0x66e3ff];
const FIREWORK_COLORS = [0xffe04b, 0xff4fb8, 0x66e3ff, 0xff7a45, 0xffffff];

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
/** @type {{
 *   points: import("three").Points;
 *   velocities: import("three").Vector3[];
 *   life: number;
 *   age: number;
 * }[]} */
let fireworks = [];

let spawnTimer = 0;
let animTime = 0;

function basicMat(color) {
  return new THREE.MeshBasicMaterial({ color });
}

function createGradientBackground() {
  const canvas = document.createElement("canvas");
  canvas.width = 32;
  canvas.height = 512;
  const ctx = canvas.getContext("2d");
  const grad = ctx.createLinearGradient(0, 0, 0, 512);
  grad.addColorStop(0.0, "#ff77b7");
  grad.addColorStop(0.35, "#ffb347");
  grad.addColorStop(0.7, "#ffd36e");
  grad.addColorStop(1.0, "#2b0b45");
  ctx.fillStyle = grad;
  ctx.fillRect(0, 0, 32, 512);
  bgTexture = new THREE.CanvasTexture(canvas);
  bgTexture.colorSpace = THREE.SRGBColorSpace;
  return bgTexture;
}

function box(contentGroup, w, h, d, color, x, y, z) {
  const mesh = new THREE.Mesh(new THREE.BoxGeometry(w, h, d), basicMat(color));
  mesh.position.set(x, y, z);
  contentGroup.add(mesh);
  return mesh;
}

function createLantern(parent, x, y, z, color) {
  const lantern = new THREE.Mesh(
    new THREE.SphereGeometry(0.16, 16, 16),
    basicMat(color)
  );
  lantern.scale.set(1, 1.25, 1);
  lantern.position.set(x, y, z);
  parent.add(lantern);

  const light = new THREE.PointLight(color, 0.5, 4);
  light.position.set(x, y, z);
  parent.add(light);
}

function createFirework(contentGroup, x, y, z, color) {
  const count = 130;
  const positions = new Float32Array(count * 3);
  const velocities = [];

  for (let i = 0; i < count; i++) {
    positions[i * 3] = x;
    positions[i * 3 + 1] = y;
    positions[i * 3 + 2] = z;

    const theta = Math.random() * Math.PI * 2;
    const phi = Math.random() * Math.PI;
    const speed = 0.03 + Math.random() * 0.08;
    velocities.push(
      new THREE.Vector3(
        Math.sin(phi) * Math.cos(theta) * speed,
        Math.cos(phi) * speed,
        Math.sin(phi) * Math.sin(theta) * speed
      )
    );
  }

  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute("position", new THREE.BufferAttribute(positions, 3));

  const material = new THREE.PointsMaterial({
    color,
    size: 0.08,
    transparent: true,
    opacity: 1,
    depthWrite: false,
    blending: THREE.AdditiveBlending,
  });

  const points = new THREE.Points(geometry, material);
  contentGroup.add(points);

  fireworks.push({
    points,
    velocities,
    life: 1,
    age: 0,
  });
}

function updateFireworks() {
  for (let f = fireworks.length - 1; f >= 0; f--) {
    const firework = fireworks[f];
    const pos = firework.points.geometry.attributes.position;

    firework.age += 0.015;
    firework.life -= 0.012;
    firework.points.material.opacity = Math.max(firework.life, 0);

    for (let i = 0; i < pos.count; i++) {
      pos.setX(i, pos.getX(i) + firework.velocities[i].x);
      pos.setY(i, pos.getY(i) + firework.velocities[i].y);
      pos.setZ(i, pos.getZ(i) + firework.velocities[i].z);
      firework.velocities[i].y -= 0.0006;
    }

    pos.needsUpdate = true;

    if (firework.life <= 0) {
      firework.points.removeFromParent();
      firework.points.geometry.dispose();
      firework.points.material.dispose();
      fireworks.splice(f, 1);
    }
  }
}

function disposeFireworks() {
  fireworks.forEach((firework) => {
    firework.points.geometry.dispose();
    firework.points.material.dispose();
  });
  fireworks = [];
}

function buildConfetti(contentGroup) {
  const confettiGeometry = new THREE.BufferGeometry();
  const confettiPositions = new Float32Array(CONFETTI_COUNT * 3);
  const confettiColors = new Float32Array(CONFETTI_COUNT * 3);
  confettiData = [];

  for (let i = 0; i < CONFETTI_COUNT; i++) {
    confettiPositions[i * 3] = (Math.random() - 0.5) * 18;
    confettiPositions[i * 3 + 1] = Math.random() * 7 + 1.5;
    confettiPositions[i * 3 + 2] = Math.random() * 7 - 1;

    const color = new THREE.Color(LANTERN_COLORS[i % LANTERN_COLORS.length]);
    confettiColors[i * 3] = color.r;
    confettiColors[i * 3 + 1] = color.g;
    confettiColors[i * 3 + 2] = color.b;

    confettiData.push({
      speed: 0.01 + Math.random() * 0.018,
      sway: Math.random() * Math.PI * 2,
    });
  }

  confettiGeometry.setAttribute(
    "position",
    new THREE.BufferAttribute(confettiPositions, 3)
  );
  confettiGeometry.setAttribute(
    "color",
    new THREE.BufferAttribute(confettiColors, 3)
  );

  const confettiMaterial = new THREE.PointsMaterial({
    size: 0.07,
    vertexColors: true,
    transparent: true,
    opacity: 0.9,
  });

  confetti = new THREE.Points(confettiGeometry, confettiMaterial);
  contentGroup.add(confetti);
}

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
  activeCamera = ctx.camera ?? null;
  contentRoot = contentGroup;

  scene.background = createGradientBackground();

  contentGroup.add(new THREE.AmbientLight(0xffd1f0, 1.2));

  const frontLight = new THREE.PointLight(0xff5db1, 4, 30);
  frontLight.position.set(0, 5, 6);
  contentGroup.add(frontLight);

  const warmLight = new THREE.PointLight(0xffd36e, 3, 30);
  warmLight.position.set(-5, 4, 4);
  contentGroup.add(warmLight);

  const ground = new THREE.Mesh(
    new THREE.PlaneGeometry(60, 25),
    basicMat(0x22002f)
  );
  ground.rotation.x = -Math.PI / 2;
  ground.position.set(0, -0.2, 0);
  contentGroup.add(ground);

  box(contentGroup, 7, 0.6, 1.8, 0x16001f, 0, 0.2, -2.8);
  box(contentGroup, 0.25, 3.2, 0.25, 0x120018, -3.2, 1.8, -2.8);
  box(contentGroup, 0.25, 3.2, 0.25, 0x120018, 3.2, 1.8, -2.8);
  box(contentGroup, 7, 0.25, 0.25, 0x120018, 0, 3.4, -2.8);

  for (let i = -2; i <= 2; i++) {
    const bulbColor = i % 2 === 0 ? 0xffdd44 : 0xff4fb8;
    const bulb = new THREE.Mesh(
      new THREE.SphereGeometry(0.12, 16, 16),
      basicMat(bulbColor)
    );
    bulb.position.set(i * 1.2, 3.15, -2.55);
    contentGroup.add(bulb);

    const light = new THREE.PointLight(bulbColor, 1.2, 8);
    light.position.copy(bulb.position);
    contentGroup.add(light);
  }

  stringGroup = new THREE.Group();
  contentGroup.add(stringGroup);

  for (let i = 0; i < 18; i++) {
    const x = -8.5 + i;
    const y = 5.3 + Math.sin(i * 0.7) * 0.25;
    createLantern(
      stringGroup,
      x,
      y,
      -1.5,
      LANTERN_COLORS[i % LANTERN_COLORS.length]
    );
  }

  for (let i = 0; i < 42; i++) {
    const person = new THREE.Group();
    const body = new THREE.Mesh(
      new THREE.CylinderGeometry(0.08, 0.11, 0.45, 8),
      basicMat(0x09000e)
    );
    body.position.y = 0.25;

    const head = new THREE.Mesh(
      new THREE.SphereGeometry(0.11, 8, 8),
      basicMat(0x09000e)
    );
    head.position.y = 0.55;

    person.add(body, head);
    person.position.set(
      (Math.random() - 0.5) * 11,
      0,
      1.2 + Math.random() * 4.2
    );
    person.scale.setScalar(0.85 + Math.random() * 0.6);
    contentGroup.add(person);
  }

  createFirework(contentGroup, -3, 5.8, -5, 0xff4fb8);
  createFirework(contentGroup, 2.5, 6.5, -6, 0xffe04b);
  createFirework(contentGroup, 0, 4.9, -4.5, 0x66e3ff);

  buildConfetti(contentGroup);

  spawnTimer = 0;
  animTime = 0;

  if (activeCamera) {
    activeCamera.position.set(0, 3.2, 12);
    activeCamera.fov = 55;
    activeCamera.lookAt(0, 2.5, 0);
    activeCamera.updateProjectionMatrix();
  }
}

/**
 * @param {number} t — elapsed seconds
 * @param {number} [delta] — frame delta seconds
 */
function animate(t, delta = 0.016) {
  animTime = t;
  spawnTimer += delta;

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

  if (confetti) {
    const pos = confetti.geometry.attributes.position;
    for (let i = 0; i < CONFETTI_COUNT; i++) {
      let y = pos.getY(i) - confettiData[i].speed;
      let x = pos.getX(i) + Math.sin(animTime * 2 + confettiData[i].sway) * 0.006;

      if (y < -0.1) {
        y = 8;
        x = (Math.random() - 0.5) * 18;
      }

      pos.setX(i, x);
      pos.setY(i, y);
    }
    pos.needsUpdate = true;
  }

  if (stringGroup) {
    stringGroup.children.forEach((obj, i) => {
      if (obj.isMesh) {
        obj.scale.setScalar(1 + Math.sin(animTime * 3 + i) * 0.08);
      }
    });
  }

  if (activeCamera) {
    activeCamera.position.x = Math.sin(animTime * 0.25) * 0.35;
    activeCamera.position.y = 3.2;
    activeCamera.position.z = 12;
    activeCamera.lookAt(0, 2.6, -3);
  }
}

function dispose() {
  disposeFireworks();

  if (confetti) {
    confetti.geometry.dispose();
    confetti.material.dispose();
    confetti = null;
  }

  if (bgTexture) {
    bgTexture.dispose();
    bgTexture = null;
  }

  stringGroup = null;
  contentRoot = null;
  confettiData = [];
  activeCamera = null;
  spawnTimer = 0;
  animTime = 0;
}

export default { init, animate, dispose };
