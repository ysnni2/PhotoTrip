import * as THREE from "three";

let scene, camera, renderer;
let animId;
let waveLines = [];
let cloudGroups = [];
let t = 0;

export default { init, animate, dispose };

function init(canvas) {
  scene = new THREE.Scene();
  scene.background = new THREE.Color(0xBDE7FF);

  camera = new THREE.PerspectiveCamera(70, canvas.clientWidth / canvas.clientHeight, 0.1, 200);
  camera.position.set(0, 3.2, 7.2);
  camera.lookAt(0, 1.1, -2.0);

  renderer = new THREE.WebGLRenderer({ canvas, antialias: true });
  renderer.setSize(canvas.clientWidth, canvas.clientHeight, false);
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));

  scene.add(new THREE.AmbientLight(0xffffff, 0.75));
  const sun = new THREE.DirectionalLight(0xfff2b0, 1.0);
  sun.position.set(3, 6, 4);
  scene.add(sun);

  buildBeachScene();
}

function stdMat(color, roughness = 0.8) {
  return new THREE.MeshStandardMaterial({ color, roughness, metalness: 0.02 });
}

function buildBeachScene() {
  // Sand (bright beige, foreground)
  const sand = new THREE.Mesh(
    new THREE.PlaneGeometry(24, 14),
    stdMat(0xEEDC9A)
  );
  sand.rotation.x = -Math.PI / 2;
  sand.position.set(0, -0.02, 1.5);
  scene.add(sand);

  // Ocean (teal-blue, background plane)
  const ocean = new THREE.Mesh(
    new THREE.PlaneGeometry(28, 8),
    new THREE.MeshStandardMaterial({ color: 0x1E9DB3, roughness: 0.55, metalness: 0.0 })
  );
  ocean.rotation.x = -Math.PI / 2;
  ocean.position.set(0, 0.0, -6.2);
  scene.add(ocean);

  // Horizon line (thin vertical plane in sky, marks sea/sky boundary)
  const horizon = new THREE.Mesh(
    new THREE.PlaneGeometry(28, 0.04),
    new THREE.MeshBasicMaterial({ color: 0xDFF8FF, transparent: true, opacity: 0.85 })
  );
  horizon.position.set(0, 1.05, -10.05);
  scene.add(horizon);

  // Wave lines near shore
  for (let i = 0; i < 5; i++) {
    const wave = new THREE.Mesh(
      new THREE.PlaneGeometry(12 - i * 1.4, 0.04),
      new THREE.MeshBasicMaterial({ color: 0xEFFFFF, transparent: true, opacity: 0.75 })
    );
    wave.rotation.x = -Math.PI / 2;
    wave.position.set((i % 2) * 0.4 - 0.2, 0.015, -2.6 - i * 0.38);
    scene.add(wave);
    waveLines.push(wave);
  }

  // Sun disk in sky
  const sunDisk = new THREE.Mesh(
    new THREE.CircleGeometry(0.65, 32),
    new THREE.MeshBasicMaterial({ color: 0xFFE566 })
  );
  sunDisk.position.set(3.5, 5.5, -12);
  scene.add(sunDisk);

  // Clouds
  cloudGroups.push(buildCloud(-5.0, 5.2, -11, 0.95));
  cloudGroups.push(buildCloud(2.5, 5.8, -13, 0.75));
  cloudGroups.push(buildCloud(7.0, 4.8, -10, 0.6));

  // Central umbrella — pole is intentionally very thin (r=0.035)
  scene.add(buildUmbrella(0, 0, 0.4));

  // Palm trees
  scene.add(buildPalmTree(-6.2, -0.5, 0.22, 0.92));
  scene.add(buildPalmTree(6.2, -0.8, -0.18, 0.92));

  // Sunbeds
  scene.add(buildSunbed(-1.9, 1.0, -0.25, 0xD8B4A0));
  scene.add(buildSunbed(1.9, 1.0, 0.25, 0x93A8C8));

  // Towels / mats
  scene.add(buildTowel(-2.7, 0.2, 0xF4A261));
  scene.add(buildTowel(2.7, 0.25, 0x60A5FA));

  // Surfboard & swim tube
  scene.add(buildSurfboard(-4.0, 1.2, 0xEF4444));
  scene.add(buildSwimTube(3.7, 1.15));

  // Drink cups
  scene.add(buildDrink(-1.2, 0.25));
  scene.add(buildDrink(1.2, 0.25));

  // Beach details: shells, rocks, starfish, footprints
  addBeachDetails();

  // Soft shadows under umbrella and palm trees
  addSoftShadow(0, 0.75, 2.4, 1.3, 0.22);
  addSoftShadow(-6.1, -0.2, 1.1, 0.5, 0.14);
  addSoftShadow(6.1, -0.4, 1.1, 0.5, 0.14);
}

// ─── Object builders ────────────────────────────────────────────────────────

