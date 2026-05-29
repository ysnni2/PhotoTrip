/**
 * PhotoTrip — beach scene (sand, ocean waves, foam, palms, umbrella, shells).
 * Ported from standalone Three.js beach demo.
 */
import * as THREE from "https://esm.sh/three@0.160.0";

/** @type {THREE.Mesh | null} */
let ocean = null;
/** @type {THREE.BufferAttribute | null} */
let oceanPos = null;
/** @type {THREE.Mesh[]} */
let foams = [];
/** @type {THREE.Group[]} */
let clouds = [];
/** @type {import("three").PerspectiveCamera | null} */
let activeCamera = null;

const SAND_Z = 5;
const OCEAN_Z = -20;
const SHORELINE_Z = -5;

function createPalmTree(contentGroup, x, z, tilt = 0) {
  const group = new THREE.Group();
  const trunkMat = new THREE.MeshStandardMaterial({
    color: 0x6b451f,
    roughness: 0.8,
  });
  const leafMat = new THREE.MeshStandardMaterial({
    color: 0x1f6b3a,
    roughness: 0.65,
  });

  const trunkHeight = 5.2;
  const trunk = new THREE.Mesh(
    new THREE.CylinderGeometry(0.16, 0.28, trunkHeight, 10),
    trunkMat
  );
  trunk.position.y = trunkHeight / 2;
  trunk.castShadow = true;
  group.add(trunk);

  const trunkTop = trunkHeight;
  const leafCount = 8;
  for (let i = 0; i < leafCount; i++) {
    const leaf = new THREE.Mesh(new THREE.ConeGeometry(0.3, 2.0, 4), leafMat);
    const angle = ((Math.PI * 2) / leafCount) * i;
    leaf.rotation.order = "YXZ";
    leaf.rotation.y = angle;
    leaf.rotation.x = Math.PI / 4 + (i % 2) * (Math.PI / 12);
    leaf.position.y = trunkTop;
    leaf.castShadow = true;
    group.add(leaf);
  }

  group.position.set(x, 0, z);
  group.rotation.z = tilt;
  contentGroup.add(group);
  return group;
}

function createUmbrella(contentGroup) {
  const group = new THREE.Group();
  const umbrellaMat = new THREE.MeshStandardMaterial({
    color: 0xd7b12a,
    roughness: 0.55,
  });

  const pole = new THREE.Mesh(
    new THREE.CylinderGeometry(0.04, 0.04, 2.2, 16),
    new THREE.MeshStandardMaterial({ color: 0x8e8e82 })
  );
  pole.position.y = 1.1;
  pole.castShadow = true;
  group.add(pole);

  const top = new THREE.Mesh(new THREE.ConeGeometry(1.5, 0.55, 6), umbrellaMat);
  top.position.y = 2.25;
  top.rotation.y = Math.PI / 6;
  top.castShadow = true;
  group.add(top);

  group.position.set(0, 0, 1.2);
  contentGroup.add(group);
}

function createTowel(contentGroup, x, z, color) {
  const mat = new THREE.MeshStandardMaterial({ color, roughness: 0.85 });
  const towel = new THREE.Mesh(new THREE.BoxGeometry(1.7, 0.04, 0.85), mat);
  towel.position.set(x, 0.08, z);
  towel.rotation.y = Math.random() * 0.2 - 0.1;
  towel.receiveShadow = true;
  contentGroup.add(towel);
}

function createRock(contentGroup, x, z, s = 1) {
  const rock = new THREE.Mesh(
    new THREE.DodecahedronGeometry(0.45 * s, 0),
    new THREE.MeshStandardMaterial({ color: 0x9a9a8e, roughness: 0.9 })
  );
  rock.position.set(x, 0.25 * s, z);
  rock.scale.set(1.3, 0.55, 0.85);
  rock.rotation.set(Math.random(), Math.random(), Math.random());
  rock.castShadow = true;
  rock.receiveShadow = true;
  contentGroup.add(rock);
}

