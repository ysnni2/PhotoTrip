/**
 * PhotoTrip — nature scene (low-poly forest corridor, path, clouds, sparkles).
 */
import * as THREE from "three";

let _scene     = null;
let _camera    = null;
let _renderer  = null;
let _rafId     = null;
let _particles = null;
let _clouds    = [];

// ─── palette ──────────────────────────────────────────────────────────────────
const C_SKY     = new THREE.Color(0x87ceeb);
const C_GRASS   = 0x4a8c3a;
const C_PATH    = 0xd4c88a;
const C_TREE_DK = 0x2d5c28;
const C_TREE_MD = 0x3a6f32;
const C_TRUNK   = 0x6b3820;
const C_ROCK    = 0x636b7a;

function lmat(color)    { return new THREE.MeshLambertMaterial({ color }); }
function flatmat(color) { return new THREE.MeshLambertMaterial({ color, flatShading: true }); }

// ─── seeded RNG (deterministic layout) ───────────────────────────────────────
function makeRng(seed) {
  let s = seed >>> 0;
  return () => {
    s ^= s << 13; s ^= s >>> 17; s ^= s << 5;
    return (s >>> 0) / 0x100000000;
  };
}

// ─── ground + central path ────────────────────────────────────────────────────
function buildGround() {
  const g = new THREE.Group();

  const grass = new THREE.Mesh(new THREE.PlaneGeometry(60, 55), lmat(C_GRASS));
  grass.rotation.x = -Math.PI / 2;
  g.add(grass);

  const path = new THREE.Mesh(new THREE.PlaneGeometry(3.6, 55), lmat(C_PATH));
  path.rotation.x = -Math.PI / 2;
  path.position.y = 0.005;
  g.add(path);

  return g;
}

// ─── low-poly conifer: trunk + 3 stacked cones ───────────────────────────────
function buildTree() {
  const g = new THREE.Group();

  const trunk = new THREE.Mesh(
    new THREE.BoxGeometry(0.28, 1.2, 0.28),
    lmat(C_TRUNK)
  );
  trunk.position.y = 0.6;
  g.add(trunk);

  // [radius, height, centerY, color]
  const tiers = [
    [1.50, 2.2, 1.90, C_TREE_DK],
    [1.10, 1.8, 3.10, C_TREE_MD],
    [0.72, 1.5, 4.10, C_TREE_MD],
  ];

  for (const [r, h, y, c] of tiers) {
    const cone = new THREE.Mesh(new THREE.ConeGeometry(r, h, 6), flatmat(c));
    cone.position.y = y;
    g.add(cone);
  }

  return g;
}

// ─── cloud: cluster of overlapping spheres ────────────────────────────────────
function buildCloud(x, y, z, sc) {
  const g = new THREE.Group();
  const m = lmat(0xf2f2f2);

  const blobs = [
    [ 0.00,  0.00,  0.00, 1.00],
    [-1.35, -0.20,  0.00, 0.80],
    [ 1.35, -0.20,  0.00, 0.85],
    [ 0.50,  0.45,  0.00, 0.70],
    [-0.50,  0.40,  0.00, 0.65],
    [ 0.00, -0.28,  0.52, 0.68],
    [ 0.80,  0.10, -0.30, 0.55],
  ];

  for (const [bx, by, bz, br] of blobs) {
    const s = new THREE.Mesh(new THREE.SphereGeometry(br * sc, 8, 6), m);
    s.position.set(bx * sc, by * sc, bz * sc);
    g.add(s);
  }

  g.position.set(x, y, z);
  return g;
}

// ─── rock: flattened dodecahedron ─────────────────────────────────────────────
function buildRock(x, z, sc, rotY) {
  const rock = new THREE.Mesh(
    new THREE.DodecahedronGeometry(sc * 0.55, 0),
    flatmat(C_ROCK)
  );
  rock.scale.set(1.0, 0.55, 1.1);
  rock.rotation.y = rotY;
  rock.position.set(x, sc * 0.18, z);
  return rock;
}

// ─── sky sparkle particles (white + yellow-green) ────────────────────────────
function buildParticles(rng) {
  const count     = 320;
  const positions = new Float32Array(count * 3);
  const colors    = new Float32Array(count * 3);

  for (let i = 0; i < count; i++) {
    positions[i * 3]     = (rng() - 0.5) * 38;
    positions[i * 3 + 1] = 4 + rng() * 11;
    positions[i * 3 + 2] = -22 + rng() * 34;

    if (rng() > 0.62) {
      // yellow-green sparkle
      colors[i * 3]     = 0.75 + rng() * 0.25;
      colors[i * 3 + 1] = 0.85 + rng() * 0.15;
      colors[i * 3 + 2] = 0.05;
    } else {
      // white
      const v = 0.88 + rng() * 0.12;
      colors[i * 3] = colors[i * 3 + 1] = colors[i * 3 + 2] = v;
    }
  }

  const geo = new THREE.BufferGeometry();
  geo.setAttribute("position", new THREE.BufferAttribute(positions, 3));
  geo.setAttribute("color",    new THREE.BufferAttribute(colors, 3));

  return new THREE.Points(geo, new THREE.PointsMaterial({
    size: 0.20, vertexColors: true,
    transparent: true, opacity: 0.88, sizeAttenuation: true,
  }));
}

