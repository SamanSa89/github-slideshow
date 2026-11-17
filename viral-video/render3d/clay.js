// Claymation / stop-motion look prototype (hook scene of the Luftraum episode).
// window.renderAt(t) -> JPEG data URL. Time is quantised to 12 fps ("on twos") with per-step jitter.
import * as THREE from 'three';
import { RoomEnvironment } from 'three/addons/environments/RoomEnvironment.js';
import { mergeVertices } from 'three/addons/utils/BufferGeometryUtils.js';

const P = new URLSearchParams(location.search);
const W = +(P.get('w') || 540), H = +(P.get('h') || 960);
const r = new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true });
r.setPixelRatio(1); r.setSize(W, H); r.outputColorSpace = THREE.SRGBColorSpace;
r.toneMapping = THREE.ACESFilmicToneMapping; r.toneMappingExposure = 1.0;
r.shadowMap.enabled = true; r.shadowMap.type = THREE.PCFSoftShadowMap;
document.body.appendChild(r.domElement);
const scene = new THREE.Scene(); scene.background = new THREE.Color(0xe9d2b4);
scene.environment = new THREE.PMREMGenerator(r).fromScene(new RoomEnvironment(), 0.04).texture; scene.environmentIntensity = 0.25;
const cam = new THREE.PerspectiveCamera(32, W / H, 0.1, 100);

// ---- deterministic noise
let seed = 3; const rnd = () => (seed = (seed * 16807) % 2147483647) / 2147483647;
const hash = (x, y, z) => { const s = Math.sin(x * 127.1 + y * 311.7 + z * 74.7) * 43758.5453; return s - Math.floor(s); };
function vnoise(x, y, z) {
  const xi = Math.floor(x), yi = Math.floor(y), zi = Math.floor(z), xf = x - xi, yf = y - yi, zf = z - zi;
  const f = t => t * t * (3 - 2 * t), u = f(xf), v = f(yf), w = f(zf); let o = 0;
  for (const dx of [0, 1]) for (const dy of [0, 1]) for (const dz of [0, 1])
    o += hash(xi + dx, yi + dy, zi + dz) * (dx ? u : 1 - u) * (dy ? v : 1 - v) * (dz ? w : 1 - w);
  return o;
}
// ---- clay bump texture: fingerprints + tool marks
function clayBump() {
  const c = document.createElement('canvas'); c.width = c.height = 512; const g = c.getContext('2d');
  g.fillStyle = '#808080'; g.fillRect(0, 0, 512, 512);
  for (let i = 0; i < 26; i++) {           // fingerprint whorls
    const x = rnd() * 512, y = rnd() * 512, R = 18 + rnd() * 34;
    for (let k = 3; k < R; k += 2.4) { g.strokeStyle = `rgba(${rnd() > .5 ? 255 : 0},${0},${0},0.06)`; g.strokeStyle = rnd() > .5 ? 'rgba(255,255,255,0.07)' : 'rgba(0,0,0,0.07)'; g.lineWidth = 1.1; g.beginPath(); g.ellipse(x, y, k, k * 0.8, rnd(), 0, Math.PI * 2); g.stroke(); }
  }
  for (let i = 0; i < 60; i++) { g.strokeStyle = 'rgba(0,0,0,0.08)'; g.lineWidth = 1 + rnd() * 2; g.beginPath(); const x = rnd() * 512, y = rnd() * 512; g.moveTo(x, y); g.quadraticCurveTo(x + rnd() * 60 - 30, y + rnd() * 60 - 30, x + rnd() * 90 - 45, y + rnd() * 90 - 45); g.stroke(); }
  const t = new THREE.CanvasTexture(c); t.wrapS = t.wrapT = THREE.RepeatWrapping; t.repeat.set(1.2, 1.2); return t;
}
const BUMP = clayBump();
const clay = (color, rough = 0.82) => new THREE.MeshStandardMaterial({ color, roughness: rough, metalness: 0, bumpMap: BUMP, bumpScale: 6.0 });
// lumpy (hand-made) geometry
function lumpy(geo, amp = 0.05, freq = 3.2) {
  geo = mergeVertices(geo); const p = geo.attributes.position, n = new THREE.Vector3();
  geo.computeVertexNormals(); const nn = geo.attributes.normal;
  for (let i = 0; i < p.count; i++) {
    n.set(nn.getX(i), nn.getY(i), nn.getZ(i));
    const d = (vnoise(p.getX(i) * freq, p.getY(i) * freq, p.getZ(i) * freq) - 0.5) * 2 * amp;
    p.setXYZ(i, p.getX(i) + n.x * d, p.getY(i) + n.y * d, p.getZ(i) + n.z * d);
  }
  geo.computeVertexNormals(); return geo;
}
const M = (geo, mat, pos = [0, 0, 0], parent = scene) => { const m = new THREE.Mesh(geo, mat); m.position.set(...pos); m.castShadow = m.receiveShadow = true; parent.add(m); return m; };