function createCloud(contentGroup, x, y, z, scale = 1) {
  const group = new THREE.Group();
  const mat = new THREE.MeshBasicMaterial({
    color: 0xffffff,
    transparent: true,
    opacity: 0.95,
  });

  const puffs = [
    { r: 0.6, px: 0, py: 0.12, pz: 0 },
    { r: 0.45, px: -0.58, py: 0, pz: 0.05 },
    { r: 0.45, px: 0.58, py: 0.08, pz: -0.04 },
    { r: 0.3, px: -1.05, py: -0.1, pz: 0.03 },
    { r: 0.3, px: 1.05, py: 0.15, pz: -0.02 },
  ];

  puffs.forEach(({ r, px, py, pz }) => {
    const puff = new THREE.Mesh(
      new THREE.SphereGeometry(r * scale, 16, 16),
      mat
    );
    puff.position.set(px * scale, py * scale, pz * scale);
    group.add(puff);
  });

  group.position.set(x, y, z);
  contentGroup.add(group);
  return group;
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
  const PI = Math.PI;

  scene.background = new THREE.Color(0xaeddf5);
  scene.fog = new THREE.Fog(0xaeddf5, 18, 60);

  const sandMat = new THREE.MeshStandardMaterial({
    color: 0xd8c38f,
    roughness: 0.9,
  });
  const oceanMat = new THREE.MeshStandardMaterial({
    color: 0x2f9fb3,
    roughness: 0.35,
    metalness: 0.05,
    transparent: true,
    opacity: 0.88,
    depthWrite: true,
  });
  const foamMat = new THREE.MeshBasicMaterial({
    color: 0xffffff,
    transparent: true,
    opacity: 0.75,
  });
  const whiteMat = new THREE.MeshStandardMaterial({
    color: 0xf8f4dc,
    roughness: 0.7,
  });

  const hemiLight = new THREE.HemisphereLight(0xffffff, 0x8f7a55, 1.5);
  contentGroup.add(hemiLight);

  const sun = new THREE.DirectionalLight(0xfff2c2, 3.5);
  sun.position.set(-7, 10, 5);
  sun.castShadow = true;
  sun.shadow.mapSize.width = 2048;
  sun.shadow.mapSize.height = 2048;
  sun.shadow.camera.left = -25;
  sun.shadow.camera.right = 25;
  sun.shadow.camera.top = 25;
  sun.shadow.camera.bottom = -25;
  contentGroup.add(sun);

  const sand = new THREE.Mesh(new THREE.PlaneGeometry(80, 40), sandMat);
  sand.rotation.x = -PI / 2;
  sand.position.set(0, 0, SAND_Z);
  sand.receiveShadow = true;
  sand.renderOrder = 1;
  contentGroup.add(sand);

  ocean = new THREE.Mesh(
    new THREE.PlaneGeometry(100, 45, 96, 32),
    oceanMat
  );
  ocean.rotation.x = -PI / 2;
  ocean.position.set(0, -0.1, OCEAN_Z);
  ocean.receiveShadow = true;
  ocean.renderOrder = 0;
  contentGroup.add(ocean);
  oceanPos = ocean.geometry.attributes.position;

  foams = [];
  for (let i = 0; i < 5; i++) {
    const foam = new THREE.Mesh(
      new THREE.PlaneGeometry(38 - i * 2, 0.12, 32, 1),
      foamMat.clone()
    );
    foam.rotation.x = -PI / 2;
    foam.position.set(0, 0.01, SHORELINE_Z + 0.15 - i * 0.35);
    foam.renderOrder = 2;
    contentGroup.add(foam);
    foams.push(foam);
  }

  const sunDisk = new THREE.Mesh(
    new THREE.CircleGeometry(2.0, 64),
    new THREE.MeshBasicMaterial({
      color: 0xffd700,
      opacity: 1.0,
    })
  );
  sunDisk.position.set(0, 8, -34);
  contentGroup.add(sunDisk);

  createPalmTree(contentGroup, -5, -0.8, -0.15);
  createPalmTree(contentGroup, 5, -1.0, 0.15);

  createUmbrella(contentGroup);
  createTowel(contentGroup, -1.5, 2.2, 0xb09c73);
  createTowel(contentGroup, 1.6, 2.2, 0x9e8d65);

  createRock(contentGroup, -3.2, -1.7, 0.7);
  createRock(contentGroup, 3.4, -1.9, 0.65);
  createRock(contentGroup, -6.5, 3.5, 0.55);
  createRock(contentGroup, 6.8, 4.2, 0.5);

  clouds = [
    createCloud(contentGroup, -6, 7, -18, 1.5),
    createCloud(contentGroup, 4, 7.5, -22, 1.2),
    createCloud(contentGroup, 9, 6.5, -16, 1.0),
  ];

  for (let i = 0; i < 28; i++) {
    const shell = new THREE.Mesh(
      new THREE.SphereGeometry(0.07, 8, 8),
      whiteMat
    );
    shell.scale.set(1, 0.35, 0.65);
    shell.position.set(
      (Math.random() - 0.5) * 16,
      0.11,
      1 + Math.random() * 9
    );
    contentGroup.add(shell);
  }

  if (activeCamera) {
    activeCamera.position.set(0, 3, 10);
    activeCamera.fov = 55;
    activeCamera.lookAt(0, 1, -3);
    activeCamera.updateProjectionMatrix();
  }
}

/**
 * @param {number} t — elapsed time in seconds
 */
function animate(t) {
  if (ocean && oceanPos) {
    for (let i = 0; i < oceanPos.count; i++) {
      const x = oceanPos.getX(i);
      const y = oceanPos.getY(i);
      const wave =
        Math.sin(x * 0.4 + t * 1.8) * 0.05 +
        Math.sin(y * 0.55 + t * 1.2) * 0.03;
      oceanPos.setZ(i, wave);
    }
    oceanPos.needsUpdate = true;
    ocean.geometry.computeVertexNormals();
  }

  foams.forEach((foam, i) => {
    const baseZ = SHORELINE_Z + 0.15 - i * 0.35;
    foam.position.z = baseZ + Math.sin(t * 1.8 + i) * 0.08;
    foam.material.opacity = 0.45 + Math.sin(t * 2 + i) * 0.18;
  });

  clouds.forEach((cloud, i) => {
    cloud.position.x += 0.003 * (i + 1);
    if (cloud.position.x > 14) cloud.position.x = -14;
  });

  if (activeCamera) {
    activeCamera.position.set(0, 3, 10);
    activeCamera.lookAt(0, 1, -3);
  }
}

function dispose() {
  ocean = null;
  oceanPos = null;
  foams = [];
  clouds = [];
  activeCamera = null;
}

export default { init, animate, dispose };