// ─── public API ───────────────────────────────────────────────────────────────
function init(canvas) {
  dispose();

  const rng = makeRng(42);

  _scene            = new THREE.Scene();
  _scene.background = C_SKY;
  _scene.fog        = new THREE.Fog(C_SKY, 10, 34);

  const w = canvas.clientWidth  || 800;
  const h = canvas.clientHeight || 450;

  _camera = new THREE.PerspectiveCamera(65, w / h, 0.1, 60);
  _camera.position.set(0, 2.2, 10);
  _camera.lookAt(0, 1.5, 0);

  _renderer = new THREE.WebGLRenderer({ canvas, antialias: true });
  _renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  _renderer.setSize(w, h, false);

  // Lighting
  _scene.add(new THREE.AmbientLight(0xc8e8c0, 2.0));
  const sun = new THREE.DirectionalLight(0xfff8e0, 2.8);
  sun.position.set(8, 18, 12);
  _scene.add(sun);

  // Ground + path
  _scene.add(buildGround());

  // ── Close hero trees (camera-facing, very large) ─────────────────────────────
  const heroTrees = [
    [-4.0,  8.5, 1.85], [-8.5,  7.0, 1.70],
    [-5.8,  7.8, 1.55], [-12.0, 6.5, 1.80],
    [ 4.0,  8.5, 1.85], [ 8.5,  7.0, 1.70],
    [ 5.8,  7.8, 1.55], [ 12.0, 6.5, 1.80],
  ];
  for (const [x, z, sc] of heroTrees) {
    const t = buildTree(); t.scale.setScalar(sc); t.position.set(x, 0, z);
    _scene.add(t);
  }

  // ── Background forest: 5 rows per side ───────────────────────────────────────
  for (let row = 0; row < 5; row++) {
    const baseX = 3.6 + row * 2.6;
    const baseSc = 1.05 - row * 0.04;
    for (let col = 0; col < 10; col++) {
      const z   = -14 + col * 2.6 + rng() * 1.6 - 0.8;
      const xOff = rng() * 1.4 - 0.7;
      const sc  = baseSc * (0.72 + rng() * 0.48);

      const tL = buildTree(); tL.scale.setScalar(sc); tL.position.set(-(baseX + xOff), 0, z);
      const tR = buildTree(); tR.scale.setScalar(sc); tR.position.set( (baseX + xOff), 0, z);
      _scene.add(tL, tR);
    }
  }

  // ── Clouds ────────────────────────────────────────────────────────────────────
  _clouds = [
    buildCloud(-5.0,  9.0, -5.0, 1.00),
    buildCloud( 4.0,  8.2, -9.5, 0.85),
    buildCloud( 0.5, 10.5,  2.0, 0.72),
  ];
  _clouds.forEach((c) => _scene.add(c));

  // ── Rocks scattered on path and verges ───────────────────────────────────────
  const rocks = [
    [ 0.8,  2.2, 0.45, 0.30], [-0.6,  0.3, 0.40, 1.10],
    [ 1.3, -2.0, 0.38, 0.70], [-1.1, -3.5, 0.52, 2.00],
    [ 0.4, -5.2, 0.42, 0.40], [-0.9,  4.2, 0.37, 1.80],
    [ 1.6, -6.8, 0.50, 0.90], [-1.4, -7.6, 0.38, 0.20],
    [ 2.1,  1.2, 0.35, 1.50], [-2.3,  3.2, 0.46, 0.60],
    [ 0.6, -1.1, 0.32, 2.30], [ 1.8, -4.5, 0.44, 1.70],
  ];
  for (const [x, z, sc, ry] of rocks) _scene.add(buildRock(x, z, sc, ry));

  // ── Particles ─────────────────────────────────────────────────────────────────
  _particles = buildParticles(rng);
  _scene.add(_particles);
}

function animate() {
  _rafId = requestAnimationFrame(animate);

  const t = performance.now() * 0.001;

  // Gentle camera sway
  _camera.position.x = Math.sin(t * 0.18) * 0.35;
  _camera.position.y = 2.2 + Math.sin(t * 0.27) * 0.08;
  _camera.lookAt(0, 1.5, 0);

  // Particles drift down and sway
  if (_particles) {
    const pos = _particles.geometry.attributes.position;
    for (let i = 0; i < pos.count; i++) {
      let y = pos.getY(i) - 0.004;
      let x = pos.getX(i) + Math.sin(t * 1.4 + i * 0.25) * 0.003;
      if (y < 2.5) { y = 13 + Math.random() * 3; x = (Math.random() - 0.5) * 38; }
      pos.setX(i, x);
      pos.setY(i, y);
    }
    pos.needsUpdate = true;
  }

  // Clouds drift sideways
  _clouds.forEach((cloud, i) => {
    cloud.position.x += 0.0018 * (i % 2 === 0 ? 1 : -0.7);
    if (cloud.position.x >  18) cloud.position.x = -18;
    if (cloud.position.x < -18) cloud.position.x =  18;
  });

  _renderer.render(_scene, _camera);
}

function dispose() {
  if (_rafId !== null) { cancelAnimationFrame(_rafId); _rafId = null; }

  if (_scene) {
    _scene.traverse((obj) => {
      if (obj.geometry) obj.geometry.dispose();
      if (obj.material) {
        if (Array.isArray(obj.material)) obj.material.forEach((m) => m.dispose());
        else obj.material.dispose();
      }
    });
    _scene = null;
  }

  if (_renderer) { _renderer.dispose(); _renderer = null; }

  _camera    = null;
  _particles = null;
  _clouds    = [];
}

export default { init, animate, dispose };
