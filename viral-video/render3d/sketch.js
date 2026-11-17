// Hand-drawn "Leinwand" (canvas) layer: marker sketches drawn stroke by stroke, synced to word timings.
// window.renderAt(t) updates the drawing for time t (deterministic).
import rough from 'roughjs';

const PRM = new URLSearchParams(location.search); const EP = PRM.get('ep') || '';
const TL = await (await fetch(PRM.get('tl') || './work/timeline.json')).json();
await document.fonts.load('700 40px Caveat');
const NS = 'http://www.w3.org/2000/svg';
const svg = document.getElementById('svg'), board = document.getElementById('board');
const rc = rough.svg(svg);
const INK = '#1d2433', RED = '#d4142a', BLUE = '#1f5fbf', GREEN = '#178a3a', YEL = '#ffd23c';
const clamp = (x, a = 0, b = 1) => Math.min(b, Math.max(a, x));
const ease = x => 1 - Math.pow(1 - clamp(x), 3);
const back = x => { x = clamp(x); const c = 1.6; return 1 + (c + 1) * Math.pow(x - 1, 3) + c * Math.pow(x - 1, 2); };

const SC = {};
for (const s of TL.scenes) { const g = document.createElementNS(NS, 'g'); svg.appendChild(g); SC[s.name] = { g, items: [], s }; }
const penLayer = document.createElementNS(NS, 'g'); svg.appendChild(penLayer);
let CUR = null, seed = 1;
const wt = (tok, nth = 0, off = 0) => {
  const hits = TL.words.filter(w => w.scene === CUR.s.name && w.w.toLowerCase().includes(tok.toLowerCase()));
  const w = hits[Math.min(nth, hits.length - 1)];
  if (!w) console.error('token not found', CUR.s.name, tok);
  return (w ? w.t0 : CUR.s.start + 1) + off;
};
const o = (x = {}) => ({ stroke: INK, strokeWidth: 3.2, roughness: 1.3, bowing: 1.1, seed: seed++, ...x });

function draw(node, t0, dur = 0.9, color = null) {
  CUR.g.appendChild(node);
  const paths = [...node.querySelectorAll('path')];
  const lens = paths.map(p => (p.getAttribute('fill') && p.getAttribute('fill') !== 'none') ? 0 : p.getTotalLength());
  paths.forEach((p, i) => { if (lens[i]) { p.style.strokeDasharray = `${lens[i]} ${lens[i]}`; p.style.strokeDashoffset = lens[i]; } else p.style.opacity = 0; });
  CUR.items.push({ kind: 'paths', node, paths, lens, total: lens.reduce((a, b) => a + b, 0) || 1, t0, dur, color: color || INK });
  return node;
}
function text(str, x, y, size, color, t0, dur = null, anchor = 'start', rot = 0) {
  const tx = document.createElementNS(NS, 'text');
  tx.setAttribute('x', x); tx.setAttribute('y', y); tx.setAttribute('font-size', size); tx.setAttribute('fill', color); tx.setAttribute('text-anchor', anchor);
  tx.textContent = str;
  const g = document.createElementNS(NS, 'g'); if (rot) g.setAttribute('transform', `rotate(${rot} ${x} ${y})`);
  g.appendChild(tx); CUR.g.appendChild(g);
  const bb = tx.getBBox();
  const cid = 'c' + (seed++); const cp = document.createElementNS(NS, 'clipPath'); cp.id = cid;
  const r = document.createElementNS(NS, 'rect'); r.setAttribute('x', bb.x - 4); r.setAttribute('y', bb.y - 10); r.setAttribute('height', bb.height + 20); r.setAttribute('width', 0);
  cp.appendChild(r); g.appendChild(cp); tx.setAttribute('clip-path', `url(#${cid})`);
  CUR.items.push({ kind: 'text', node: g, tx, r, bb, t0, dur: dur ?? Math.min(1.4, 0.25 + str.length * 0.045), color });
  return g;
}
const rocket = (x, y, h, extra = {}) => {   // nose at (x,y), height h
  const w = h * 0.22, b = y + h;
  return `M ${x} ${y} C ${x + w * 0.6} ${y + h * 0.12} ${x + w / 2} ${y + h * 0.25} ${x + w / 2} ${y + h * 0.3} L ${x + w / 2} ${b - h * 0.08} L ${x + w} ${b} L ${x - w} ${b} L ${x - w / 2} ${b - h * 0.08} L ${x - w / 2} ${y + h * 0.3} C ${x - w / 2} ${y + h * 0.25} ${x - w * 0.6} ${y + h * 0.12} ${x} ${y} Z`;
};
const arrow = (x1, y1, x2, y2, t0, col = INK) => {
  draw(rc.line(x1, y1, x2, y2, o({ stroke: col })), t0, 0.45, col);
  const a = Math.atan2(y2 - y1, x2 - x1), L = 22;
  draw(rc.linearPath([[x2 - L * Math.cos(a - 0.45), y2 - L * Math.sin(a - 0.45)], [x2, y2], [x2 - L * Math.cos(a + 0.45), y2 - L * Math.sin(a + 0.45)]], o({ stroke: col })), t0 + 0.4, 0.25, col);
};
const check = (x, y, s, t0, col = GREEN) => draw(rc.linearPath([[x, y], [x + s * 0.35, y + s * 0.4], [x + s, y - s * 0.5]], o({ stroke: col, strokeWidth: 6 })), t0, 0.5, col);
const cross = (x, y, s, t0, col = RED, w = 6) => { draw(rc.line(x, y, x + s, y + s, o({ stroke: col, strokeWidth: w })), t0, 0.3, col); draw(rc.line(x + s, y, x, y + s, o({ stroke: col, strokeWidth: w })), t0 + 0.3, 0.3, col); };
const sat = (x, y, s, t0, col = INK) => { draw(rc.rectangle(x - s * 0.3, y - s * 0.3, s * 0.6, s * 0.6, o({ stroke: col, strokeWidth: 2.4 })), t0, 0.25, col); draw(rc.rectangle(x - s * 1.3, y - s * 0.18, s * 0.9, s * 0.36, o({ stroke: col, strokeWidth: 2, fill: '#9cc2ff', fillStyle: 'hachure', hachureGap: 5 })), t0 + 0.2, 0.25, col); draw(rc.rectangle(x + s * 0.4, y - s * 0.18, s * 0.9, s * 0.36, o({ stroke: col, strokeWidth: 2, fill: '#9cc2ff', fillStyle: 'hachure', hachureGap: 5 })), t0 + 0.35, 0.25, col); };
const highlight = (x, y, w, h, t0) => draw(rc.rectangle(x, y, w, h, { stroke: 'none', fill: YEL, fillStyle: 'zigzag', hachureGap: 7, fillWeight: 14, roughness: 1.6, seed: seed++ }), t0, 0.5, YEL);

