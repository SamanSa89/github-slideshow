// Decoder 3D studio – deterministic renderer: window.renderAt(t) draws the frame for time t.
import * as THREE from 'three';
import { RoomEnvironment } from 'three/addons/environments/RoomEnvironment.js';
import { RoundedBoxGeometry } from 'three/addons/geometries/RoundedBoxGeometry.js';

const params = new URLSearchParams(location.search);
const W = +(params.get('w') || 720), H = +(params.get('h') || 1280);
const TL = await (await fetch(params.get('tl') || './work/timeline.json')).json();
const BGMODE = params.get('mode') === 'bg';
const MAPIMG = new Image(); if (BGMODE) { MAPIMG.src = './work/map.jpg'; await MAPIMG.decode(); }

const renderer = new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true });
renderer.setPixelRatio(1); renderer.setSize(W, H);
renderer.toneMapping = THREE.ACESFilmicToneMapping; renderer.toneMappingExposure = 1.05;
renderer.outputColorSpace = THREE.SRGBColorSpace;
renderer.shadowMap.enabled = params.get('shadows') === '1'; renderer.shadowMap.type = THREE.PCFShadowMap;
document.body.appendChild(renderer.domElement);

const scene = new THREE.Scene();
scene.background = new THREE.Color(0x05060b);
scene.fog = new THREE.Fog(0x05060b, 6, 14);
const pmrem = new THREE.PMREMGenerator(renderer);
scene.environment = pmrem.fromScene(new RoomEnvironment(), 0.04).texture;
scene.environmentIntensity = 0.35;

const camera = new THREE.PerspectiveCamera(40, W / H, 0.05, 50);

// ---------------------------------------------------------------- helpers
const M = (color, o = {}) => new THREE.MeshStandardMaterial({ color, roughness: 0.5, metalness: 0, ...o });
const mesh = (g, m, p = [0, 0, 0], parent = scene) => { const x = new THREE.Mesh(g, m); x.position.set(...p); x.castShadow = x.receiveShadow = true; parent.add(x); return x; };
const clamp = (x, a = 0, b = 1) => Math.min(b, Math.max(a, x));
const ease = x => 1 - Math.pow(1 - clamp(x), 3);
const easeIO = x => { x = clamp(x); return x < .5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2; };
const back = x => { x = clamp(x); const c = 1.7; return 1 + (c + 1) * Math.pow(x - 1, 3) + c * Math.pow(x - 1, 2); };
const pulse = (t, t0, up = 0.25, hold = 0.6, down = 0.5) => t < t0 ? 0 : t < t0 + up ? easeIO((t - t0) / up) : t < t0 + up + hold ? 1 : 1 - easeIO((t - t0 - up - hold) / down);
const sceneAt = t => { let s = TL.scenes[0]; for (const x of TL.scenes) if (t >= x.start - 0.05) s = x; return s; };
const sc = n => TL.scenes.find(s => s.name === n);
const wordT = (scene, tok) => { const w = TL.words.find(w => w.scene === scene && w.w.toLowerCase().includes(tok.toLowerCase())); return w ? w.t0 : sc(scene).start; };
const HL = TL.words.filter(w => w.hl).map(w => w.t0);
const rand = (() => { let s = 7; return () => (s = (s * 16807) % 2147483647) / 2147483647; })();

// ---------------------------------------------------------------- lights
scene.add(new THREE.AmbientLight(0x404660, 0.35));
const key = new THREE.DirectionalLight(0xfff1e0, 1.9); key.position.set(-1.6, 3.2, 3.2); key.castShadow = true;
key.shadow.mapSize.set(1024, 1024); key.shadow.camera.left = -2; key.shadow.camera.right = 2; key.shadow.camera.top = 3.5; key.shadow.camera.bottom = -0.5; key.shadow.bias = -0.0004; key.shadow.radius = 4;
scene.add(key);
const fill = new THREE.DirectionalLight(0x9fb8ff, 0.6); fill.position.set(2, 1.5, 2.5); scene.add(fill);
const rimR = new THREE.SpotLight(0xff2a3a, 40, 8, 0.6, 0.6); rimR.position.set(1.6, 2.6, -1.2); rimR.target.position.set(0, 1.5, 0); scene.add(rimR, rimR.target);
const rimC = new THREE.SpotLight(0x38d8ff, 28, 8, 0.6, 0.6); rimC.position.set(-1.7, 2.4, -1.0); rimC.target.position.set(0, 1.5, 0); scene.add(rimC, rimC.target);
const holoLight = new THREE.PointLight(0x58e0ff, 0, 4); holoLight.position.set(0, 2.7, 0.4); scene.add(holoLight);
const flash = new THREE.PointLight(0xffb070, 0, 6); flash.position.set(0, 2.8, 0.3); scene.add(flash);

// ---------------------------------------------------------------- studio
const floor = mesh(new THREE.CircleGeometry(9, 64), M(0x0b0d14, { roughness: 0.22, metalness: 0.6 }));
floor.rotation.x = -Math.PI / 2;
// floor light rings
for (let i = 0; i < 3; i++) { const r = mesh(new THREE.RingGeometry(1.2 + i * 0.9, 1.215 + i * 0.9, 96), new THREE.MeshBasicMaterial({ color: i ? 0x18303f : 0x6a1520 }), [0, 0.003, 0]); r.rotation.x = -Math.PI / 2; }