// ---- set: seamless paper backdrop + table
M(new THREE.PlaneGeometry(14, 10), new THREE.MeshStandardMaterial({ color: 0xead2b0, roughness: 1 }), [0, 4, -3]);
M(new THREE.PlaneGeometry(14, 10), new THREE.MeshStandardMaterial({ color: 0xe6cfae, roughness: 1 }), [0, 0, 0]).rotation.x = -Math.PI / 2;
const key = new THREE.DirectionalLight(0xfff0dc, 2.6); key.position.set(-3, 6, 4); key.castShadow = true; key.shadow.mapSize.set(2048, 2048); key.shadow.radius = 6; key.shadow.camera.left = -4; key.shadow.camera.right = 4; key.shadow.camera.top = 6; key.shadow.camera.bottom = -2; scene.add(key);
scene.add(new THREE.HemisphereLight(0xfff4e6, 0xb89878, 0.9));
const rim = new THREE.DirectionalLight(0xffe2c0, 0.8); rim.position.set(3, 4, -3); scene.add(rim);

// ---- sea (blue clay slab) + Japan island
M(lumpy(new THREE.BoxGeometry(3.6, 0.18, 2.4, 40, 4, 30), 0.03, 2.5), clay(0x5c8fb8, 0.7), [0, 0.09, 0]);
const isl = new THREE.Group(); scene.add(isl);
const islandShape = new THREE.Shape(); [[-1.3, -0.35], [-0.7, -0.6], [0.2, -0.35], [1.2, 0.2], [1.45, 0.55], [1.0, 0.6], [0.1, 0.15], [-0.6, 0.05], [-1.35, -0.1]].forEach(([x, y], i) => i ? islandShape.lineTo(x, y) : islandShape.moveTo(x, y));
const ig = lumpy(new THREE.ExtrudeGeometry(islandShape, { depth: 0.16, bevelEnabled: true, bevelThickness: 0.08, bevelSize: 0.08, bevelSegments: 4, curveSegments: 24 }), 0.035, 3);
const island = M(ig, clay(0x8db36b), [0, 0.2, 0], isl); island.rotation.x = -Math.PI / 2; island.scale.set(0.9, 0.9, 1);
for (const [x, z, h] of [[-0.6, 0.15, 0.22], [0.3, -0.05, 0.28], [0.8, -0.3, 0.2]]) M(lumpy(new THREE.ConeGeometry(0.16, h, 16, 4), 0.02, 6), clay(0x6f9a55), [x, 0.42 + h / 2 - 0.05, z]);
for (const [x, z] of [[-0.2, 0.25], [0.05, 0.3]]) { M(lumpy(new THREE.BoxGeometry(0.1, 0.09, 0.1), 0.01, 9), clay(0xf2ede4), [x, 0.46, z]); M(lumpy(new THREE.ConeGeometry(0.09, 0.07, 4), 0.01, 9), clay(0xc1543e), [x, 0.535, z]).rotation.y = Math.PI / 4; }
// little flag on the island
M(new THREE.CylinderGeometry(0.008, 0.008, 0.32), clay(0x8a6a4a), [0.55, 0.57, 0.15]);
const flag = M(lumpy(new THREE.BoxGeometry(0.2, 0.13, 0.012, 8, 6, 1), 0.006, 8), clay(0xf7f3ec), [0.65, 0.66, 0.15]);
M(new THREE.CylinderGeometry(0.035, 0.035, 0.014, 20), clay(0xd2302f), [0.65, 0.66, 0.158]).rotation.x = Math.PI / 2;

