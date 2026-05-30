/**
 * PhotoTrip — culture scene (warm museum gallery).
 */
import * as THREE from "three";

let _scene    = null;
let _camera   = null;
let _renderer = null;
let _rafId    = null;

// ─── palette ──────────────────────────────────────────────────────────────────
const C_BG       = new THREE.Color(0xf5f0e8);
const C_WALL     = 0xd4c8ac;
const C_FLOOR    = 0xe8dcc8;
const C_CEIL     = 0xcfc3a8;
const C_COLUMN   = 0xf0ebe0;
const C_FRAME    = 0xb8922a;
const C_PEDESTAL = 0xd4c8a8;
const C_SCULPT   = 0xc8a860;
const C_ART_BRN  = 0x5c3820;
const C_ART_BLU  = 0x3a5878;
const C_ART_RED  = 0x6b2020;

function lmat(color) { return new THREE.MeshLambertMaterial({ color }); }
function bmat(color) { return new THREE.MeshBasicMaterial({ color }); }

// ─── room ─────────────────────────────────────────────────────────────────────
function buildRoom() {
  const g = new THREE.Group();

  // Floor
  const floor = new THREE.Mesh(new THREE.PlaneGeometry(14, 32), lmat(C_FLOOR));
  floor.rotation.x = -Math.PI / 2;
  g.add(floor);

  // Central walkway (slightly lighter strip)
  const walk = new THREE.Mesh(new THREE.PlaneGeometry(4, 32), lmat(0xf0e8d0));
  walk.rotation.x = -Math.PI / 2;
  walk.position.y = 0.002;
  g.add(walk);

  // Ceiling
  const ceil = new THREE.Mesh(new THREE.PlaneGeometry(14, 32), lmat(C_CEIL));
  ceil.rotation.x = Math.PI / 2;
  ceil.position.y = 4.2;
  g.add(ceil);

  // Left wall
  const wallL = new THREE.Mesh(new THREE.PlaneGeometry(32, 4.2), lmat(C_WALL));
  wallL.rotation.y = Math.PI / 2;
  wallL.position.set(-7, 2.1, 0);
  g.add(wallL);

  // Right wall
  const wallR = new THREE.Mesh(new THREE.PlaneGeometry(32, 4.2), lmat(C_WALL));
  wallR.rotation.y = -Math.PI / 2;
  wallR.position.set(7, 2.1, 0);
  g.add(wallR);

  // Back wall
  const wallB = new THREE.Mesh(new THREE.PlaneGeometry(14, 4.2), lmat(C_WALL));
  wallB.position.set(0, 2.1, -13);
  g.add(wallB);

  return g;
}

// ─── column ───────────────────────────────────────────────────────────────────
function buildColumn(x, z, sc = 1) {
  const g = new THREE.Group();
  const m = lmat(C_COLUMN);

  const base = new THREE.Mesh(new THREE.BoxGeometry(0.6 * sc, 0.15 * sc, 0.6 * sc), m);
  base.position.y = 0.075 * sc;

  const shaft = new THREE.Mesh(new THREE.CylinderGeometry(0.18 * sc, 0.20 * sc, 3.8 * sc, 14), m);
  shaft.position.y = (0.15 + 1.9) * sc;

  const capital = new THREE.Mesh(new THREE.CylinderGeometry(0.32 * sc, 0.22 * sc, 0.22 * sc, 14), m);
  capital.position.y = (0.15 + 3.8 + 0.11) * sc;

  const abacus = new THREE.Mesh(new THREE.BoxGeometry(0.72 * sc, 0.12 * sc, 0.72 * sc), m);
  abacus.position.y = (0.15 + 3.8 + 0.22 + 0.06) * sc;

  g.add(base, shaft, capital, abacus);
  g.position.set(x, 0, z);
  return g;
}

// ─── framed painting ──────────────────────────────────────────────────────────
function buildPainting(cx, cy, cz, rotY, w, h, artColor) {
  const g  = new THREE.Group();
  const fm = lmat(C_FRAME);
  const ft = 0.1;
  const fd = 0.08;

  const topBar = new THREE.Mesh(new THREE.BoxGeometry(w + ft * 2, ft, fd), fm);
  topBar.position.y = h / 2 + ft / 2;
  const botBar = new THREE.Mesh(new THREE.BoxGeometry(w + ft * 2, ft, fd), fm);
  botBar.position.y = -(h / 2 + ft / 2);
  const lBar = new THREE.Mesh(new THREE.BoxGeometry(ft, h, fd), fm);
  lBar.position.x = -(w / 2 + ft / 2);
  const rBar = new THREE.Mesh(new THREE.BoxGeometry(ft, h, fd), fm);
  rBar.position.x = w / 2 + ft / 2;

  const art = new THREE.Mesh(new THREE.PlaneGeometry(w, h), lmat(artColor));
  art.position.z = fd / 2 + 0.003;

  g.add(topBar, botBar, lBar, rBar, art);
  g.position.set(cx, cy, cz);
  g.rotation.y = rotY;
  return g;
}