// ------------------------------------------------------------------ scenes
if (EP === 'luftraum') {

const jet = (x, y, ang, sz, t0, col = RED) => {   // top-view jet, nose pointing to ang (rad)
  const P = [[0, -1], [0.12, -0.55], [0.12, -0.15], [0.75, 0.25], [0.75, 0.38], [0.12, 0.2], [0.1, 0.62], [0.35, 0.8], [0.35, 0.9], [0, 0.82], [-0.35, 0.9], [-0.35, 0.8], [-0.1, 0.62], [-0.12, 0.2], [-0.75, 0.38], [-0.75, 0.25], [-0.12, -0.15], [-0.12, -0.55]];
  const c = Math.cos(ang + Math.PI / 2), s_ = Math.sin(ang + Math.PI / 2);
  draw(rc.polygon(P.map(([px, py]) => [x + (px * c - py * s_) * sz, y + (px * s_ + py * c) * sz]), o({ stroke: col, strokeWidth: 2.4, fill: col, fillStyle: 'hachure', hachureGap: 4 })), t0, 0.5, col);
};
const ship = (x, y, w, t0, col = INK) => draw(rc.polygon([[x, y], [x + w, y], [x + w * 0.85, y + w * 0.28], [x + w * 0.12, y + w * 0.28]], o({ stroke: col, strokeWidth: 2.2 })), t0, 0.22, col);
const LAND = { stroke: '#2e5e3a', fill: '#cfe3c4', fillStyle: 'hachure', hachureGap: 7 };

CUR = SC.hook;
draw(rc.circle(200, 230, 260, o()), wt('4:07'), 0.8);
draw(rc.line(200, 230, 200, 125, o({ strokeWidth: 5 })), wt('4:07', 0, 0.5), 0.3); draw(rc.line(200, 230, 260, 210, o({ strokeWidth: 5 })), wt('4:07', 0, 0.7), 0.3);
text('4:07', 120, 440, 110, RED, wt('4:07', 0, 0.2));
text('Uhr · Japan', 105, 500, 46, INK, wt('japanische'));
draw(rc.path('M 560 120 q 40 -30 90 -10 t 90 20 t 60 60', o({ stroke: '#888', strokeWidth: 2 })), wt('geschlafen'), 0.6, '#888');
text('Zzz', 740, 120, 60, '#888', wt('geschlafen', 0, 0.3));
draw(rc.path('M 470 520 Q 520 380 640 330 Q 760 290 880 330 Q 820 420 700 470 Q 600 520 470 520 Z', o(LAND)), wt('Japans', 0, -0.4), 0.8, '#2e5e3a');
text('JAPAN', 620, 450, 50, '#2e5e3a', wt('Japans', 0, -0.1));
draw(rc.path('M 440 560 Q 520 300 700 270 Q 860 250 920 300', o({ stroke: RED, strokeLineDash: [12, 9] })), wt('Luftraum', 0, -0.2), 0.6, RED);
jet(560, 240, 2.2, 34, wt('russische')); jet(640, 200, 2.2, 34, wt('Militärflugzeuge'));
text('nicht umgekehrt!', 420, 650, 64, RED, wt('nicht', 0, -0.1));

CUR = SC.route;
// map: Korea, Japan (Kyushu/Honshu), Taiwan, Yonaguni
draw(rc.path('M 170 40 Q 230 60 240 140 Q 250 230 210 300 Q 170 320 150 260 Q 130 160 170 40 Z', o(LAND)), SC.route.s.start + 0.1, 0.7, '#2e5e3a');
draw(rc.path('M 330 330 Q 380 290 420 300 Q 440 360 400 410 Q 350 420 330 330 Z', o(LAND)), SC.route.s.start + 0.4, 0.6, '#2e5e3a');
draw(rc.path('M 420 290 Q 520 230 640 170 Q 760 110 860 40 L 880 70 Q 790 150 660 220 Q 540 280 440 320 Z', o(LAND)), SC.route.s.start + 0.6, 0.7, '#2e5e3a');
draw(rc.ellipse(170, 600, 70, 150, o(LAND)), SC.route.s.start + 0.9, 0.5, '#2e5e3a');
text('Korea', 110, 340, 36, '#2e5e3a', SC.route.s.start + 0.5); text('Japan', 640, 290, 40, '#2e5e3a', SC.route.s.start + 0.8); text('Taiwan', 60, 700, 38, '#2e5e3a', SC.route.s.start + 1.0);
draw(rc.circle(330, 250, 14, o({ stroke: RED, fill: RED, fillStyle: 'solid' })), wt('Okinoshima'), 0.3, RED);
text('Okinoshima · 3 min', 345, 225, 40, RED, wt('Okinoshima', 0, 0.1));
draw(rc.path('M 560 40 Q 430 120 330 250', o({ stroke: RED, strokeWidth: 4, strokeLineDash: [14, 9] })), wt('Drei', 0, 0), 0.8, RED);
jet(470, 330, -0.6, 22, wt('Abfangjäger'), BLUE); jet(510, 360, -0.6, 22, wt('Abfangjäger', 0, 0.2), BLUE);
text('Funkwarnung', 520, 410, 36, BLUE, wt('Warnungen', 0, -0.2));
draw(rc.path('M 330 250 Q 290 280 285 330', o({ stroke: RED, strokeWidth: 4, strokeLineDash: [14, 9] })), wt('Tsushima', 0, -0.3), 0.5, RED);
text('Tsushima', 200, 395, 34, INK, wt('Tsushima'));
jet(120, 210, 0.8, 18, wt('Südkorea'), BLUE); text('Südkorea: Jets ↑', 20, 180, 32, BLUE, wt('Jets', 0, -0.3));
draw(rc.path('M 285 330 Q 300 450 245 560', o({ stroke: RED, strokeWidth: 4, strokeLineDash: [14, 9] })), wt('Lücke', 0, -0.3), 0.6, RED);
draw(rc.circle(265, 585, 12, o({ fill: INK, fillStyle: 'solid' })), wt('Yonaguni', 0, -0.2), 0.2); text('Yonaguni', 280, 595, 32, INK, wt('Yonaguni'));
draw(rc.path('M 245 560 Q 225 620 250 660', o({ stroke: RED, strokeWidth: 4, strokeLineDash: [14, 9] })), wt('Ostküste', 0, -0.4), 0.5, RED);
text('Taiwan ortet', 20, 520, 34, INK, wt('ortet', 0, -0.1));
arrow(255, 665, 640, 650, wt('Pazifik', 0, -0.4), RED); text('Pazifik', 650, 665, 48, BLUE, wt('Pazifik'));
text('Moskau: …', 600, 560, 56, INK, wt('Moskau')); draw(rc.line(640, 520, 860, 520, o({ stroke: '#888' })), wt('Schweigt'), 0.3, '#888');

CUR = SC.china;
text('100+', 60, 160, 130, RED, wt('100'));
for (let i = 0; i < 18; i++) ship(330 + (i % 6) * 95, 70 + Math.floor(i / 6) * 60, 70, wt('Kriegs') + i * 0.07);
text('Schiffe im Westpazifik', 330, 290, 46, INK, wt('Westpazifik', 0, -0.2));
text('ohne Ankündigung', 330, 340, 40, RED, wt('Ankündigung', 0, -0.3));
draw(rc.ellipse(230, 560, 300, 70, o({ fill: '#555c6a', fillStyle: 'hachure', hachureGap: 6 })), wt('U-Boot', 0, -0.2), 0.6);
draw(rc.rectangle(215, 500, 50, 30, o()), wt('U-Boot', 0, 0.2), 0.3);
draw(rc.path('M 240 495 Q 260 380 340 380', o({ stroke: RED, strokeLineDash: [10, 8] })), TL.events.rakete, 0.6, RED);
draw(rc.path(rocket(340, 350, 70), o({ stroke: RED })), TL.events.rakete + 0.4, 0.4, RED);
text('ICBM?', 400, 420, 70, RED, TL.events.rakete + 0.5);
text('„sagt ein Beamter“', 420, 480, 38, INK, wt('Beamter', 0, -0.3));
{ const st = document.createElementNS(NS, 'g'); st.setAttribute('transform', 'rotate(-8 710 600)'); CUR.g.appendChild(st);
  const n = rc.rectangle(560, 560, 300, 80, o({ stroke: '#e0a100', strokeWidth: 6 })); st.appendChild(n); draw(n, wt('nicht', 0, -0.1), 0.4, '#e0a100'); st.appendChild(CUR.g.lastChild);
  text('UNBESTÄTIGT', 710, 620, 58, '#e0a100', wt('nicht', 0, 0.2), 0.5, 'middle', -8); }

CUR = SC.timing;
draw(rc.rectangle(60, 60, 220, 220, o()), wt('Zeitpunkt'), 0.6); draw(rc.rectangle(60, 60, 220, 55, o({ stroke: RED, fill: RED, fillStyle: 'hachure', hachureGap: 6 })), wt('Zeitpunkt', 0, 0.4), 0.4, RED);
text('19.11.', 75, 220, 80, INK, wt('19. November', 0, -0.2));
draw(rc.circle(640, 330, 260, o({ fill: '#c9b38a', fillStyle: 'hachure', hachureGap: 9 })), wt('Stunden'), 0.7);
[['Trump', 640, 150], ['Xi', 820, 400], ['Putin', 460, 400]].forEach(([n, x, y], i) => { draw(rc.circle(x, y, 60, o({ stroke: BLUE })), wt(n === 'Xi' ? 'Xi' : n), 0.3, BLUE); text(n, x, y + (y < 300 ? -45 : 75), 44, BLUE, wt(n === 'Xi' ? 'Xi' : n, 0, 0.1), 0.4, 'middle'); });
text('Shenzhen', 640, 340, 48, RED, wt('Shenzhen'), 0.6, 'middle');
draw(rc.circle(640, 560, 60, o({ stroke: '#888', strokeLineDash: [8, 8] })), wt('Europa', 0, -0.2), 0.4, '#888');
text('Europa?', 640, 650, 50, '#888', wt('Europa'), 0.5, 'middle'); cross(615, 535, 50, wt('Tisch'), RED, 5);

CUR = SC.decode;
text('„Cyberangriffe!“', 60, 140, 80, INK, wt('Cyberangriffe', 0, -0.3));
draw(rc.circle(780, 160, 150, o({ stroke: BLUE, strokeWidth: 5 })), wt('geprüft', 0, -0.3), 0.5, BLUE); draw(rc.line(835, 215, 910, 290, o({ stroke: BLUE, strokeWidth: 9 })), wt('geprüft'), 0.3, BLUE);
text('Behörden: technischer Fehler', 60, 330, 58, BLUE, wt('Behörden'));
text('≠ Angriff', 60, 410, 70, RED, wt('Angriff'));
highlight(60, 520, 560, 80, wt('Geschichte', 0, -0.3));
text('Geschichte ≠ Analyse', 70, 585, 72, INK, wt('Geschichte', 0, -0.2));

CUR = SC.fazit;
text('Russland', 60, 170, 64, RED, wt('Russland')); text('China', 60, 330, 64, RED, wt('China'));
[['Washington', 160], ['Tokio', 300], ['Taipeh', 440]].forEach(([n, y]) => { arrow(330, 240, 580, y - 15, wt(n, 0, -0.3)); text(n, 600, y, 56, BLUE, wt(n)); });
draw(rc.path('M 300 200 q 15 40 0 80', o({ stroke: RED })), wt('zeigen'), 0.3, RED); draw(rc.path('M 320 185 q 25 55 0 110', o({ stroke: RED })), wt('zeigen', 0, 0.15), 0.3, RED);
highlight(60, 560, 840, 90, wt('Verhandlungsposition', 0, -0.5));
text('= Verhandlungsposition', 80, 630, 76, INK, wt('Verhandlungsposition', 0, -0.4));
text('kein geheimer Plan', 60, 520, 46, '#888', wt('geheimer', 0, -0.2));

CUR = SC.cta;
highlight(150, 170, 660, 120, wt('Prüf', 0, -0.3));
text('PRÜF MICH!', 480, 270, 130, RED, wt('Prüf', 0, -0.1), 0.7, 'middle');
draw(rc.ellipse(480, 225, 760, 210, o({ stroke: RED, strokeWidth: 5 })), wt('mich', 0, 0.2), 0.6, RED);
text('Quellen ↓ in der Beschreibung', 480, 460, 58, INK, wt('Quellen'), 1.0, 'middle');
text('Nächste Folge: nach Shenzhen', 480, 600, 54, BLUE, wt('Shenzhen', 0, -0.2), 0.9, 'middle');

} else {
CUR = SC.hook;
draw(rc.circle(170, 200, 210, o()), wt('48'), 0.8); draw(rc.linearPath([[170, 200], [170, 125]], o({ stroke: RED })), wt('48', 0, 0.6), 0.3, RED); draw(rc.linearPath([[170, 200], [225, 230]], o()), wt('48', 0, 0.8), 0.3);
text('48 h', 95, 370, 96, RED, wt('48', 0, 0.3));
draw(rc.path(rocket(450, 110, 220), o({ fill: '#dfe4ea', fillStyle: 'hachure', hachureGap: 8 })), wt('Raumschiff'), 1.0);
for (const y of [115, 330]) draw(rc.line(530, y, 530, 400, o()), wt('Raumschiff', 0, 0.6), 0.4);
draw(rc.line(530, 400, 600, 400, o()), wt('Raumschiff', 0, 0.9), 0.2);
draw(rc.line(490, 230, 560, 230, o({ stroke: BLUE, strokeWidth: 5 })), wt('Stäbchen'), 0.3, BLUE); draw(rc.line(490, 262, 560, 262, o({ stroke: BLUE, strokeWidth: 5 })), wt('Stäbchen', 0, 0.15), 0.3, BLUE);
text('gefangen', 395, 455, 54, GREEN, wt('gefangen')); check(560, 430, 50, wt('gefangen', 0, 0.6));
[[700, 150], [800, 130], [880, 200], [730, 250], [840, 290], [770, 340]].forEach(([x, y], i) => sat(x, y, 26, wt('40') + i * 0.12));
cross(680, 110, 240, wt('Minuten'), RED, 7);
text('−40', 760, 420, 80, RED, wt('Minuten', 0, 0.5));
highlight(140, 560, 690, 70, wt('Himmel', 0, -0.3));
text('WEM GEHÖRT DER HIMMEL?', 480, 615, 78, RED, wt('Himmel', 0, -0.2), 1.0, 'middle');
draw(rc.path('M 150 650 Q 300 680 480 655 T 820 650', o({ stroke: RED, strokeWidth: 4 })), wt('gehört', 0, 0.4), 0.5, RED);

CUR = SC.starship;
text('TEXAS · 14.11.', 40, 80, 52, BLUE, wt('Freitag'));
draw(rc.path('M 900 120 Q 780 40 640 130 T 470 200', o({ stroke: BLUE, strokeLineDash: [14, 10] })), wt('Orbit', 0, -0.2), 0.9, BLUE);
text('Orbit', 800, 80, 48, BLUE, wt('Orbit', 0, 0.3));
draw(rc.line(560, 230, 560, 650, o({ strokeWidth: 4 })), wt('Armen'), 0.4); draw(rc.line(620, 230, 620, 650, o({ strokeWidth: 4 })), wt('Armen', 0, 0.2), 0.4);
draw(rc.linearPath([[560, 650], [620, 600], [560, 550], [620, 500], [560, 450], [620, 400], [560, 350], [620, 300], [560, 250]], o({ strokeWidth: 2 })), wt('Armen', 0, 0.4), 0.8);
draw(rc.line(560, 330, 440, 330, o({ stroke: RED, strokeWidth: 6 })), wt('Startturms', 0, -0.2), 0.3, RED); draw(rc.line(560, 370, 440, 370, o({ stroke: RED, strokeWidth: 6 })), wt('Startturms'), 0.3, RED);
draw(rc.path(rocket(470, 205, 300), o({ fill: '#dfe4ea', fillStyle: 'hachure', hachureGap: 8 })), wt('Starship'), 1.1);
check(690, 330, 80, wt('Startturms', 0, 0.5));
text('22 h im All', 680, 460, 60, INK, wt('22'));
text('+26 Starlink', 680, 540, 50, BLUE, wt('26'));
[[860, 500], [910, 560]].forEach(([x, y], i) => sat(x, y, 18, wt('26', 0, 0.5 + i * 0.2), BLUE));
draw(rc.path('M 40 640 q 30 -18 60 0 t 60 0 t 60 0 t 60 0 t 60 0 t 60 0', o({ stroke: BLUE })), wt('Booster'), 0.7, BLUE);
draw(rc.path('M 40 680 q 30 -18 60 0 t 60 0 t 60 0 t 60 0 t 60 0 t 60 0', o({ stroke: BLUE })), wt('Booster', 0, 0.3), 0.7, BLUE);
draw(rc.rectangle(140, 560, 44, 110, o()), wt('Meer'), 0.5).setAttribute('transform', 'rotate(28 162 615)');
text('Booster → Meer', 40, 540, 46, INK, wt('Booster', 0, 0.2));
text('Signal: eindeutig!', 640, 650, 56, RED, wt('Signal'));

CUR = SC.vulcan;
text('FLORIDA · 15.11.', 40, 80, 52, BLUE, wt('Florida'));
draw(rc.path(rocket(170, 140, 360), o({ fill: '#f2b56b', fillStyle: 'hachure', hachureGap: 9 })), wt('Vulcan'), 1.1);
draw(rc.rectangle(105, 330, 22, 150, o()), wt('Vulcan', 0, 0.7), 0.4); draw(rc.rectangle(213, 330, 22, 150, o()), wt('Vulcan', 0, 0.9), 0.4);
draw(rc.path('M 140 505 Q 170 590 200 505', o({ stroke: '#e07a10', fill: '#ffcf70', fillStyle: 'hachure' })), wt('ULA'), 0.5, '#e07a10');
text('ULA = Boeing + Lockheed', 320, 150, 50, INK, wt('Boeing', 0, -0.3));
for (let i = 0; i < 40; i++) { const cx = 330 + (i % 8) * 64, cy = 200 + Math.floor(i / 8) * 56; draw(rc.rectangle(cx, cy, 42, 36, o({ strokeWidth: 2.2, roughness: 1.6 })), wt('40') + i * 0.035, 0.18); }
text('40 Satelliten', 330, 505, 46, INK, wt('Satelliten'));
const an = TL.events.anomaly;
draw(rc.polygon([[170, 80], [195, 135], [255, 115], [215, 165], [270, 205], [205, 205], [195, 265], [165, 210], [105, 235], [140, 180], [90, 140], [150, 140]], o({ stroke: RED, fill: '#ffb3a0', fillStyle: 'cross-hatch', hachureGap: 8 })), an, 0.5, RED);
text('ANOMALIE!', 40, 600, 66, RED, an + 0.3, 0.7);
cross(320, 190, 510, wt('verloren'), RED, 9);
draw(rc.rectangle(330, 600, 580, 46, o()), wt('400', 0, -0.2), 0.5);
draw(rc.rectangle(333, 603, 72, 40, { stroke: 'none', fill: '#ff9a30', fillStyle: 'hachure', hachureGap: 6, seed: seed++ }), wt('400'), 0.5, '#ff9a30');
text('398 / 3.236', 330, 700, 52, INK, wt('3.200', 0, -0.4));

CUR = SC.connect;
[[70, 120], [170, 70], [260, 140]].forEach(([x, y], i) => draw(rc.circle(x, y, 18, o({ fill: INK, fillStyle: 'solid' })), wt('verbinde') + i * 0.15, 0.2));
draw(rc.linearPath([[70, 120], [170, 70], [260, 140]], o({ stroke: RED })), wt('Punkte'), 0.6, RED);
const box = (x, y, w, label, t0, col = INK, fill = null) => { draw(rc.rectangle(x, y, w, 100, o({ stroke: col, ...(fill ? { fill, fillStyle: 'hachure', hachureGap: 7 } : {}) })), t0, 0.6, col); text(label, x + w / 2, y + 66, 50, col, t0 + 0.3, 0.6, 'middle'); };
box(40, 230, 250, 'Satelliten', wt('Satelliten', 0, -0.2));
arrow(300, 280, 360, 280, wt('Internet', 0, -0.2)); box(370, 230, 240, 'Internet', wt('Internet'));
arrow(620, 280, 680, 280, wt('entscheidet', 0, -0.4)); box(690, 230, 230, 'MACHT', wt('entscheidet'), RED, '#ffc2c2');
draw(rc.path('M 60 600 A 150 150 0 0 1 360 600', o({ strokeWidth: 5 })), wt('Ukraine'), 0.6);
draw(rc.path('M 300 520 A 150 150 0 0 1 360 600', o({ stroke: RED, strokeWidth: 9 })), wt('Starlink', 0, 0.2), 0.4, RED);
draw(rc.line(210, 600, 335, 540, o({ stroke: RED, strokeWidth: 5 })), wt('161'), 0.4, RED);
text('161 km/h → AUS', 400, 560, 60, RED, wt('161', 0, 0.2));
text('Europa: Alternative?', 400, 640, 50, BLUE, wt('Europa'));
text('größter Herausforderer:', 400, 705, 42, INK, wt('Herausforderer', 0, -0.2)); cross(830, 665, 40, wt('gescheitert'), RED, 6);

CUR = SC.genf;
text('GENF · HEUTE', 40, 80, 52, BLUE, wt('Genf'));
draw(rc.ellipse(230, 260, 300, 150, o({ fill: '#c9b38a', fillStyle: 'hachure', hachureGap: 9 })), wt('Vertreter'), 0.7);
for (let i = 0; i < 16; i++) { const a = i / 16 * Math.PI * 2; draw(rc.circle(230 + Math.cos(a) * 185, 260 + Math.sin(a) * 105, 20, o({ strokeWidth: 2 })), wt('128') + i * 0.04, 0.15); }
text('128 Staaten', 110, 420, 56, INK, wt('Staaten'));
draw(rc.rectangle(590, 200, 120, 50, o({ fill: '#555c6a', fillStyle: 'hachure', hachureGap: 6 })), wt('Killerroboter', 0, -0.3), 0.5);
for (const [x, y] of [[540, 180], [760, 180]]) { draw(rc.line(x + (x < 600 ? 20 : -20), y + 10, x < 600 ? 590 : 710, 215, o()), wt('Killerroboter'), 0.3); draw(rc.ellipse(x, y, 90, 22, o()), wt('Killerroboter', 0, 0.2), 0.3); }
draw(rc.circle(650, 270, 22, o({ stroke: RED, fill: RED, fillStyle: 'solid' })), wt('Killerroboter', 0, 0.5), 0.2, RED);
draw(rc.circle(650, 390, 90, o({ stroke: RED })), wt('Waffen'), 0.5, RED);
draw(rc.line(650, 330, 650, 450, o({ stroke: RED, strokeWidth: 2 })), wt('Waffen', 0, 0.4), 0.2, RED); draw(rc.line(590, 390, 710, 390, o({ stroke: RED, strokeWidth: 2 })), wt('Waffen', 0, 0.5), 0.2, RED);
text('entscheidet selbst', 520, 500, 46, RED, wt('selbst', 0, -0.2));
draw(rc.circle(85, 560, 40, o()), wt('menschliche', 0, -0.3), 0.3); draw(rc.linearPath([[85, 580], [85, 640], [60, 690]], o()), wt('menschliche', 0, -0.1), 0.3); draw(rc.line(85, 640, 110, 690, o()), wt('menschliche'), 0.2); draw(rc.line(55, 605, 115, 605, o()), wt('menschliche', 0, 0.1), 0.2);
text('menschliche Kontrolle', 140, 640, 54, INK, wt('menschliche', 0, 0.1));
draw(rc.line(135, 625, 560, 615, o({ stroke: RED, strokeWidth: 6 })), wt('streichen'), 0.4, RED);
{ const st = document.createElementNS(NS, 'g'); st.setAttribute('transform', 'rotate(-8 740 640)'); CUR.g.appendChild(st);
  const n = rc.rectangle(600, 600, 290, 80, o({ stroke: '#e0a100', strokeWidth: 6 })); st.appendChild(n); draw(n, wt('nicht', 0, -0.1), 0.4, '#e0a100'); st.appendChild(CUR.g.lastChild);
  text('UNBESTÄTIGT', 745, 660, 58, '#e0a100', wt('nicht', 0, 0.2), 0.5, 'middle', -8); }

CUR = SC.verdict;
text('Verschwörung?', 60, 150, 84, INK, wt('Verschwörung'));
draw(rc.line(50, 120, 520, 125, o({ stroke: RED, strokeWidth: 7 })), wt('Nein'), 0.35, RED);
text('NEIN.', 600, 150, 90, RED, wt('Nein', 0, 0.1));
text('Physik + Geld', 60, 340, 92, BLUE, wt('Physik'));
text('= Kontrolle', 540, 340, 92, RED, wt('kontrolliert', 0, -0.2));
draw(rc.ellipse(720, 310, 400, 130, o({ stroke: RED })), wt('Infrastruktur'), 0.6, RED);
draw(rc.circle(170, 560, 110, o({ stroke: '#b8860b', strokeWidth: 6 })), wt('Schlüssel', 0, -0.3), 0.5, '#b8860b');
draw(rc.line(225, 560, 430, 560, o({ stroke: '#b8860b', strokeWidth: 8 })), wt('Schlüssel'), 0.4, '#b8860b');
draw(rc.linearPath([[380, 560], [380, 605], [410, 605], [410, 560]], o({ stroke: '#b8860b', strokeWidth: 6 })), wt('Schlüssel', 0, 0.3), 0.3, '#b8860b');
highlight(520, 530, 330, 80, wt('Firma', 0, -0.4));
text('1 Firma?', 540, 595, 90, INK, wt('Firma', 0, -0.2));

CUR = SC.cta;
highlight(150, 170, 660, 120, wt('Prüf', 0, -0.3));
text('PRÜF MICH!', 480, 270, 130, RED, wt('Prüf', 0, -0.1), 0.7, 'middle');
draw(rc.ellipse(480, 225, 760, 210, o({ stroke: RED, strokeWidth: 5 })), wt('mich', 0, 0.2), 0.6, RED);
text('Quellen ↓ in der Beschreibung', 480, 460, 58, INK, wt('Quellen'), 1.0, 'middle');
draw(rc.rectangle(230, 540, 60, 60, o({ stroke: BLUE })), wt('Folg', 0, -0.2), 0.4, BLUE); check(240, 575, 50, wt('Folg', 0, 0.3), GREEN);
text('Folgen – morgen geht’s weiter', 310, 595, 54, BLUE, wt('Folg', 0, 0.1));

}
// ------------------------------------------------------------------ pen
const pen = document.createElementNS(NS, 'g');
pen.innerHTML = `<g transform="rotate(-35)"><rect x="-7" y="-150" width="22" height="120" rx="6" fill="#2a2f3a"/><rect x="-7" y="-150" width="22" height="34" rx="6" class="cap"/><path d="M -7 -30 L 15 -30 L 6 -4 L 2 -4 Z" fill="#d9dde3"/><path d="M 2 -4 L 6 -4 L 4 2 Z" class="tip"/></g>`;
penLayer.appendChild(pen);
const penCap = pen.querySelector('.cap'), penTip = pen.querySelector('.tip');