// ---- two red clay jets on a visible wire (stop-motion rig look)
function jet() {
  const g = new THREE.Group(); const red = clay(0xc8322f), dark = clay(0x6b1f1d);
  const body = M(lumpy(new THREE.CapsuleGeometry(0.06, 0.42, 6, 16), 0.008, 10), red, [0, 0, 0], g); body.rotation.z = Math.PI / 2;
  const nose = M(lumpy(new THREE.ConeGeometry(0.06, 0.14, 16), 0.006, 10), red, [0.3, 0, 0], g); nose.rotation.z = -Math.PI / 2;
  const wing = M(lumpy(new THREE.BoxGeometry(0.16, 0.025, 0.6, 6, 2, 12), 0.008, 8), red, [-0.02, 0, 0], g); wing.rotation.y = 0.0;
  M(lumpy(new THREE.BoxGeometry(0.1, 0.02, 0.24), 0.006, 9), red, [-0.22, 0.02, 0], g);
  M(lumpy(new THREE.BoxGeometry(0.1, 0.13, 0.02), 0.006, 9), red, [-0.23, 0.08, 0], g);
  M(new THREE.SphereGeometry(0.035, 12, 8), clay(0x2b3a4a, 0.4), [0.14, 0.05, 0], g).scale.set(1.6, 0.8, 1);
  return g;
}
const jets = [jet(), jet()]; jets.forEach(j => { j.scale.setScalar(0.62); scene.add(j); });
const wireMat = new THREE.MeshBasicMaterial({ color: 0x7a6d60 });
const wires = jets.map(() => { const w = new THREE.Mesh(new THREE.CylinderGeometry(0.004, 0.004, 1, 6), wireMat); scene.add(w); return w; });

// ---- clay clock "4:07"
const clock = new THREE.Group(); clock.position.set(-0.75, 2.35, -0.8); scene.add(clock);
M(lumpy(new THREE.CylinderGeometry(0.42, 0.42, 0.1, 48, 1), 0.012, 6), clay(0xf4ead8), [0, 0, 0], clock).rotation.x = Math.PI / 2;
M(lumpy(new THREE.TorusGeometry(0.42, 0.05, 12, 48), 0.01, 7), clay(0x2f3b52), [0, 0, 0], clock);
for (let i = 0; i < 12; i++) { const a = i / 12 * Math.PI * 2; M(new THREE.SphereGeometry(0.022, 10, 8), clay(0x2f3b52), [Math.sin(a) * 0.33, Math.cos(a) * 0.33, 0.06], clock); }
const hourH = new THREE.Group(), minH = new THREE.Group(); clock.add(hourH, minH);
M(lumpy(new THREE.BoxGeometry(0.035, 0.2, 0.025), 0.004, 9), clay(0x2f3b52), [0, 0.1, 0.07], hourH);
M(lumpy(new THREE.BoxGeometry(0.025, 0.3, 0.025), 0.004, 9), clay(0xc8322f), [0, 0.15, 0.09], minH);
M(new THREE.SphereGeometry(0.035, 12, 8), clay(0x2f3b52), [0, 0, 0.1], clock);
M(new THREE.CylinderGeometry(0.01, 0.01, 2.0), wireMat, [-0.75, 3.75, -0.8]);

// ---- animation (stop motion: 12 fps steps + small per-step jitter on everything animated)
window.renderAt = (tReal) => {
  const t = Math.floor(tReal * 12) / 12, step = Math.floor(tReal * 12);
  const j = (k, a = 0.006) => (hash(step, k, 7.1) - 0.5) * 2 * a;
  // clock hands sweep to 4:07 then settle
  const k = Math.min(1, t / 1.6), e = 1 - Math.pow(1 - k, 3);
  const minA = -(7 / 60) * Math.PI * 2 * e - Math.PI * 2 * (1 - e) * 0.6, hourA = -((4 + 7 / 60) / 12) * Math.PI * 2 * e;
  minH.rotation.z = minA + j(1, 0.02); hourH.rotation.z = hourA + j(2, 0.02);
  clock.rotation.z = Math.sin(t * 2) * 0.02 + j(3, 0.01);
  // jets fly in over the island and keep going (route continues)
  jets.forEach((g, i) => {
    const s = Math.max(0, t - 0.6 - i * 0.35), u = s / 4.0;
    const x = 2.0 - u * 4.0, z = -0.3 + i * 0.45 + Math.sin(u * 3) * 0.15, y = 1.35 + i * 0.14 + Math.sin(u * 6) * 0.04;
    g.position.set(x + j(10 + i), y + j(20 + i), z + j(30 + i)); g.rotation.set(0.15 + j(40 + i, 0.03), Math.PI + 0.25, -0.12 + Math.sin(u * 5) * 0.08);
    const w = wires[i]; w.position.set(g.position.x, (g.position.y + 4) / 2, g.position.z); w.scale.y = 4 - g.position.y;
  });
  flag.rotation.y = Math.sin(t * 6) * 0.15;
  // handheld-free locked-off camera with tiny animator-nudge between steps
  cam.position.set(0.1 + j(50, 0.004), 2.6 + j(51, 0.004), 7.2); cam.lookAt(0, 1.05, 0);
  r.render(scene, cam);
  return r.domElement.toDataURL('image/jpeg', 0.92);
};
window.READY = true;