// LED wall with live canvas texture
const wallCv = document.createElement('canvas'); wallCv.width = 1024; wallCv.height = 1024;
const wctx = wallCv.getContext('2d'); const wallTex = new THREE.CanvasTexture(wallCv); wallTex.colorSpace = THREE.SRGBColorSpace; wallTex.wrapS = THREE.RepeatWrapping; wallTex.repeat.x = -1;
const wallGeo = new THREE.CylinderGeometry(3.2, 3.2, 3.4, 64, 1, true, -0.55, 1.1);
const wall = mesh(wallGeo, new THREE.MeshStandardMaterial({ map: wallTex, emissive: 0xffffff, emissiveMap: wallTex, emissiveIntensity: 0.32, side: THREE.BackSide, roughness: 0.9 }), [0, 2.1, 1.6]);
wall.rotation.y = Math.PI; wall.castShadow = false;
// wall frame strips
for (const y of [0.42, 3.78]) mesh(new THREE.TorusGeometry(3.18, 0.012, 6, 80, 1.1), new THREE.MeshBasicMaterial({ color: 0xe8263a }), [0, y, 1.6]).rotation.set(Math.PI / 2, 0, Math.PI / 2 - 0.55 + Math.PI);
// side pillars with light bars
for (const x of [-2.1, 2.1]) {
  mesh(new RoundedBoxGeometry(0.25, 3.6, 0.25, 4, 0.04), M(0x111420, { roughness: 0.3, metalness: 0.7 }), [x, 1.8, -0.9]);
  mesh(new THREE.BoxGeometry(0.03, 3.2, 0.03), new THREE.MeshBasicMaterial({ color: x < 0 ? 0x38d8ff : 0xff2a3a }), [x + (x < 0 ? 0.13 : -0.13), 1.8, -0.77]);
}

// desk
const _deskStart = scene.children.length;
const deskMat = M(0x0d0f16, { roughness: 0.18, metalness: 0.75 });
mesh(new RoundedBoxGeometry(1.9, 0.08, 0.7, 4, 0.03), deskMat, [0, 0.98, 0.45]);
const deskFront = mesh(new RoundedBoxGeometry(1.7, 0.92, 0.12, 4, 0.04), deskMat, [0, 0.5, 0.72]);
const logoCv = document.createElement('canvas'); logoCv.width = 1024; logoCv.height = 256; const lc = logoCv.getContext('2d');
lc.fillStyle = '#000'; lc.fillRect(0, 0, 1024, 256); lc.fillStyle = '#e8263a'; lc.fillRect(0, 230, 1024, 10);
lc.font = 'bold 120px DejaVu Sans, sans-serif'; lc.textAlign = 'center'; lc.fillStyle = '#ffffff'; lc.fillText('DECODER', 512, 160);
const logoTex = new THREE.CanvasTexture(logoCv); logoTex.colorSpace = THREE.SRGBColorSpace;
mesh(new THREE.PlaneGeometry(1.3, 0.325), new THREE.MeshStandardMaterial({ map: logoTex, emissive: 0xffffff, emissiveMap: logoTex, emissiveIntensity: 0.8 }), [0, 0.62, 0.785]);
mesh(new THREE.BoxGeometry(1.72, 0.015, 0.02), new THREE.MeshBasicMaterial({ color: 0xff2a3a }), [0, 0.94, 0.79]);

const _deskEnd = scene.children.length;
// ---------------------------------------------------------------- host
const SKIN = new THREE.MeshStandardMaterial({ color: 0xd49674, roughness: 0.6 });
const SUIT = M(0x1a2440, { roughness: 0.62 }), SUIT_D = M(0x111829, { roughness: 0.6 });
const HAIR = M(0x231a17, { roughness: 0.45, metalness: 0.1 });
const host = new THREE.Group(); scene.add(host);
const torsoProf = [[0, 0], [0.18, 0], [0.19, 0.22], [0.205, 0.38], [0.2, 0.46], [0.17, 0.51], [0.1, 0.545], [0.05, 0.56], [0, 0.56]].map(([x, y]) => new THREE.Vector2(x, y));
const torso = mesh(new THREE.LatheGeometry(torsoProf, 48), SUIT, [0, 0.86, 0], host); torso.scale.set(1.22, 1, 0.62);
for (const sx of [-1, 1]) { const sc = mesh(new THREE.SphereGeometry(0.075, 24, 16), SUIT, [sx * 0.215, 1.33, 0], host); sc.scale.set(1, 0.8, 0.9); }
const shirt = mesh(new THREE.ConeGeometry(0.085, 0.26, 3), M(0xf2f2f5), [0, 1.33, 0.112], host); shirt.rotation.set(Math.PI, Math.PI, 0.0); shirt.scale.z = 0.25;
const tie = mesh(new THREE.BoxGeometry(0.05, 0.3, 0.012), M(0xc81e32, { roughness: 0.35 }), [0, 1.24, 0.128], host); tie.rotation.x = -0.12;
mesh(new THREE.BoxGeometry(0.05, 0.035, 0.015), M(0xa5182a), [0, 1.385, 0.115], host);
for (const s of [-1, 1]) { const l = mesh(new THREE.BoxGeometry(0.05, 0.3, 0.015), SUIT_D, [s * 0.075, 1.27, 0.122], host); l.rotation.set(-0.12, 0, s * 0.32); }
mesh(new THREE.CylinderGeometry(0.066, 0.07, 0.14, 20), SKIN, [0, 1.46, 0.0], host);
mesh(new THREE.SphereGeometry(0.012, 12, 8), new THREE.MeshBasicMaterial({ color: 0xff2a3a }), [-0.15, 1.3, 0.118], host);