function buildUmbrella(x, y, z) {
  const group = new THREE.Group();

  // Pole: r=0.035, height 1.9 — thin so it never blocks the view
  const pole = new THREE.Mesh(
    new THREE.CylinderGeometry(0.035, 0.035, 1.9, 12),
    stdMat(0xC7C7C7)
  );
  pole.position.set(0, 0.95, 0);
  group.add(pole);

  // Canopy (4-sided low-poly cone, yellow)
  const canopy = new THREE.Mesh(
    new THREE.ConeGeometry(1.45, 0.55, 4),
    stdMat(0xFACC15, 0.55)
  );
  canopy.position.set(0, 1.95, 0);
  canopy.rotation.y = Math.PI / 4;
  canopy.scale.z = 0.75;
  group.add(canopy);

  // Trim ring
  const trim = new THREE.Mesh(
    new THREE.CylinderGeometry(1.05, 1.15, 0.04, 4),
    stdMat(0xFACC15, 0.55)
  );
  trim.position.set(0, 1.68, 0);
  trim.rotation.y = Math.PI / 4;
  trim.scale.z = 0.75;
  group.add(trim);

  group.position.set(x, y, z);
  return group;
}

function buildPalmTree(x, z, tilt, scale) {
  const group = new THREE.Group();

  const trunk = new THREE.Mesh(
    new THREE.CylinderGeometry(0.18, 0.28, 3.5, 8),
    stdMat(0x6B3F1D)
  );
  trunk.position.y = 1.65;
  trunk.rotation.z = tilt;
  group.add(trunk);

  const leafGroup = new THREE.Group();
  for (let i = 0; i < 8; i++) {
    const angle = (Math.PI * 2 * i) / 8;
    const leaf = new THREE.Mesh(
      new THREE.ConeGeometry(0.28, 1.6, 4),
      stdMat(0x1F5E2E)
    );
    leaf.position.set(Math.cos(angle) * 0.45, 0, Math.sin(angle) * 0.45);
    leaf.rotation.z = Math.PI / 2;
    leaf.rotation.y = angle;
    leaf.scale.set(1.3, 0.65, 0.8);
    leafGroup.add(leaf);
  }
  leafGroup.position.y = 3.45;
  leafGroup.rotation.z = tilt;
  group.add(leafGroup);

  group.position.set(x, 0, z);
  group.scale.setScalar(scale);
  return group;
}

function buildSunbed(x, z, rotY, color) {
  const group = new THREE.Group();

  const bed = new THREE.Mesh(
    new THREE.BoxGeometry(1.55, 0.08, 0.55),
    stdMat(color)
  );
  bed.position.y = 0.13;
  group.add(bed);

  const back = new THREE.Mesh(
    new THREE.BoxGeometry(0.6, 0.08, 0.55),
    stdMat(color)
  );
  back.position.set(-0.55, 0.36, 0);
  back.rotation.z = -0.55;
  group.add(back);

  for (let i = 0; i < 4; i++) {
    const leg = new THREE.Mesh(
      new THREE.BoxGeometry(0.06, 0.25, 0.06),
      stdMat(0xA77B4D)
    );
    leg.position.set(i < 2 ? -0.55 : 0.55, 0.02, i % 2 === 0 ? -0.22 : 0.22);
    group.add(leg);
  }

  group.position.set(x, 0.02, z);
  group.rotation.y = rotY;
  return group;
}

function buildTowel(x, z, color) {
  const towel = new THREE.Mesh(
    new THREE.BoxGeometry(1.2, 0.025, 0.55),
    stdMat(color)
  );
  towel.position.set(x, 0.025, z);
  return towel;
}

function buildSurfboard(x, z, color) {
  const group = new THREE.Group();

  // Flat board shape: box scaled wide/thin to mimic surfboard silhouette
  const board = new THREE.Mesh(
    new THREE.BoxGeometry(0.36, 0.08, 1.7),
    stdMat(color)
  );
  board.position.y = 0.04;
  group.add(board);

  const stripe = new THREE.Mesh(
    new THREE.BoxGeometry(0.06, 0.02, 1.4),
    new THREE.MeshBasicMaterial({ color: 0xffffff })
  );
  stripe.position.y = 0.085;
  group.add(stripe);

  group.position.set(x, 0, z);
  group.rotation.y = -0.35;
  return group;
}

function buildSwimTube(x, z) {
  const tube = new THREE.Mesh(
    new THREE.TorusGeometry(0.35, 0.08, 12, 28),
    new THREE.MeshStandardMaterial({ color: 0xFF7AB6, roughness: 0.5 })
  );
  tube.position.set(x, 0.12, z);
  tube.rotation.x = Math.PI / 2;
  return tube;
}

