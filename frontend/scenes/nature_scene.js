/**
 * PhotoTrip — simple daytime green hills + deciduous trees.
 */
import * as THREE from "https://esm.sh/three@0.160.0";

const TREE_COUNT = 20;

/** @type {import("three").PerspectiveCamera | null} */
let activeCamera = null;

function randomRange(min, max) {
  return min + Math.random() * (max - min);
}

function lambert(color) {
  return new THREE.MeshLambertMaterial({ color });
}

function addHill(contentGroup, x, y, z) {
  const hill = new THREE.Mesh(
    new THREE.SphereGeometry(12, 24, 16, 0, Math.PI * 2, 0, Math.PI / 2),
    lambert(0x3d6b35)
  );
  hill.position.set(x, y, z);
  contentGroup.add(hill);
}

function createTree() {
  const group = new THREE.Group();

  const trunk = new THREE.Mesh(
    new THREE.CylinderGeometry(0.2, 0.3, 2, 8),
    lambert(0x8b5e3c)
  );
  trunk.position.y = 1;
  group.add(trunk);

  const foliage = new THREE.Mesh(
    new THREE.SphereGeometry(1.5, 12, 12),
    lambert(0x4caf50)
  );
  foliage.position.y = 2.6;
  group.add(foliage);

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
  const rr = ctx.randomRange ?? randomRange;
  activeCamera = ctx.camera ?? null;

  scene.background = new THREE.Color(0x87ceeb);
  scene.fog = new THREE.Fog(0x87ceeb, 30, 80);

  const floor = new THREE.Mesh(
    new THREE.PlaneGeometry(100, 100),
    lambert(0x4a7c3f)
  );
  floor.rotation.x = -Math.PI / 2;
  floor.receiveShadow = true;
  contentGroup.add(floor);

  addHill(contentGroup, -15, -8, -10);
  addHill(contentGroup, 15, -8, -10);
  addHill(contentGroup, 0, -10, -20);

  for (let i = 0; i < TREE_COUNT; i++) {
    const tree = createTree();
    tree.position.set(rr(-20, 20), 0, rr(-25, -5));
    tree.rotation.y = rr(0, Math.PI * 2);
    contentGroup.add(tree);
  }

  const pond = new THREE.Mesh(
    new THREE.CylinderGeometry(1, 1, 0.1, 24),
    lambert(0x5bb8d4)
  );
  pond.position.set(0, 0.05, -5);
  contentGroup.add(pond);

  contentGroup.add(new THREE.AmbientLight(0xffffff, 1.2));
  const sun = new THREE.DirectionalLight(0xfff4e0, 1.5);
  sun.position.set(5, 10, 5);
  contentGroup.add(sun);

  if (activeCamera) {
    activeCamera.position.set(0, 3, 12);
    activeCamera.lookAt(0, 1, 0);
    activeCamera.updateProjectionMatrix();
  }
}

function animate(_t, _delta) {}

function dispose() {
  activeCamera = null;
}

export default { init, animate, dispose };