const head = new THREE.Group(); head.position.set(0, 1.625, 0.01); host.add(head);
const skull = mesh(new THREE.SphereGeometry(0.15, 48, 32), SKIN, [0, 0, 0], head); skull.scale.set(0.93, 1.07, 0.98);
const jaw = mesh(new THREE.SphereGeometry(0.12, 40, 24), SKIN, [0, -0.07, 0.012], head); jaw.scale.set(1.04, 0.85, 1.0);
const stubble = null && mesh(new THREE.SphereGeometry(0.1215, 40, 24, 0, Math.PI * 2, Math.PI * 0.45, Math.PI * 0.55), M(0x6b4a3c, { roughness: 0.9, transparent: true, opacity: 0.22 }), [0, -0.07, 0.012], head); 
for (const s of [-1, 1]) { const e = mesh(new THREE.SphereGeometry(0.035, 16, 12), SKIN, [s * 0.138, 0.0, -0.005], head); e.scale.set(0.45, 1, 0.8); }
const nose = mesh(new THREE.SphereGeometry(0.024, 20, 14), SKIN, [0, -0.01, 0.148], head); nose.scale.set(0.85, 1.15, 1.1);
const eyes = [];
for (const s of [-1, 1]) {
  const g = new THREE.Group(); g.position.set(s * 0.05, 0.028, 0.126); head.add(g);
  mesh(new THREE.SphereGeometry(0.021, 24, 16), M(0xf7f7f7, { roughness: 0.15 }), [0, 0, 0], g);
  mesh(new THREE.SphereGeometry(0.012, 20, 14), M(0x3d5f8a, { roughness: 0.2 }), [0, 0, 0.0135], g);
  mesh(new THREE.SphereGeometry(0.006, 12, 8), M(0x050505, { roughness: 0.1 }), [0, 0, 0.0225], g);
  mesh(new THREE.SphereGeometry(0.003, 8, 6), new THREE.MeshBasicMaterial({ color: 0xffffff }), [0.004, 0.004, 0.0245], g);
  const lid = mesh(new THREE.SphereGeometry(0.023, 24, 16, 0, Math.PI * 2, 0, Math.PI * 0.42), SKIN, [0, 0, 0], g); lid.rotation.x = -0.25;
  eyes.push({ g, lid });
}
const brows = [-1, 1].map(s => { const b = mesh(new RoundedBoxGeometry(0.062, 0.014, 0.018, 2, 0.006), HAIR, [s * 0.052, 0.066, 0.138], head); b.rotation.set(-0.2, 0, -s * 0.12); return b; });
const mouth = new THREE.Group(); mouth.position.set(0, -0.078, 0.128); head.add(mouth);
const mouthIn = mesh(new THREE.SphereGeometry(0.03, 24, 16), M(0x3a0f14, { roughness: 0.8 }), [0, 0, 0], mouth); mouthIn.scale.set(1.25, 0.15, 0.45);
const teeth = mesh(new RoundedBoxGeometry(0.044, 0.01, 0.01, 2, 0.003), M(0xf4f4f0, { roughness: 0.3 }), [0, 0.006, 0.008], mouth);
const lipU = mesh(new THREE.TorusGeometry(0.036, 0.0065, 8, 24, Math.PI), M(0xb86a66, { roughness: 0.5 }), [0, 0.004, 0.0], mouth); lipU.scale.set(1, 0.3, 1);
const lipL = mesh(new THREE.TorusGeometry(0.034, 0.007, 8, 24, Math.PI), M(0xb86a66, { roughness: 0.5 }), [0, -0.004, 0.0], mouth); lipL.rotation.z = Math.PI; lipL.scale.set(1, 0.3, 1);
// hair
const hairTop = mesh(new THREE.SphereGeometry(0.16, 40, 24, 0, Math.PI * 2, 0, Math.PI * 0.4), HAIR, [0, 0.022, -0.018], head); hairTop.scale.set(0.98, 1.1, 1.02); hairTop.rotation.x = -0.42;
const hairBack = mesh(new THREE.SphereGeometry(0.158, 40, 24, Math.PI * 0.15, Math.PI * 0.7, 0.2, Math.PI * 0.45), HAIR, [0, 0.0, -0.012], head); hairBack.rotation.y = Math.PI; hairBack.scale.set(0.97, 1.08, 1.02);
const quiff = mesh(new THREE.SphereGeometry(0.075, 24, 16), HAIR, [0.02, 0.145, 0.045], head); quiff.scale.set(1.5, 0.55, 1.05); quiff.rotation.set(-0.45, 0, -0.12);
for (const s of [-1, 1]) { const sb = mesh(new THREE.SphereGeometry(0.06, 16, 12), HAIR, [s * 0.128, 0.05, -0.03], head); sb.scale.set(0.35, 0.9, 1.1); }
// headset
const micCurve = new THREE.CatmullRomCurve3([new THREE.Vector3(-0.142, 0.0, 0.0), new THREE.Vector3(-0.138, -0.06, 0.07), new THREE.Vector3(-0.09, -0.09, 0.125), new THREE.Vector3(-0.045, -0.085, 0.14)]);
mesh(new THREE.TubeGeometry(micCurve, 20, 0.0035, 6), M(0x111111, { roughness: 0.3, metalness: 0.6 }), [0, 0, 0], head);
mesh(new THREE.SphereGeometry(0.009, 12, 8), M(0x111111), [-0.045, -0.085, 0.14], head);
mesh(new THREE.SphereGeometry(0.022, 16, 12), M(0x111111, { metalness: 0.6, roughness: 0.3 }), [-0.15, 0.0, 0.0], head);

// arms (shoulder -> elbow -> hand)
function makeArm(s) {
  const sh = new THREE.Group(); sh.position.set(s * 0.25, 1.33, 0.0); host.add(sh);
  const up = mesh(new THREE.CapsuleGeometry(0.062, 0.22, 6, 16), SUIT, [0, -0.15, 0], sh);
  const el = new THREE.Group(); el.position.set(0, -0.3, 0); sh.add(el);
  mesh(new THREE.CapsuleGeometry(0.058, 0.2, 6, 16), SUIT, [0, -0.13, 0], el);
  mesh(new THREE.CylinderGeometry(0.05, 0.05, 0.03, 16), M(0xf2f2f5), [0, -0.265, 0], el);
  const hand = new THREE.Group(); hand.position.set(0, -0.3, 0); el.add(hand);
  const palm = mesh(new RoundedBoxGeometry(0.075, 0.09, 0.035, 3, 0.015), SKIN, [0, -0.03, 0], hand);
  const thumb = mesh(new THREE.CapsuleGeometry(0.013, 0.035, 4, 8), SKIN, [s * -0.04, -0.01, 0.01], hand); thumb.rotation.z = s * 0.7;
  for (let i = 0; i < 4; i++) { const f = mesh(new THREE.CapsuleGeometry(0.009, 0.04, 4, 8), SKIN, [-0.026 + i * 0.017, -0.095, 0], hand); }
  return { sh, el, hand, s };
}
const arms = [makeArm(-1), makeArm(1)];

