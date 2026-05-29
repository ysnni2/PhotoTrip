/**
 * PhotoTrip — city night street view (eye-level, buildings along avenue).
 */
import * as THREE from "https://esm.sh/three@0.160.0";

const BUILDING_COLOR = 0x253050;
const GROUND_COLOR = 0x1a1a2e;
const ROAD_COLOR = 0x252538;
const WIN_COLOR = 0xffff99;

const LEFT_COLS = [-4, -8, -12];
const RIGHT_COLS = [4, 8, 12];
const HEIGHT_SCALE = [1, 0.88, 0.74];

/**
 * @param {{
 *   scene: import("three").Scene,
 *   contentGroup: import("three").Group,
 *   randomRange: (min: number, max: number) => number,
 * }} ctx
 * @returns {{ sceneAnimate: (t: number) => void, applyCamera: (cam: import("three").PerspectiveCamera) => void }}
 */
export function buildCityNightScene({ scene, contentGroup, randomRange }) {
  const PI = Math.PI;
  scene.background = new THREE.Color(0x080c18);
  scene.fog = new THREE.Fog(0x080c18, 35, 70);

  const ground = new THREE.Mesh(
    new THREE.PlaneGeometry(60, 60),
    new THREE.MeshLambertMaterial({ color: GROUND_COLOR, transparent: false, opacity: 1 })
  );
  ground.rotation.x = -PI / 2;
  ground.position.y = 0;
  contentGroup.add(ground);

  const road = new THREE.Mesh(
    new THREE.PlaneGeometry(4, 60),
    new THREE.MeshLambertMaterial({ color: ROAD_COLOR })
  );
  road.rotation.x = -PI / 2;
  road.position.set(0, 0.01, 0);
  contentGroup.add(road);

  for (let z = -28; z <= 10; z += 3.5) {
    [-0.55, 0.55].forEach((x) => {
      const dash = new THREE.Mesh(
        new THREE.BoxGeometry(0.12, 0.02, 1.6),
        new THREE.MeshBasicMaterial({ color: 0xffffff })
      );
      dash.position.set(x, 0.025, z);
      contentGroup.add(dash);
    });
  }

  const winMaterial = new THREE.MeshBasicMaterial({
    color: WIN_COLOR,
    emissive: WIN_COLOR,
    emissiveIntensity: 1,
  });

  function pickZSlots() {
    const all = [-5, -10, -15, -20, -25];
    return Math.random() > 0.45 ? all : all.slice(0, 4);
  }

  function addBuilding(x, z, colIndex) {
    const w = randomRange(1.5, 3);
    const scale = HEIGHT_SCALE[colIndex] ?? 1;
    const h = randomRange(5, 15) * scale;
    const d = randomRange(1.5, 2);

    const group = new THREE.Group();

    const body = new THREE.Mesh(
      new THREE.BoxGeometry(w, h, d),
      new THREE.MeshLambertMaterial({
        color: BUILDING_COLOR,
        transparent: false,
        opacity: 1,
      })
    );
    body.position.y = h / 2;
    group.add(body);

    const rows = Math.max(3, Math.floor(h / 2));
    const cols = Math.max(2, Math.floor(w / 0.55));
    for (let r = 0; r < rows; r++) {
      for (let c = 0; c < cols; c++) {
        if (Math.random() > 0.72) continue;
        const win = new THREE.Mesh(
          new THREE.BoxGeometry(0.25, 0.25, 0.05),
          winMaterial
        );
        win.position.set(
          -w / 2 + 0.4 + c * 0.55,
          1.2 + r * 1.85,
          d / 2 + 0.026
        );
        group.add(win);
      }
    }

    group.position.set(x, 0, z);
    contentGroup.add(group);
  }

  LEFT_COLS.forEach((x, colIndex) => {
    for (const z of pickZSlots()) {
      addBuilding(x, z + randomRange(-0.6, 0.6), colIndex);
    }
  });
  RIGHT_COLS.forEach((x, colIndex) => {
    for (const z of pickZSlots()) {
      addBuilding(x, z + randomRange(-0.6, 0.6), colIndex);
    }
  });

  for (let z = -26; z <= 8; z += 8) {
    [-2.4, 2.4].forEach((x) => {
      const pole = new THREE.Mesh(
        new THREE.CylinderGeometry(0.05, 0.07, 2.8, 6),
        new THREE.MeshLambertMaterial({ color: 0x444455 })
      );
      pole.position.set(x, 1.4, z);
      contentGroup.add(pole);

      const street = new THREE.PointLight(0xff9944, 2.0, 16);
      street.position.set(x, 2.8, z);
      contentGroup.add(street);
    });
  }

  contentGroup.add(new THREE.AmbientLight(0xffffff, 0.5));

  const rim = new THREE.DirectionalLight(0x4466ff, 0.5);
  rim.position.set(0, 12, -32);
  contentGroup.add(rim);

  function createCar(color) {
    const group = new THREE.Group();
    const bodyMat = new THREE.MeshLambertMaterial({ color });

    const lower = new THREE.Mesh(
      new THREE.BoxGeometry(1.2, 0.3, 2.2),
      bodyMat
    );
    lower.position.y = 0.15;
    group.add(lower);

    const cabin = new THREE.Mesh(
      new THREE.BoxGeometry(0.8, 0.3, 1.2),
      bodyMat
    );
    cabin.position.set(0, 0.45, 0.25);
    group.add(cabin);

    const headMat = new THREE.MeshBasicMaterial({ color: 0xffffff });
    const tailMat = new THREE.MeshBasicMaterial({ color: 0xff2200 });
    [-0.35, 0.35].forEach((lx) => {
      const head = new THREE.Mesh(
        new THREE.BoxGeometry(0.15, 0.1, 0.05),
        headMat
      );
      head.position.set(lx, 0.12, -1.12);
      group.add(head);

      const tail = new THREE.Mesh(
        new THREE.BoxGeometry(0.15, 0.1, 0.05),
        tailMat
      );
      tail.position.set(lx, 0.12, 1.12);
      group.add(tail);
    });

    return group;
  }

  const cars = [];
  const carColors = [0xcc3333, 0x3366cc];
  [-0.9, 0.9].forEach((x, i) => {
    const car = createCar(carColors[i]);
    car.position.set(x, 0, 6 - i * 4);
    car.userData = { speed: 0.018 + i * 0.004 };
    contentGroup.add(car);
    cars.push(car);
  });

  const sceneAnimate = () => {
    cars.forEach((car) => {
      car.position.z -= car.userData.speed;
      if (car.position.z < -28) car.position.z = 10;
    });
  };

  const applyCamera = (cam) => {
    cam.position.set(0, 3, 12);
    cam.fov = 75;
    cam.lookAt(0, 5, 0);
    cam.updateProjectionMatrix();
  };

  return { sceneAnimate, applyCamera };
}