// ─── vase sculpture ───────────────────────────────────────────────────────────
function vasePoints() {
  return [
    new THREE.Vector2(0.00, 0.00),
    new THREE.Vector2(0.10, 0.04),
    new THREE.Vector2(0.22, 0.20),
    new THREE.Vector2(0.28, 0.42),
    new THREE.Vector2(0.28, 0.62),
    new THREE.Vector2(0.22, 0.78),
    new THREE.Vector2(0.12, 0.90),
    new THREE.Vector2(0.07, 1.00),
    new THREE.Vector2(0.09, 1.06),
    new THREE.Vector2(0.07, 1.12),
  ];
}

function buildSculpture(x, z, sc) {
  const g = new THREE.Group();

  const pedH = 0.58;
  const ped = new THREE.Mesh(new THREE.BoxGeometry(0.55, pedH, 0.55), lmat(C_PEDESTAL));
  ped.position.y = pedH / 2;

  const vase = new THREE.Mesh(new THREE.LatheGeometry(vasePoints(), 24), lmat(C_SCULPT));
  vase.scale.setScalar(0.45);
  vase.position.y = pedH;

  g.add(ped, vase);
  g.scale.setScalar(sc);
  g.position.set(x, 0, z);
  return g;
}

// ─── ceiling glow disc ────────────────────────────────────────────────────────
function buildCeilGlow() {
  const disc = new THREE.Mesh(
    new THREE.CircleGeometry(0.7, 32),
    bmat(0xfff8c0)
  );
  disc.rotation.x = Math.PI / 2;
  disc.position.set(0, 4.18, 0);
  return disc;
}

// ─── public API ───────────────────────────────────────────────────────────────
function init(canvas) {
  dispose();

  _scene            = new THREE.Scene();
  _scene.background = C_BG;

  const w = canvas.clientWidth  || 800;
  const h = canvas.clientHeight || 450;

  _camera = new THREE.PerspectiveCamera(62, w / h, 0.1, 60);
  _camera.position.set(0, 1.85, 9.5);
  _camera.lookAt(0, 1.6, 0);

  _renderer = new THREE.WebGLRenderer({ canvas, antialias: true });
  _renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  _renderer.setSize(w, h, false);

  // ── Lighting ─────────────────────────────────────────────────────────────────
  _scene.add(new THREE.AmbientLight(0xfff5e0, 1.8));

  const spot = new THREE.PointLight(0xfff0a0, 5, 24);
  spot.position.set(0, 4.0, 0);
  _scene.add(spot);

  const midPt = new THREE.PointLight(0xffe8a0, 2.5, 16);
  midPt.position.set(0, 3.8, -5);
  _scene.add(midPt);

  // Painting accent lights
  const paintL = new THREE.PointLight(0xfff0d0, 1.5, 8);
  paintL.position.set(-6.2, 2.8, 3.0);
  _scene.add(paintL);
  const paintR = new THREE.PointLight(0xfff0d0, 1.5, 8);
  paintR.position.set(6.2, 2.8, 3.0);
  _scene.add(paintR);

  // ── Scene objects ─────────────────────────────────────────────────────────────
  _scene.add(buildRoom());
  _scene.add(buildCeilGlow());

  // Columns — 3 pairs: front (large), mid, back
  const colPairs = [
    { z: 5.5, sc: 1.0 },
    { z: 1.2, sc: 1.0 },
    { z: -3.0, sc: 1.0 },
  ];
  for (const { z, sc } of colPairs) {
    _scene.add(buildColumn(-4.0, z, sc));
    _scene.add(buildColumn( 4.0, z, sc));
  }

  // Left wall paintings (rotY = +π/2, facing right/inward)
  // 3 paintings: large brown, medium blue, small red
  _scene.add(buildPainting(-6.96, 2.1,  4.0, Math.PI / 2, 1.30, 0.96, C_ART_BRN));
  _scene.add(buildPainting(-6.96, 2.1,  0.2, Math.PI / 2, 0.90, 0.75, C_ART_BLU));
  _scene.add(buildPainting(-6.96, 2.1, -3.8, Math.PI / 2, 0.78, 0.65, C_ART_RED));

  // Right wall paintings (rotY = -π/2, facing left/inward)
  _scene.add(buildPainting( 6.96, 2.1,  0.2, -Math.PI / 2, 0.90, 0.75, C_ART_BLU));
  _scene.add(buildPainting( 6.96, 2.1,  4.0, -Math.PI / 2, 1.30, 0.96, C_ART_BRN));
  _scene.add(buildPainting( 6.96, 2.1, -3.8, -Math.PI / 2, 0.78, 0.65, C_ART_RED));

  // Central sculptures — front to back
  _scene.add(buildSculpture(0,  3.8, 1.00));
  _scene.add(buildSculpture(0,  0.8, 0.82));
  _scene.add(buildSculpture(0, -2.2, 0.65));
}

function animate() {
  _rafId = requestAnimationFrame(animate);

  const t = performance.now() * 0.001;
  _camera.position.x = Math.sin(t * 0.22) * 0.40;
  _camera.lookAt(0, 1.6, 0);

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
  _camera = null;
}

export default { init, animate, dispose };