// ---------------------------------------------------------------- holograms / props
const HOLO = (c = 0x58e0ff, o = 0.9) => new THREE.MeshStandardMaterial({ color: 0x000000, emissive: c, emissiveIntensity: 1.6, transparent: true, opacity: o, depthWrite: false, side: THREE.DoubleSide });
const LINE = (c = 0x58e0ff, o = 0.75) => new THREE.LineBasicMaterial({ color: c, transparent: true, opacity: o });
const stage = new THREE.Group(); stage.position.set(0, 2.36, 0.3); stage.scale.setScalar(0.72); scene.add(stage);
// projector disc on desk
const disc = mesh(new THREE.CylinderGeometry(0.22, 0.25, 0.03, 48), M(0x111520, { metalness: 0.8, roughness: 0.25 }), [0.62, 1.035, 0.42]);
const discGlow = mesh(new THREE.TorusGeometry(0.21, 0.008, 8, 64), new THREE.MeshBasicMaterial({ color: 0x58e0ff }), [0.62, 1.052, 0.42]); discGlow.rotation.x = Math.PI / 2;
const beam = mesh(new THREE.CylinderGeometry(0.55, 0.2, 1.4, 48, 1, true), new THREE.MeshBasicMaterial({ color: 0x58e0ff, transparent: true, opacity: 0.05, depthWrite: false, side: THREE.DoubleSide, blending: THREE.AdditiveBlending }), [0.3, 1.75, 0.35]);
beam.visible = false;

function globe(r = 0.42) {
  const g = new THREE.Group();
  const core = new THREE.Mesh(new THREE.SphereGeometry(r * 0.985, 48, 32), new THREE.MeshStandardMaterial({ color: 0x06121e, emissive: 0x0a2a40, emissiveIntensity: 0.6, transparent: true, opacity: 0.85, roughness: 0.4 }));
  g.add(core);
  const lines = new THREE.LineSegments(new THREE.EdgesGeometry(new THREE.SphereGeometry(r, 24, 14)), LINE(0x58e0ff, 0.45)); g.add(lines);
  // pseudo continents: dotted cloud
  const pts = []; for (let i = 0; i < 1400; i++) { const u = rand() * 2 - 1, th = rand() * Math.PI * 2; const n = Math.sin(th * 3 + u * 4) + Math.cos(th * 2 - u * 5) * 0.8; if (n > 0.6) { const s = Math.sqrt(1 - u * u); pts.push(r * s * Math.cos(th), r * u, r * s * Math.sin(th)); } }
  const pg = new THREE.BufferGeometry(); pg.setAttribute('position', new THREE.Float32BufferAttribute(pts, 3));
  g.add(new THREE.Points(pg, new THREE.PointsMaterial({ color: 0x9ff0ff, size: 0.012, transparent: true, opacity: 0.9 })));
  return g;
}
function satellite(scale = 1, color = 0xd8dde6) {
  const g = new THREE.Group();
  mesh(new THREE.BoxGeometry(0.03, 0.03, 0.05), M(color, { metalness: 0.8, roughness: 0.3 }), [0, 0, 0], g);
  for (const s of [-1, 1]) mesh(new THREE.BoxGeometry(0.07, 0.003, 0.035), M(0x1b3d8f, { metalness: 0.5, roughness: 0.25, emissive: 0x0a1a40 }), [s * 0.052, 0, 0], g);
  g.scale.setScalar(scale); return g;
}
function rocketStarship() {
  const g = new THREE.Group(); const steel = M(0xc9ced6, { metalness: 0.95, roughness: 0.22 });
  mesh(new THREE.CylinderGeometry(0.06, 0.06, 0.5, 32), steel, [0, 0, 0], g);
  mesh(new THREE.SphereGeometry(0.06, 32, 16, 0, Math.PI * 2, 0, Math.PI / 2), steel, [0, 0.25, 0], g).scale.y = 1.8;
  for (const [y, s] of [[0.2, 1], [-0.2, 1.3]]) for (const k of [-1, 1]) { const f = mesh(new THREE.BoxGeometry(0.05 * s, 0.09 * s, 0.006), M(0x2a2e36, { metalness: 0.7, roughness: 0.4 }), [k * 0.075, y, 0], g); f.rotation.z = k * 0.1; }
  for (let i = 0; i < 6; i++) mesh(new THREE.BoxGeometry(0.11, 0.0015, 0.11), M(0x9aa2ad, { metalness: 0.9 }), [0, -0.2 + i * 0.07, 0], g).visible = i % 2 === 0;
  const fl = mesh(new THREE.ConeGeometry(0.045, 0.22, 20, 1, true), new THREE.MeshBasicMaterial({ color: 0xffa040, transparent: true, opacity: 0.85, blending: THREE.AdditiveBlending, depthWrite: false }), [0, -0.37, 0], g);
  fl.rotation.x = Math.PI; g.userData.flame = fl; return g;
}
function tower() {
  const g = new THREE.Group(); const metal = M(0x3a3f4a, { metalness: 0.8, roughness: 0.45 });
  for (const [x, z] of [[-0.06, -0.06], [0.06, -0.06], [-0.06, 0.06], [0.06, 0.06]]) mesh(new THREE.BoxGeometry(0.012, 1.0, 0.012), metal, [x, 0, z], g);
  for (let i = 0; i < 12; i++) { const b = mesh(new THREE.BoxGeometry(0.13, 0.008, 0.008), metal, [0, -0.48 + i * 0.085, 0.06], g); b.rotation.z = (i % 2 ? 0.6 : -0.6); }
  const arms = [];
  for (const s of [-1, 1]) { const p = new THREE.Group(); p.position.set(0.07, 0.18, s * 0.05); g.add(p); mesh(new THREE.BoxGeometry(0.34, 0.025, 0.02), M(0x8b919c, { metalness: 0.85, roughness: 0.3 }), [0.17, 0, 0], p); arms.push(p); }
  g.userData.arms = arms; return g;
}
function vulcan() {
  const g = new THREE.Group();
  mesh(new THREE.CylinderGeometry(0.055, 0.055, 0.42, 32), M(0xd9893a, { roughness: 0.5 }), [0, -0.05, 0], g);
  mesh(new THREE.CylinderGeometry(0.055, 0.055, 0.2, 32), M(0xeeeeee, { roughness: 0.4 }), [0, 0.26, 0], g);
  mesh(new THREE.ConeGeometry(0.055, 0.14, 32), M(0xeeeeee, { roughness: 0.4 }), [0, 0.43, 0], g);
  for (const s of [-1, 1]) { mesh(new THREE.CylinderGeometry(0.018, 0.018, 0.26, 16), M(0xf4f4f4), [s * 0.07, -0.13, 0], g); mesh(new THREE.ConeGeometry(0.018, 0.04, 16), M(0xf4f4f4), [s * 0.07, 0.02, 0], g); }
  const fl = mesh(new THREE.ConeGeometry(0.06, 0.3, 20, 1, true), new THREE.MeshBasicMaterial({ color: 0xffb050, transparent: true, opacity: 0.9, blending: THREE.AdditiveBlending, depthWrite: false }), [0, -0.42, 0], g);
  fl.rotation.x = Math.PI; g.userData.flame = fl; return g;
}
function drone() {
  const g = new THREE.Group(); const gun = M(0x2a2d33, { metalness: 0.85, roughness: 0.35 });
  mesh(new RoundedBoxGeometry(0.16, 0.05, 0.2, 3, 0.02), gun, [0, 0, 0], g);
  const rotors = [];
  for (const [x, z] of [[-1, -1], [1, -1], [-1, 1], [1, 1]]) {
    const a = mesh(new THREE.BoxGeometry(0.16, 0.012, 0.012), gun, [x * 0.08, 0, z * 0.08], g); a.rotation.y = Math.atan2(z, x) * -1 + Math.PI / 2 * 0;
    a.lookAt(new THREE.Vector3(0, 0, 0)); a.rotation.set(0, Math.atan2(-z, x), 0);
    const r = mesh(new THREE.CylinderGeometry(0.075, 0.075, 0.003, 24), new THREE.MeshStandardMaterial({ color: 0x444a55, transparent: true, opacity: 0.45, metalness: 0.5 }), [x * 0.14, 0.03, z * 0.14], g); rotors.push(r);
    mesh(new THREE.CylinderGeometry(0.012, 0.012, 0.035, 12), gun, [x * 0.14, 0.012, z * 0.14], g);
  }
  const eye = mesh(new THREE.SphereGeometry(0.022, 20, 14), new THREE.MeshBasicMaterial({ color: 0xff2030 }), [0, -0.01, 0.1], g);
  const cone = new THREE.Mesh(new THREE.ConeGeometry(0.16, 0.7, 32, 1, true), new THREE.MeshBasicMaterial({ color: 0xff2030, transparent: true, opacity: 0.05, depthWrite: false, blending: THREE.AdditiveBlending, side: THREE.DoubleSide }));
  cone.position.set(0, -0.04, 0.45); cone.rotation.x = -Math.PI / 2 - 0.5; g.add(cone);
  g.userData = { rotors, cone }; return g;
}
function keyObj() {
  const g = new THREE.Group(); const gold = M(0xd8a640, { metalness: 1.0, roughness: 0.18 });
  mesh(new THREE.TorusGeometry(0.1, 0.028, 20, 48), gold, [0, 0.22, 0], g);
  mesh(new THREE.CylinderGeometry(0.022, 0.022, 0.38, 24), gold, [0, -0.04, 0], g);
  for (const [y, w] of [[-0.2, 0.08], [-0.13, 0.06], [-0.07, 0.07]]) mesh(new THREE.BoxGeometry(w, 0.035, 0.03), gold, [w / 2 + 0.01, y, 0], g);
  return g;
}
function textPlane(txt, color = '#ffffff', w = 0.9, size = 140, bg = null) {
  const cv = document.createElement('canvas'); cv.width = 1024; cv.height = 256; const c = cv.getContext('2d');
  if (bg) { c.fillStyle = bg; c.fillRect(0, 0, 1024, 256); }
  c.font = `bold ${size}px DejaVu Sans, sans-serif`; c.textAlign = 'center'; c.textBaseline = 'middle'; c.fillStyle = color; c.fillText(txt, 512, 132);
  const tx = new THREE.CanvasTexture(cv); tx.colorSpace = THREE.SRGBColorSpace;
  const m = new THREE.Mesh(new THREE.PlaneGeometry(w, w / 4), new THREE.MeshBasicMaterial({ map: tx, transparent: true, depthWrite: false }));
  return m;
}

