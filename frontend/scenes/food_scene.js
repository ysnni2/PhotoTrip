/**
 * PhotoTrip — warm dining table (Korean / Western / Chinese / Japanese).
 */
import * as THREE from "https://esm.sh/three@0.160.0";

const TABLE_TOP_Y = 1.575;

/** @type {import("three").PerspectiveCamera | null} */
let activeCamera = null;
let orbitT = 0;

function mat(color, opts = {}) {
  return new THREE.MeshStandardMaterial({
    color,
    roughness: opts.roughness ?? 0.65,
    metalness: opts.metalness ?? 0.05,
    ...opts,
  });
}

const FOOD_SCALE = 1.5;

function addKorean(group) {
  const cluster = new THREE.Group();
  cluster.position.set(-2, 0, 1);
  cluster.scale.setScalar(FOOD_SCALE);

  const gx = 0;
  const gz = 0;

  const riceBowl = new THREE.Mesh(
    new THREE.CylinderGeometry(0.4, 0.3, 0.3, 20),
    mat(0xf5f5f5)
  );
  riceBowl.position.set(gx - 0.35, 0.2, gz);
  cluster.add(riceBowl);

  const rice = new THREE.Mesh(new THREE.SphereGeometry(0.35, 16, 12), mat(0xffffff));
  rice.position.set(gx - 0.35, 0.42, gz);
  cluster.add(rice);

  const ttuk = new THREE.Mesh(
    new THREE.CylinderGeometry(0.45, 0.4, 0.4, 20),
    mat(0x8b4513)
  );
  ttuk.position.set(gx + 0.35, 0.22, gz);
  cluster.add(ttuk);

  const stew = new THREE.Mesh(new THREE.SphereGeometry(0.3, 14, 12), mat(0xcc2200));
  stew.position.set(gx + 0.35, 0.48, gz);
  cluster.add(stew);

  const light = new THREE.PointLight(0xffe8c8, 1.2, 8);
  light.position.set(gx, 0.6, gz);
  cluster.add(light);
  group.add(cluster);
}

function addWestern(group) {
  const cluster = new THREE.Group();
  cluster.position.set(2, 0, 1);
  cluster.scale.setScalar(FOOD_SCALE);

  const gx = 0;
  const gz = 0;

  const plate = new THREE.Mesh(
    new THREE.CylinderGeometry(0.6, 0.6, 0.05, 32),
    mat(0xffffff)
  );
  plate.position.set(gx, 0.05, gz);
  cluster.add(plate);

  const steak = new THREE.Mesh(new THREE.BoxGeometry(0.5, 0.08, 0.35), mat(0x8b3a0f));
  steak.position.set(gx, 0.12, gz);
  cluster.add(steak);

  const broccoliPositions = [
    [gx - 0.22, gz + 0.18],
    [gx + 0.2, gz + 0.15],
    [gx, gz - 0.2],
  ];
  broccoliPositions.forEach(([x, z]) => {
    const broc = new THREE.Mesh(new THREE.SphereGeometry(0.12, 10, 8), mat(0x2d6a1f));
    broc.position.set(x, 0.18, z);
    cluster.add(broc);
  });

  const light = new THREE.PointLight(0xfff5e6, 1.2, 8);
  light.position.set(gx, 0.55, gz);
  cluster.add(light);
  group.add(cluster);
}

function addChinese(group) {
  const cluster = new THREE.Group();
  cluster.position.set(1.5, 0, -1.5);
  cluster.scale.setScalar(FOOD_SCALE);

  const gx = 0;
  const gz = 0;

  const bowl = new THREE.Mesh(
    new THREE.CylinderGeometry(0.5, 0.4, 0.35, 24),
    mat(0xcc0000)
  );
  bowl.position.set(gx, 0.2, gz);
  cluster.add(bowl);

  const noodles = new THREE.Mesh(
    new THREE.TorusGeometry(0.3, 0.05, 8, 20),
    mat(0xffd700)
  );
  noodles.rotation.x = Math.PI / 2;
  noodles.position.set(gx, 0.42, gz);
  cluster.add(noodles);

  [-0.28, 0.28].forEach((ox) => {
    const chop = new THREE.Mesh(new THREE.BoxGeometry(0.04, 0.04, 0.8), mat(0x6b4226));
    chop.position.set(gx + ox, 0.15, gz + 0.55);
    chop.rotation.z = ox < 0 ? 0.12 : -0.12;
    cluster.add(chop);
  });

  const light = new THREE.PointLight(0xffddb0, 1.2, 8);
  light.position.set(gx, 0.6, gz);
  cluster.add(light);
  group.add(cluster);
}