function sceneAt(t) { let s = TL.scenes[0]; for (const x of TL.scenes) if (t >= x.start - 0.05) s = x; return s; }
const toSvg = (el, x, y) => { const p = svg.createSVGPoint(); p.x = x; p.y = y; const m = el.getCTM(); const r = svg.getCTM(); return p.matrixTransform(m).matrixTransform(r.inverse()); };

window.renderAt = (t) => {
  const s = sceneAt(t);
  // board drop-in at start, gentle sway, page "flip" at scene changes
  const t0 = TL.scenes[0].start;
  const drop = back((t - t0 + 0.2) / 0.7);
  const ls = t - s.start, flip = s !== TL.scenes[0] ? clamp(ls / 0.35) : 1;
  board.style.transform = `translateY(${(1 - drop) * -820}px) rotate(${Math.sin(t * 0.5) * 0.35 - 0.6}deg) scaleY(${0.92 + 0.08 * ease(flip)})`;
  let penPos = null, penCol = INK, latest = -1;
  for (const k in SC) {
    const sc = SC[k]; const vis = sc.s === s; sc.g.style.display = vis ? '' : 'none'; if (!vis) continue;
    for (const it of sc.items) {
      const p = clamp((t - it.t0) / it.dur);
      if (it.kind === 'paths') {
        let L = p * it.total, cur = null;
        it.paths.forEach((pa, i) => {
          if (!it.lens[i]) { pa.style.opacity = p > 0.6 ? Math.min(1, (p - 0.6) / 0.4) : 0; return; }
          const v = clamp(L, 0, it.lens[i]); L -= it.lens[i];
          pa.style.strokeDashoffset = it.lens[i] - v;
          if (v > 0 && v < it.lens[i]) cur = [pa, v];
        });
        if (p > 0 && p < 1 && cur && it.t0 >= latest) { const pt = cur[0].getPointAtLength(cur[1]); penPos = toSvg(cur[0], pt.x, pt.y); penCol = it.color; latest = it.t0; }
      } else {
        it.r.setAttribute('width', (it.bb.width + 8) * p);
        if (p > 0 && p < 1 && it.t0 >= latest) { penPos = toSvg(it.tx, it.bb.x + it.bb.width * p, it.bb.y + it.bb.height * 0.72); penCol = it.color; latest = it.t0; }
      }
    }
  }
  if (penPos) { pen.style.display = ''; pen.setAttribute('transform', `translate(${penPos.x} ${penPos.y})`); penCap.setAttribute('fill', penCol); penTip.setAttribute('fill', penCol); }
  else pen.style.display = 'none';
  return true;
};
window.READY = true;