// build per-scene prop groups
const P = {};
P.hook = new THREE.Group(); { const gl = globe(); P.hook.add(gl); P.hook.userData.globe = gl; const sats = []; for (let i = 0; i < 8; i++) { const s = satellite(0.9); P.hook.add(s); sats.push(s); } P.hook.userData.sats = sats; }
P.starship = new THREE.Group(); { const tw = tower(); tw.position.set(-0.12, -0.1, 0); tw.scale.setScalar(0.8); P.starship.add(tw); const sh = rocketStarship(); P.starship.add(sh); const sats = []; for (let i = 0; i < 26; i++) { const s = satellite(0.55); s.visible = false; P.starship.add(s); sats.push(s); } Object.assign(P.starship.userData, { tw, sh, sats }); }
P.vulcan = new THREE.Group(); { const v = vulcan(); P.vulcan.add(v); const sats = []; for (let i = 0; i < 40; i++) { const s = satellite(0.45, 0xffffff); s.visible = false; P.vulcan.add(s); sats.push(s); } const smoke = []; for (let i = 0; i < 40; i++) { const m = new THREE.Mesh(new THREE.SphereGeometry(0.04, 12, 8), new THREE.MeshStandardMaterial({ color: 0x9a9a9a, transparent: true, opacity: 0.4, roughness: 1, depthWrite: false })); P.vulcan.add(m); smoke.push(m); }
  const boom = new THREE.Mesh(new THREE.SphereGeometry(0.2, 32, 16), new THREE.MeshBasicMaterial({ color: 0xffc070, transparent: true, opacity: 0, blending: THREE.AdditiveBlending, depthWrite: false })); P.vulcan.add(boom); Object.assign(P.vulcan.userData, { v, sats, smoke, boom }); }