function addJapanese(group) {
  const cluster = new THREE.Group();
  cluster.position.set(-1.5, 0, -1.5);
  cluster.scale.setScalar(FOOD_SCALE);

  const gx = 0;
  const gz = 0;

  const board = new THREE.Mesh(new THREE.BoxGeometry(1.2, 0.05, 0.4), mat(0xdeb887));
  board.position.set(gx, 0.06, gz);
  cluster.add(board);

  const toppings = [0xff6b6b, 0x1a1a1a, 0xff6b6b];
  [-0.35, 0, 0.35].forEach((ox, i) => {
    const sushi = new THREE.Mesh(
      new THREE.CylinderGeometry(0.12, 0.12, 0.1, 16),
      mat(0xffffff)
    );
    sushi.position.set(gx + ox, 0.16, gz);
    cluster.add(sushi);

    const top = new THREE.Mesh(
      new THREE.BoxGeometry(0.12, 0.06, 0.1),
      mat(toppings[i])
    );
    top.position.set(gx + ox, 0.24, gz);
    cluster.add(top);
  });

  const soy = new THREE.Mesh(
    new THREE.CylinderGeometry(0.12, 0.1, 0.08, 16),
    mat(0x111111)
  );
  soy.position.set(gx + 0.65, 0.1, gz);
  cluster.add(soy);

  const light = new THREE.PointLight(0xfff0d8, 1.2, 8);
  light.position.set(gx, 0.55, gz);
  cluster.add(light);
  group.add(cluster);
}

function addExtraDishes(group) {
  const pizza = new THREE.Mesh(
    new THREE.CylinderGeometry(0.4, 0.4, 0.05, 24),
    mat(0xf4a623)
  );
  pizza.position.set(-1.8, 0.2, 1.0);
  group.add(pizza);

  for (let i = 0; i < 5; i++) {
    const angle = (Math.PI * 2 * i) / 5;
    const topping = new THREE.Mesh(new THREE.SphereGeometry(0.06, 10, 8), mat(0xcc2200));
    topping.position.set(-1.8 + Math.cos(angle) * 0.18, 0.28, 1.0 + Math.sin(angle) * 0.18);
    group.add(topping);
  }

  const pastaPlate = new THREE.Mesh(
    new THREE.CylinderGeometry(0.45, 0.45, 0.05, 24),
    mat(0xffffff)
  );
  pastaPlate.position.set(1.8, 0.2, 1.0);
  group.add(pastaPlate);

  const pasta = new THREE.Mesh(
    new THREE.TorusGeometry(0.25, 0.06, 8, 16),
    mat(0xf5deb3)
  );
  pasta.rotation.x = Math.PI / 2;
  pasta.position.set(1.8, 0.28, 1.0);
  group.add(pasta);

  const cake = new THREE.Mesh(
    new THREE.CylinderGeometry(0.3, 0.3, 0.4, 20),
    mat(0xff9999)
  );
  cake.position.set(1.8, 0.2, -1.0);
  group.add(cake);

  const cherry = new THREE.Mesh(new THREE.SphereGeometry(0.08, 10, 8), mat(0xcc2200));
  cherry.position.set(1.8, 0.44, -1.0);
  group.add(cherry);

  const ramenBowl = new THREE.Mesh(
    new THREE.CylinderGeometry(0.4, 0.35, 0.3, 20),
    mat(0xcc0000)
  );
  ramenBowl.position.set(-1.8, 0.2, -1.0);
  group.add(ramenBowl);

  const ramenNoodles = new THREE.Mesh(
    new THREE.TorusGeometry(0.2, 0.04, 8, 16),
    mat(0xffd700)
  );
  ramenNoodles.rotation.x = Math.PI / 2;
  ramenNoodles.position.set(-1.8, 0.38, -1.0);
  group.add(ramenNoodles);

  const egg = new THREE.Mesh(new THREE.SphereGeometry(0.12, 12, 10), mat(0xfff8dc));
  egg.position.set(-1.55, 0.42, -0.85);
  group.add(egg);

  const taco = new THREE.Mesh(new THREE.BoxGeometry(0.5, 0.2, 0.3), mat(0xf4a623));
  taco.position.set(0, 0.2, 2.0);
  group.add(taco);
}