function buildDrink(x, z) {
  const group = new THREE.Group();

  const cup = new THREE.Mesh(
    new THREE.CylinderGeometry(0.08, 0.065, 0.22, 16),
    new THREE.MeshStandardMaterial({ color: 0xBFEFFF, transparent: true, opacity: 0.55, roughness: 0.2 })
  );
  cup.position.y = 0.16;
  group.add(cup);

  const straw = new THREE.Mesh(
    new THREE.CylinderGeometry(0.01, 0.01, 0.32, 8),
    stdMat(0xFFFFFF)
  );
  straw.position.set(0.04, 0.3, 0);
  straw.rotation.z = -0.25;
  group.add(straw);

  group.position.set(x, 0, z);
  return group;
}

function addBeachDetails() {
  // Shells (9 pieces)
  const shellPos = [
    [-4.5, 2.2], [-3.7, 1.8], [-2.9, 2.55],
    [3.1, 2.2], [4.1, 1.65], [-5.2, 0.8],
    [5.2, 0.7], [-1.2, 2.7], [1.4, 2.6]
  ];
  shellPos.forEach(([x, z], i) => {
    const shell = new THREE.Mesh(
      new THREE.SphereGeometry(0.08 + (i % 3) * 0.015, 8, 6),
      stdMat(0xFFF7D6)
    );
    shell.scale.y = 0.35;
    shell.position.set(x, 0.045, z);
    scene.add(shell);
  });

  // Rocks (4 pieces)
  [[-2.9, 0.3], [2.7, 0.2], [-0.8, 1.45], [4.7, 1.2]].forEach(([x, z]) => {
    const rock = new THREE.Mesh(
      new THREE.DodecahedronGeometry(0.23, 0),
      stdMat(0x6B7280)
    );
    rock.scale.set(1.2, 0.55, 0.8);
    rock.position.set(x, 0.11, z);
    scene.add(rock);
  });

  // Starfish (1)
  const star = new THREE.Mesh(
    new THREE.CylinderGeometry(0.18, 0.18, 0.035, 5),
    stdMat(0xF97316)
  );
  star.position.set(-4.3, 0.04, 1.35);
  star.rotation.y = 0.3;
  scene.add(star);

  // Footprints (8 impressions)
  const footMat = new THREE.MeshBasicMaterial({ color: 0xD6BF78, transparent: true, opacity: 0.55 });
  for (let i = 0; i < 8; i++) {
    const foot = new THREE.Mesh(new THREE.SphereGeometry(0.09, 8, 6), footMat);
    foot.scale.set(0.55, 0.08, 1.0);
    foot.position.set(-5.2 + i * 0.33, 0.025, 2.75 + Math.sin(i) * 0.12);
    foot.rotation.y = 0.35;
    scene.add(foot);
  }
}

function addSoftShadow(x, z, sx, sz, opacity) {
  const shadow = new THREE.Mesh(
    new THREE.CircleGeometry(1, 32),
    new THREE.MeshBasicMaterial({ color: 0x3F3F2F, transparent: true, opacity, depthWrite: false })
  );
  shadow.rotation.x = -Math.PI / 2;
  shadow.scale.set(sx, sz, 1);
  shadow.position.set(x, 0.012, z);
  scene.add(shadow);
}

function buildCloud(x, y, z, scale) {
  const group = new THREE.Group();
  const cMat = new THREE.MeshBasicMaterial({ color: 0xffffff, transparent: true, opacity: 0.9 });
  const sizes =   [0.6, 0.45, 0.45, 0.3, 0.3];
  const offsets = [0, -0.35, 0.35, -0.6, 0.6];
  const yOff =    [0,  0.06,  0.06, -0.04, -0.04];

  sizes.forEach((r, i) => {
    const puff = new THREE.Mesh(new THREE.SphereGeometry(r * scale, 10, 10), cMat);
    puff.position.set(offsets[i] * scale, yOff[i] * scale, 0);
    puff.scale.set(1.3, 0.75, 0.65);
    group.add(puff);
  });

  group.position.set(x, y, z);
  scene.add(group);
  return group;
}

// ─── Animation loop ──────────────────────────────────────────────────────────

function animate() {
  animId = requestAnimationFrame(animate);
  t += 0.01;

  // Wave opacity pulse
  waveLines.forEach((w, i) => {
    w.material.opacity = 0.5 + Math.sin(t * 1.8 + i * 0.9) * 0.22;
  });

  // Cloud drift
  cloudGroups.forEach((cloud, i) => {
    cloud.position.x += 0.002 * (i % 2 === 0 ? 1 : 0.65);
    if (cloud.position.x > 12) cloud.position.x = -12;
  });

  // Gentle camera sway
  camera.position.x = Math.sin(t * 0.18) * 0.15;
  camera.lookAt(0, 1.1, -2.0);

  renderer.render(scene, camera);
}

// ─── Cleanup ─────────────────────────────────────────────────────────────────

function dispose() {
  cancelAnimationFrame(animId);
  scene.traverse(obj => {
    if (obj.geometry) obj.geometry.dispose();
    if (obj.material) {
      if (Array.isArray(obj.material)) obj.material.forEach(m => m.dispose());
      else obj.material.dispose();
    }
  });
  renderer.dispose();
}