P.connect = new THREE.Group(); { const gl = globe(0.38); P.connect.add(gl);
  const n = 500, im = new THREE.InstancedMesh(new THREE.SphereGeometry(0.006, 6, 4), new THREE.MeshBasicMaterial({ color: 0x9ff0ff }), n); P.connect.add(im);
  const im2 = new THREE.InstancedMesh(new THREE.SphereGeometry(0.011, 8, 6), new THREE.MeshBasicMaterial({ color: 0xff9a30 }), 40); P.connect.add(im2);
  const seeds = Array.from({ length: n }, () => [rand() * 6.28, rand() * 6.28, 0.45 + rand() * 0.03]); const seeds2 = Array.from({ length: 40 }, () => [rand() * 6.28, rand() * 6.28, 0.52]);
  const l1 = textPlane('STARLINK', '#9ff0ff', 0.5, 120); l1.position.set(-0.25, 0.48, 0.2); P.connect.add(l1);
  const l2 = textPlane('AMAZON LEO', '#ff9a30', 0.55, 120); l2.position.set(0.25, -0.5, 0.2); P.connect.add(l2);
  Object.assign(P.connect.userData, { gl, im, im2, seeds, seeds2 }); }
P.genf = new THREE.Group(); { const d = drone(); d.scale.setScalar(2.3); P.genf.add(d); P.genf.userData.d = d; }
P.verdict = new THREE.Group(); { const k = keyObj(); k.scale.setScalar(1.15); P.verdict.add(k); P.verdict.userData.k = k; }
P.cta = new THREE.Group(); { const t1 = textPlane('PRÜF MICH.', '#ff2a3a', 1.1, 150); P.cta.add(t1); const ring = new THREE.Mesh(new THREE.TorusGeometry(0.45, 0.008, 8, 96), HOLO(0xff2a3a)); P.cta.add(ring); const ring2 = new THREE.Mesh(new THREE.TorusGeometry(0.5, 0.004, 8, 96), HOLO(0x58e0ff)); P.cta.add(ring2); Object.assign(P.cta.userData, { t1, ring, ring2 }); }
for (const k in P) { P[k].visible = false; stage.add(P[k]); P[k].traverse(o => { if (o.isMesh) o.castShadow = false; }); }

// ---------------------------------------------------------------- LED wall drawing
const FONT = 'DejaVu Sans, sans-serif';
function wallDrawBG(t, s) {
  const c = wctx, lt = t - s.start;
  const g = c.createLinearGradient(0, 0, 0, 1024); g.addColorStop(0, '#0a2a7a'); g.addColorStop(0.6, '#06205e'); g.addColorStop(1, '#041437'); c.fillStyle = g; c.fillRect(0, 0, 1024, 1024);
  const EN = params.get('lang') === 'en';
  c.globalAlpha = 0.85; c.drawImage(MAPIMG, 600, 520, 300, 420); c.globalAlpha = 1;
  // BREAKING NEWS band at the anchor's eye line (visible left and right of the head)
  const blink = 0.75 + 0.25 * Math.sin(t * 5);
  c.fillStyle = '#0b1d52'; c.fillRect(0, 372, 1024, 112);
  c.fillStyle = `rgba(212,20,42,${blink})`; c.fillRect(208, 380, 166, 96);
  c.fillStyle = '#ffffff'; c.textAlign = 'left'; c.textBaseline = 'alphabetic';
  c.font = `bold 28px ${FONT}`; c.fillText('BREAKING', 218, 418); c.fillText('NEWS', 218, 456);
  c.fillStyle = '#ffffff'; c.fillRect(592, 380, 178, 96);
  c.font = `bold 20px ${FONT}`; c.fillStyle = '#0b1d52'; c.fillText(EN ? 'THE' : 'DER', 602, 404);
  c.fillStyle = '#d4142a'; c.fillRect(600, 412, 162, 50);
  c.font = `bold 30px ${FONT}`; c.fillStyle = '#ffffff'; c.fillText('DECODER', 606, 449);
  // ticker strip
  c.fillStyle = '#d4142a'; c.fillRect(0, 486, 1024, 30);
  const tk = (EN ? '  THE DECODER  •  BREAKING NEWS  •  VERIFY ME  •' : '  DER DECODER  •  BREAKING NEWS  •  PRÜF MICH  •').repeat(6);
  c.font = `bold 20px ${FONT}`; c.fillStyle = '#ffffff'; c.fillText(tk, -((t * 60) % 520), 508);
  // moving light streak
  const x = ((t * 90) % 1400) - 200; const lg = c.createLinearGradient(x - 120, 0, x + 120, 0); lg.addColorStop(0, 'rgba(120,180,255,0)'); lg.addColorStop(0.5, 'rgba(120,180,255,0.16)'); lg.addColorStop(1, 'rgba(120,180,255,0)'); c.fillStyle = lg; c.fillRect(0, 0, 1024, 1024);
  c.fillStyle = '#d4142a'; c.fillRect(0, 960, 1024, 10); c.fillStyle = '#3a8dff'; c.fillRect(0, 60, 1024, 8);
  if (params.get('calib')) { [[200,'#00ffff'],[350,'#00ff00'],[500,'#ffff00'],[650,'#ff00ff'],[800,'#ffffff']].forEach(([y,c])=>{ const c_=wctx; c_.fillStyle=c; c_.fillRect(0,y,1024,30); c_.fillStyle='#000'; c_.font='bold 28px sans-serif'; for(let x=0;x<1024;x+=128){c_.fillText(String(x),x+4,y+26);} }); }
  wallTex.needsUpdate = true;
}
function wallDraw(t, s) {
  if (BGMODE) return wallDrawBG(t, s);
  const c = wctx, lt = t - s.start;
  const g = c.createLinearGradient(0, 0, 0, 1024); g.addColorStop(0, '#0a0d1c'); g.addColorStop(1, '#16070c'); c.fillStyle = g; c.fillRect(0, 0, 1024, 1024);
  c.strokeStyle = 'rgba(88,224,255,0.07)'; c.lineWidth = 2; for (let x = (t * 20) % 64; x < 1024; x += 64) { c.beginPath(); c.moveTo(x, 0); c.lineTo(x, 1024); c.stroke(); } for (let y = 0; y < 1024; y += 64) { c.beginPath(); c.moveTo(0, y); c.lineTo(1024, y); c.stroke(); }
  c.textAlign = 'center'; c.textBaseline = 'middle';
  const big = (txt, y, col = '#fff', sz = 92) => { c.font = `bold ${sz}px ${FONT}`; c.fillStyle = col; c.fillText(txt, 512, y); };
  const tag = (txt, y, col = '#e8263a') => { c.font = `bold 40px ${FONT}`; const w = c.measureText(txt).width + 50; c.fillStyle = col; c.fillRect(512 - w / 2, y - 32, w, 64); c.fillStyle = '#fff'; c.fillText(txt, 512, y + 2); };
  const KW = { hook: 'HIMMEL', starship: 'ORBIT', vulcan: 'ANOMALIE', connect: 'NETZ', genf: 'GENF', verdict: 'KONTROLLE', cta: 'DECODER' };
  c.globalAlpha = 0.07 * ease(lt / 0.8); c.font = `bold 190px ${FONT}`; c.fillStyle = s.name === 'vulcan' && t > TL.events.anomaly ? '#ff3040' : '#9fdfff';
  c.fillText(KW[s.name] || '', 512, 520);
  c.globalAlpha = 0.5; c.fillStyle = '#e8263a'; c.fillRect(0, 980, 1024 * ((t % 8) / 8), 6);
  c.globalAlpha = 1;
  wallTex.needsUpdate = true;
}