/**
 * @param {{
 *   scene: import("three").Scene,
 *   contentGroup: import("three").Group,
 *   camera?: import("three").PerspectiveCamera,
 * }} ctx
 */
function init(ctx) {
  dispose();

  const { scene, contentGroup } = ctx;
  activeCamera = ctx.camera ?? null;
  orbitT = 0;

  scene.background = new THREE.Color(0x3d1a00);
  scene.fog = new THREE.FogExp2(0x3d1a00, 0.08);

  contentGroup.add(new THREE.AmbientLight(0xffe4b5, 2.5));

  const dir = new THREE.DirectionalLight(0xfff8dc, 2.0);
  dir.position.set(0, 12, 4);
  contentGroup.add(dir);

  const floor = new THREE.Mesh(
    new THREE.PlaneGeometry(30, 30),
    mat(0x2c1200, { roughness: 0.95 })
  );
  floor.rotation.x = -Math.PI / 2;
  floor.position.y = 0;
  floor.receiveShadow = true;
  contentGroup.add(floor);

  const legMat = mat(0x6b3a12);
  const legOffsets = [
    [1.8, 1.8],
    [-1.8, 1.8],
    [1.8, -1.8],
    [-1.8, -1.8],
  ];
  legOffsets.forEach(([x, z]) => {
    const leg = new THREE.Mesh(
      new THREE.CylinderGeometry(0.1, 0.1, 1.5, 12),
      legMat
    );
    leg.position.set(x, 0.75, z);
    leg.castShadow = true;
    contentGroup.add(leg);
  });

  const tabletop = new THREE.Mesh(
    new THREE.CylinderGeometry(4, 4, 0.15, 32),
    mat(0x8b4513, { roughness: 0.75 })
  );
  tabletop.position.y = TABLE_TOP_Y;
  tabletop.castShadow = true;
  tabletop.receiveShadow = true;
  contentGroup.add(tabletop);

  const tableLight = new THREE.PointLight(0xffe4b5, 3.5, 14);
  tableLight.position.set(0, TABLE_TOP_Y + 1.2, 0);
  contentGroup.add(tableLight);

  const foodSurface = new THREE.Group();
  foodSurface.position.y = TABLE_TOP_Y + 0.08;
  contentGroup.add(foodSurface);

  addKorean(foodSurface);
  addWestern(foodSurface);
  addChinese(foodSurface);
  addJapanese(foodSurface);
  addExtraDishes(foodSurface);

  if (activeCamera) {
    activeCamera.position.set(0, 5, 6);
    activeCamera.fov = 65;
    activeCamera.lookAt(0, 0, 0);
    activeCamera.updateProjectionMatrix();
  }
}

/**
 * @param {number} _t
 * @param {number} [_delta]
 */
function animate(_t, _delta) {
  orbitT += 0.003;
  if (!activeCamera) return;

  activeCamera.position.x = Math.sin(orbitT) * 6;
  activeCamera.position.y = 5;
  activeCamera.position.z = Math.cos(orbitT) * 6;
  activeCamera.lookAt(0, 0, 0);
}

function dispose() {
  activeCamera = null;
  orbitT = 0;
}

export default { init, animate, dispose };