// ---------------------------------------------------------------- animation per frame
function animHost(t, fi) {
  const lv = TL.mouth[Math.min(fi, TL.mouth.length - 1)] || 0;
  const prev = TL.mouth[Math.max(0, fi - 1)] || 0, sm = 0.6 * lv + 0.4 * prev;
  mouthIn.scale.y = 0.12 + sm * 0.95; teeth.position.y = 0.006 + sm * 0.004; lipL.position.y = -0.004 - sm * 0.022;
  const bl = (t % 3.7 < 0.14) || (t % 9.1 < 0.1) ? 1 : 0;
  for (const e of eyes) { e.lid.rotation.x = bl ? 1.25 : -0.25; e.g.children[1].position.x = Math.sin(t * 0.7) * 0.003; }
  // highlights -> brow raise + gesture
  let hl = 0, last = -9, idx = 0;
  HL.forEach((h, i) => { if (t >= h - 0.15) { last = h; idx = i; } });
  hl = pulse(t, last - 0.15, 0.25, 0.7, 0.6);
  brows[0].position.y = 0.066 + hl * 0.006; brows[1].position.y = 0.066 + hl * 0.014; brows[1].rotation.z = -0.12 - hl * 0.15;
  const q = TL.words.some(w => t >= w.t0 && t < w.t1 + 0.4 && w.w.endsWith('?'));
  // head motion
  head.rotation.x = -0.03 + Math.sin(t * 1.9) * 0.02 - sm * 0.05 + hl * 0.03;
  head.rotation.y = Math.sin(t * 0.55) * 0.12 + Math.sin(t * 1.3) * 0.03;
  head.rotation.z = Math.sin(t * 0.8) * 0.03 + (q ? 0.08 : 0);
  torso.scale.y = 1 + Math.sin(t * 1.6) * 0.008;
  host.rotation.y = Math.sin(t * 0.35) * 0.06;
  // arms: rest = forearms on desk; gesture alternating hands on highlights
  arms.forEach((a, i) => {
    const g = (idx % 2 === i) ? hl : 0;
    const talk = sm * 0.12 * (i ? 1 : 0.6);
    a.sh.rotation.x = -0.35 - g * 0.55 - talk; a.sh.rotation.z = a.s * (0.12 + g * 0.25);
    a.el.rotation.x = -1.2 - g * 0.85 + Math.sin(t * 2.3 + i) * 0.04; a.el.rotation.z = a.s * -0.15 * g;
    a.hand.rotation.x = -0.1 + g * 0.6; a.hand.rotation.y = a.s * (0.5 + g * 0.5);
  });
}

function showProp(name, t, s) {
  for (const k in P) P[k].visible = false;
  const p = P[name]; if (!p) return; p.visible = true;
  const lt = t - s.start, out = s.end - t;
  const sc = back(lt / 0.6) * (out < 0.4 ? ease(out / 0.4) : 1);
  p.scale.setScalar(Math.max(0.001, sc));
  p.rotation.set(0, 0, 0); p.position.set(0, 0, 0);
  const u = p.userData;
  if (name === 'hook') { u.globe.rotation.y = t * 0.35; u.globe.rotation.z = 0.35; u.sats.forEach((x, i) => { const a = t * (0.5 + i * 0.07) + i; const r = 0.55 + (i % 3) * 0.05; x.position.set(Math.cos(a) * r, Math.sin(a * 0.7 + i) * 0.25, Math.sin(a) * r); x.rotation.y = -a; }); p.position.x = 0.05; }
  if (name === 'starship') {
    p.position.set(0.15, -0.05, 0);
    const catchT = s.start + (wordT('starship', 'Startturms') - s.start) + 0.3;
    const k = ease((t - s.start - 0.3) / (catchT - s.start - 0.3));
    u.sh.position.set(0.11, 0.9 - 0.82 * k, 0); u.sh.userData.flame.visible = k < 1; u.sh.userData.flame.scale.y = 0.8 + Math.sin(t * 40) * 0.2;
    const close = ease((t - catchT + 0.2) / 0.5); u.tw.userData.arms.forEach((a, i) => a.rotation.y = (i ? -1 : 1) * (0.9 - 0.9 * close));
    p.rotation.y = Math.sin(t * 0.4) * 0.5 - 0.3;
    const st = wordT('starship', '26');
    u.sats.forEach((x, i) => { x.visible = t > st; const a = (i / 26) * Math.PI * 2 + t * 0.4; const r = 0.5 * ease((t - st) / 1.2); x.position.set(Math.cos(a) * r, 0.25 + Math.sin(a * 3) * 0.04, Math.sin(a) * r); x.rotation.y = -a; });
  }
  if (name === 'vulcan') {
    const an = TL.events.anomaly; const k = clamp((t - s.start) / Math.max(0.1, an - s.start));
    u.v.visible = t < an; u.v.position.set(0, -0.55 + 0.95 * easeIO(k), 0); u.v.rotation.z = Math.sin(t * 3) * 0.02; u.v.userData.flame.scale.y = 0.9 + Math.sin(t * 37) * 0.15;
    u.smoke.forEach((m, i) => { const born = s.start + i * (an - s.start) / 40; const age = t - born; m.visible = age > 0 && age < 3; const y0 = -0.55 + 0.95 * easeIO(clamp((born - s.start) / (an - s.start))) - 0.35; m.position.set(Math.sin(i * 7) * 0.04 * age, y0 - age * 0.05, Math.cos(i * 5) * 0.04 * age); m.scale.setScalar(0.4 + age * 0.35); m.material.opacity = 0.25 * (1 - age / 3); });
    const be = t - an; u.boom.material.opacity = be > 0 ? Math.max(0, 1 - be / 0.8) : 0; u.boom.scale.setScalar(be > 0 ? 0.3 + be * 1.6 : 0.01); u.boom.position.set(0, 0.4, 0);
    flash.intensity = be > 0 ? Math.max(0, 30 * (1 - be / 0.6)) : 0;
    u.sats.forEach((x, i) => { x.visible = be > 0 && be < 4; const a = i * 2.39996, e = Math.acos(1 - 2 * (i + 0.5) / 40); const r = 0.05 + be * 0.35; x.position.set(Math.sin(e) * Math.cos(a) * r, 0.4 + Math.cos(e) * r - be * be * 0.06, Math.sin(e) * Math.sin(a) * r); x.rotation.set(be * (i % 5), be * 3, 0); x.children.forEach(c => { if (c.material.emissive) c.material.emissive.setHex(0x550000); }); });
  } else flash.intensity = 0;
  if (name === 'connect') {
    u.gl.rotation.y = t * 0.3; const m4 = new THREE.Matrix4();
    u.seeds.forEach((s_, i) => { const a = s_[0] + t * 0.5, b = s_[1]; m4.setPosition(Math.cos(a) * Math.cos(b) * s_[2], Math.sin(b) * s_[2] * 0.9, Math.sin(a) * Math.cos(b) * s_[2]); u.im.setMatrixAt(i, m4); });
    u.im.instanceMatrix.needsUpdate = true;
    u.seeds2.forEach((s_, i) => { const a = s_[0] + t * 0.35, b = s_[1]; m4.setPosition(Math.cos(a) * Math.cos(b) * s_[2], Math.sin(b) * s_[2] * 0.9, Math.sin(a) * Math.cos(b) * s_[2]); u.im2.setMatrixAt(i, m4); });
    u.im2.instanceMatrix.needsUpdate = true;
  }
  if (name === 'genf') { const d = u.d; d.position.set(Math.sin(t * 0.6) * 0.15, Math.sin(t * 1.3) * 0.05, 0); d.rotation.set(0.25, Math.sin(t * 0.5) * 0.7, Math.sin(t * 0.9) * 0.05); d.userData.rotors.forEach((r, i) => r.rotation.y = t * 40 + i); d.userData.cone.rotation.z = Math.sin(t * 1.4) * 0.4; }
  if (name === 'verdict') { u.k.rotation.set(0.2, t * 0.9, Math.sin(t * 0.7) * 0.15); u.k.position.y = -0.02 + Math.sin(t * 1.2) * 0.03; }
  if (name === 'cta') { u.ring.rotation.set(1.2, 0, t * 0.8); u.ring2.rotation.set(1.3, 0.2, -t * 0.6); u.t1.position.z = 0.05; }
}

function animCamera(t, s) {
  const lt = t - s.start;
  const base = { hook: [0, 1.95, 2.75], starship: [0.25, 2.0, 2.7], vulcan: [-0.25, 2.0, 2.7], connect: [0.2, 1.95, 2.8], genf: [-0.25, 1.98, 2.65], verdict: [0, 1.9, 2.55], cta: [0, 1.92, 2.75] }[s.name] || [0, 2.05, 3.5];
  const prev = TL.scenes[TL.scenes.indexOf(s) - 1];
  let p = base;
  if (prev) { const pb = { hook: [0, 1.95, 2.75], starship: [0.25, 2.0, 2.7], vulcan: [-0.25, 2.0, 2.7], connect: [0.2, 1.95, 2.8], genf: [-0.25, 1.98, 2.65], verdict: [0, 1.9, 2.55], cta: [0, 1.92, 2.75] }[prev.name]; const k = easeIO(lt / 1.4); p = pb.map((v, i) => v + (base[i] - v) * k); }
  const dolly = -Math.min(lt, 12) * 0.018;
  camera.position.set(p[0] + Math.sin(t * 0.21) * 0.08, p[1] + Math.sin(t * 0.33) * 0.03, p[2] + dolly);
  let hl = 0; HL.forEach(h => { hl = Math.max(hl, pulse(t, h - 0.1, 0.18, 0.3, 0.6)); });
  camera.fov = 40 - hl * 1.6; camera.updateProjectionMatrix();
  camera.lookAt(0.03 + Math.sin(t * 0.21) * 0.03, 1.98, 0);
}

if (BGMODE) {
  host.visible = false; for (let i = _deskStart; i < _deskEnd; i++) scene.children[i].visible = false;
  disc.visible = false; discGlow.visible = false;
  scene.background = new THREE.Color(0x041233); scene.fog = new THREE.Fog(0x041233, 7, 16);
  wall.material.emissiveIntensity = 0.75; floor.material.color.setHex(0x0a1430);
  stage.position.set(0, 2.62, 0.3); stage.scale.setScalar(0.78);
  if (params.get('noprops')) stage.visible = false;
}
function animCameraBG(t, s) {
  camera.position.set(Math.sin(t * 0.17) * 0.18, 2.2 + Math.sin(t * 0.23) * 0.03, 3.6);
  camera.fov = 40; camera.updateProjectionMatrix(); camera.lookAt(Math.sin(t * 0.17) * 0.05, 2.32, 0);
}
let frameI = 0;
window.renderAt = (t) => {
  const s = sceneAt(t); const fi = Math.round(t * TL.fps);
  if (!BGMODE) animHost(t, fi); showProp(s.name, t, s); wallDraw(t, s); if (BGMODE) animCameraBG(t, s); else animCamera(t, s);
  holoLight.intensity = 3 + Math.sin(t * 3) * 0.5;
  discGlow.material.color.setHSL(0.53, 1, 0.5 + 0.1 * Math.sin(t * 4));
  renderer.render(scene, camera); frameI++;
  return renderer.domElement.toDataURL('image/jpeg', 0.92);
};
window.READY = true;
