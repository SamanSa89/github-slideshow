// Hand-drawn "Leinwand" (canvas) layer: marker sketches drawn stroke by stroke, synced to word timings.
// window.renderAt(t) updates the drawing for time t (deterministic).
import rough from 'roughjs';

const PRM = new URLSearchParams(location.search); const EP = PRM.get('ep') || '';
const TL = await (await fetch(PRM.get('tl') || './work/timeline.json')).json();
await document.fonts.load('700 40px Caveat');
const NS = 'http://www.w3.org/2000/svg';
const svg = document.getElementById('svg'), board = document.getElementById('board');
const PORTRAIT = PRM.get('portrait') === '1';   // tall board for the PIP layout: 960x1080
const BH = PORTRAIT ? 1080 : 720;
if (PORTRAIT) { document.getElementById('stage').style.height = '1170px'; board.style.height = BH + 'px'; svg.setAttribute('height', BH); svg.setAttribute('viewBox', `0 0 960 ${BH}`); }
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
// ---- OpenMoji picture icons (CC BY-SA 4.0, openmoji.org), inlined SVG, pop-in animation
const ICON_LOADS = [];
function icon(code, x, y, size, t0, rot = 0) {
  const g = document.createElementNS(NS, 'g'); g.style.opacity = 0; CUR.g.appendChild(g);
  ICON_LOADS.push(fetch(`./node_modules/openmoji/color/svg/${code}.svg`).then(r => r.text()).then(txt => {
    const doc = new DOMParser().parseFromString(txt, 'image/svg+xml'); const root = doc.documentElement;
    for (const ch of [...root.childNodes]) g.appendChild(document.importNode(ch, true));
  }));
  CUR.items.push({ kind: 'icon', node: g, x, y, size, rot, t0, dur: 0.35 });
  return g;
}
if (EP === 'shenzhen_en') {
const seat = (x, y, label, col, t0, below = true) => { draw(rc.circle(x, y, 70, o({ stroke: col, strokeWidth: 4 })), t0, 0.35, col); text(label, x, below ? y + 75 : y - 50, 44, col, t0 + 0.15, 0.4, 'middle'); };
const stamp = (txt, cx, cy, w, col, t0, rot = -7) => { const st = document.createElementNS(NS, 'g'); st.setAttribute('transform', `rotate(${rot} ${cx} ${cy})`); CUR.g.appendChild(st);
  const n = rc.rectangle(cx - w / 2, cy - 45, w, 90, o({ stroke: col, strokeWidth: 7 })); st.appendChild(n); draw(n, t0, 0.35, col); st.appendChild(CUR.g.lastChild);
  text(txt, cx, cy + 20, 56, col, t0 + 0.2, 0.45, 'middle', rot); };

CUR = SC.hook;
draw(rc.circle(480, 290, 300, o({ fill: '#c9b38a', fillStyle: 'hachure', hachureGap: 9 })), wt('Trump', 0, -0.3), 0.7);
seat(480, 95, 'Trump', BLUE, wt('Trump'), false); seat(290, 410, 'Xi', RED, wt('Xi')); seat(670, 410, 'Putin', RED, wt('Putin'));
text('SHENZHEN', 480, 305, 60, RED, wt('Shenzhen', 0, -0.2), 0.6, 'middle');
highlight(250, 590, 460, 80, wt('lost', 0, -0.3));
text('Trump lost?', 480, 655, 80, INK, wt('lost', 0, -0.2), 0.6, 'middle');
text('let’s decode →', 700, 700, 40, BLUE, wt('decode'), 0.6);

icon('1F1FA-1F1F8', 480, 95, 62, wt('Trump', 0, 0.1)); icon('1F1E8-1F1F3', 290, 410, 62, wt('Xi', 0, 0.1)); icon('1F1F7-1F1FA', 670, 410, 62, wt('Putin', 0, 0.1));
icon('1F4F1', 820, 520, 150, wt('Viral', 0, -0.1), -10); icon('1F525', 905, 430, 90, wt('Viral', 0, 0.2));
icon('1F50E', 905, 630, 80, wt('decode', 0, 0.2));
CUR = SC.before;
draw(rc.rectangle(60, 60, 200, 170, o()), wt('earlier', 0, -0.4), 0.5); draw(rc.rectangle(60, 60, 200, 45, o({ stroke: RED, fill: RED, fillStyle: 'hachure', hachureGap: 6 })), wt('earlier', 0, -0.1), 0.3, RED);
text('Nov 18', 75, 185, 64, INK, wt('earlier'));
seat(380, 170, 'Xi', RED, wt('Xi')); seat(600, 170, 'Putin', RED, wt('Putin'));
draw(rc.line(415, 170, 565, 170, o({ stroke: RED, strokeWidth: 5 })), wt('Putin', 0, 0.3), 0.4, RED);
text('LEAD → multipolar world', 60, 360, 56, RED, wt('lead', 0, -0.2));
draw(rc.path('M 300 560 L 400 430 L 450 480 L 520 400 L 640 560 Z', o({ fill: '#b7c7a6', fillStyle: 'hachure', hachureGap: 8 })), wt('mountain', 0, -0.5), 0.7);
text('“steady as a mountain”', 300, 610, 46, INK, wt('mountain', 0, -0.1));
text('Nov 19: Trump arrives →', 470, 690, 46, BLUE, wt('American', 0, -0.4));

icon('1F1E8-1F1F3', 380, 170, 62, wt('Xi', 0, 0.1)); icon('1F1F7-1F1FA', 600, 170, 62, wt('Putin', 0, 0.1));
icon('1F91D', 490, 285, 120, wt('Putin', 0, 0.5)); icon('1F3D4', 800, 470, 170, wt('mountain', 0, -0.3));
icon('1F6EC', 405, 668, 80, wt('American', 0, -0.5));
CUR = SC.summit;
draw(rc.rectangle(60, 50, 330, 400, o({ fill: '#ffffff', fillStyle: 'solid' })), wt('three-way', 0, -0.2), 0.6);
text('Declaration', 90, 110, 48, INK, wt('four-point', 0, -0.3));
for (let i = 0; i < 4; i++) { text(`${i + 1}.`, 90, 180 + i * 70, 40, INK, wt('four-point') + i * 0.15, 0.2); draw(rc.line(130, 170 + i * 70, 360, 170 + i * 70, o({ strokeWidth: 2 })), wt('four-point') + i * 0.15, 0.3); }
text('nuclear risk', 450, 110, 50, INK, wt('nuclear', 0, -0.2)); check(760, 85, 46, wt('nuclear', 0, 0.4));
text('“no winners in a nuclear war”', 450, 170, 34, '#555', wt('won', 0, -0.4));
[['Ukraine', 'Ukraine', 250], ['Iran', 'Iran', 330], ['arsenal cuts', 'arsenals', 410]].forEach(([lab, tok, y]) => { text(lab, 450, y, 50, INK, wt(tok, 0, -0.2)); cross(760, y - 40, 44, wt(tok, 0, 0.2)); });
text('Putin: no direct talks with Kyiv', 60, 540, 46, RED, wt('Kyiv', 0, -0.6));
highlight(60, 590, 470, 95, wt('twelve', 0, -0.3));
text('Trump: “12 / 10”', 75, 665, 76, BLUE, wt('twelve', 0, -0.2));

icon('1F4C3', 340, 90, 80, wt('four-point', 0, -0.2), 8); icon('2622', 890, 95, 78, wt('nuclear', 0, 0.1));
icon('1F1FA-1F1E6', 890, 236, 78, wt('Ukraine', 0, 0.1)); icon('1F1EE-1F1F7', 890, 316, 78, wt('Iran', 0, 0.1));
icon('1F1F7-1F1FA', 885, 520, 72, wt('Kyiv', 0, -0.3)); icon('1F3C6', 650, 630, 130, wt('twelve', 0, 0.1));
CUR = SC.iran;
text('IRAN', 60, 110, 90, INK, wt('Iran', 0, -0.2));
text('UN Security Council · Sept 17', 60, 190, 46, BLUE, wt('September', 0, -0.2));
draw(rc.path('M 200 480 A 280 200 0 0 1 760 480', o({ strokeWidth: 6 })), wt('Beijing'), 0.6);
text('China', 230, 420, 54, RED, wt('China')); text('Russia', 600, 420, 54, RED, wt('Russia'));
text('US draft: monitor Iran sanctions', 120, 560, 46, INK, wt('Security', 0, -0.2));
draw(rc.line(110, 545, 760, 540, o({ stroke: RED, strokeWidth: 6 })), wt('sanctions', 0, 0.2), 0.4, RED);
stamp('VETO', 770, 110, 250, RED, TL.events.veto - 0.1, -9);

icon('1F1EE-1F1F7', 340, 72, 110, wt('Iran', 0, 0.1)); icon('1F1FA-1F1F3', 600, 160, 90, wt('September', 0, 0.2));
icon('1F1E8-1F1F3', 285, 335, 90, wt('China', 0, -0.1)); icon('1F1F7-1F1FA', 655, 335, 90, wt('Russia', 0, -0.1));
icon('1F1FA-1F1F8', 72, 545, 70, wt('Security', 0, -0.3));
CUR = SC.claims;
text('VIRAL CLAIM:', 60, 90, 56, RED, wt('viral', 0, -0.2));
text('“Xi greeted Trump at the airport”', 60, 170, 50, INK, wt('airport', 0, -0.8));
draw(rc.circle(820, 120, 120, o({ stroke: BLUE, strokeWidth: 5 })), wt('found', 0, -0.3), 0.4, BLUE); draw(rc.line(862, 162, 930, 230, o({ stroke: BLUE, strokeWidth: 9 })), wt('found'), 0.3, BLUE);
stamp('NO REPORT FOUND', 480, 280, 560, '#e0a100', wt('report', 0, -0.1), -5);
text('“A new G3 runs the world”?', 60, 440, 52, INK, wt('G3', 0, -0.4));
draw(rc.line(55, 425, 690, 420, o({ stroke: RED, strokeWidth: 6 })), wt('say', 0, 0.1), 0.4, RED);
highlight(60, 540, 520, 90, wt('risk', 0, -0.3));
text('= risk management', 75, 610, 70, INK, wt('risk', 0, -0.2));
text('(Chinese analysts)', 610, 610, 38, '#555', wt('risk', 0, 0.6));

icon('1F4F1', 480, 68, 90, wt('viral', 0, 0.1), -10); icon('1F525', 548, 58, 70, wt('viral', 0, 0.3));
icon('1F6EC', 115, 268, 84, wt('airport', 0, -0.2)); icon('1F30F', 815, 430, 130, wt('G3', 0, -0.2));
icon('1F6E1', 880, 560, 110, wt('risk', 0, 0.2));
CUR = SC.verdict;
text('Did Trump fail?', 60, 95, 64, INK, wt('fail', 0, -0.5));
draw(rc.line(480, 245, 480, 480, o({ strokeWidth: 6 })), wt('optics', 0, -0.4), 0.4); draw(rc.polygon([[430, 520], [530, 520], [480, 475]], o()), wt('optics', 0, -0.2), 0.3);
draw(rc.line(220, 270, 740, 220, o({ strokeWidth: 6 })), wt('optics', 0, -0.1), 0.4);
draw(rc.path('M 140 290 Q 220 400 300 290', o({ stroke: RED })), wt('optics'), 0.4, RED); text('OPTICS', 220, 450, 40, RED, wt('optics', 0, 0.2), null, 'middle'); text('→ Beijing', 220, 515, 52, RED, wt('Beijing'), null, 'middle');
draw(rc.path('M 660 240 Q 740 350 820 240', o({ stroke: BLUE })), wt('substance'), 0.4, BLUE); text('SUBSTANCE', 740, 400, 40, BLUE, wt('substance', 0, 0.2), null, 'middle'); text('→ nobody (yet)', 740, 465, 48, BLUE, wt('nobody'), null, 'middle');
highlight(60, 600, 840, 85, wt('three', 0, -0.4));
text('No G3 – but no deal without all 3', 75, 665, 60, INK, wt('three', 0, -0.3));

icon('1F1E8-1F1F3', 220, 300, 80, wt('Beijing', 0, 0.1)); icon('2753', 740, 252, 80, wt('nobody', 0, 0.1));
icon('1F1FA-1F1F8', 700, 552, 64, wt('three', 0, 0.1)); icon('1F1E8-1F1F3', 770, 552, 64, wt('three', 0, 0.2)); icon('1F1F7-1F1FA', 840, 552, 64, wt('three', 0, 0.3));
CUR = SC.cta;
highlight(150, 170, 660, 120, wt('Verify', 0, -0.3));
text('VERIFY ME!', 480, 270, 130, RED, wt('Verify', 0, -0.1), 0.7, 'middle');
draw(rc.ellipse(480, 225, 760, 210, o({ stroke: RED, strokeWidth: 5 })), wt('Verify', 0, 0.5), 0.6, RED);
text('Sources ↓ in the description', 480, 460, 58, INK, wt('Sources'), 1.0, 'middle');
text('THE DECODER', 480, 600, 64, BLUE, wt('Decoder', 0, -0.2), 0.8, 'middle');
icon('1F50E', 150, 445, 90, wt('Sources', 0, -0.2)); icon('270D', 800, 600, 90, wt('Decoder', 0, 0.1));

} else if (EP === 'kushner_en') {
const ORG = '#e0a100';
const stamp = (txt, cx, cy, w, col, t0, rot = -7, fs = 56) => { const st = document.createElementNS(NS, 'g'); st.setAttribute('transform', `rotate(${rot} ${cx} ${cy})`); CUR.g.appendChild(st);
  const n = rc.rectangle(cx - w / 2, cy - 45, w, 90, o({ stroke: col, strokeWidth: 7 })); st.appendChild(n); draw(n, t0, 0.35, col); st.appendChild(CUR.g.lastChild);
  text(txt, cx, cy + 20, fs, col, t0 + 0.2, 0.45, 'middle', rot); };
const node = (x, y, label, col, t0) => { draw(rc.circle(x, y, 120, o({ stroke: col, strokeWidth: 4 })), t0, 0.35, col); text(label, x, y + 105, 40, col, t0 + 0.15, 0.4, 'middle'); };
const dashed = (x1, y, x2, t0, col = INK) => { for (let x = x1; x < x2 - 10; x += 34) draw(rc.line(x, y, Math.min(x + 18, x2), y, o({ stroke: col, strokeWidth: 3 })), t0 + (x - x1) / 400, 0.1, col); };

CUR = SC.hook;
text('VIRAL CLAIM', 60, 85, 58, RED, wt('viral', 0, -0.2));
icon('1F4F1', 470, 62, 80, wt('viral', 0, 0.1), -10); icon('1F525', 535, 52, 60, wt('viral', 0, 0.3));
node(125, 230, 'Kushner', BLUE, wt('Kushner', 0, -0.1)); icon('1F1FA-1F1F8', 125, 230, 70, wt('Kushner', 0, 0.1));
node(360, 230, 'hitman?', RED, wt('hitman', 0, -0.1)); icon('1F575', 360, 230, 80, wt('hitman', 0, 0.1));
node(600, 230, 'Kirk case', INK, wt('Kirk', 0, -0.1)); icon('2696', 600, 230, 80, wt('Kirk', 0, 0.1));
node(840, 230, 'Egypt jets', ORG, wt('Egypt', 0, -0.1)); icon('2708', 840, 230, 80, wt('Egypt', 0, 0.1));
dashed(190, 230, 295, wt('hitman', 0, 0.2)); dashed(425, 230, 535, wt('Kirk', 0, 0.2)); dashed(665, 230, 775, wt('Egypt', 0, 0.2));
text('?', 242, 205, 44, RED, wt('hitman', 0, 0.5), 0.2, 'middle'); text('?', 480, 205, 44, RED, wt('Kirk', 0, 0.5), 0.2, 'middle'); text('?', 720, 205, 44, RED, wt('Egypt', 0, 0.5), 0.2, 'middle');
text('documented', 170, 485, 54, GREEN, wt('documented', 0, -0.2)); icon('2705', 110, 467, 64, wt('documented', 0, 0));
text('alleged', 170, 570, 54, ORG, wt('alleged', 0, -0.2)); icon('26A0', 110, 552, 64, wt('alleged', 0, 0));
text('unanswered', 170, 655, 54, BLUE, wt('answered', 0, -0.4)); icon('2753', 110, 637, 64, wt('answered', 0, -0.2));
icon('1F50E', 760, 560, 170, wt('lay', 0, 0), -8);

CUR = SC.book;
draw(rc.rectangle(60, 50, 230, 300, o({ fill: '#e9dcc0', fillStyle: 'hachure', hachureGap: 9 })), wt('book', 0, -0.4), 0.6);
text('Princes', 175, 140, 46, INK, wt('book', 0, -0.1), 0.5, 'middle'); text('& Thieves', 175, 190, 46, INK, wt('book', 0, 0.2), 0.5, 'middle');
text('— M. Cole', 175, 300, 36, '#555', wt('Cole', 0, 0), 0.5, 'middle'); icon('1F4D6', 175, 245, 60, wt('book', 0, 0.4));
draw(rc.rectangle(360, 60, 300, 110, o({ stroke: BLUE, strokeWidth: 4 })), wt('Dubai', 0, -0.3), 0.5, BLUE);
text('Dubai account', 510, 128, 46, BLUE, wt('Dubai', 0, -0.1), 0.5, 'middle'); icon('1F3E6', 720, 112, 80, wt('Dubai', 0, 0.2)); icon('1F4B0', 820, 112, 70, wt('money', 0, 0));
arrow(440, 180, 420, 250, wt('warlord', 0, -0.4)); text('warlord', 360, 300, 42, INK, wt('warlord', 0, -0.1));
arrow(510, 180, 600, 250, wt('mercenary', 0, -0.4)); text('mercenary', 560, 300, 42, INK, wt('mercenary', 0, -0.1));
arrow(600, 175, 800, 250, wt('hit', 0, -0.5), RED); text('“hit man”', 760, 300, 42, RED, wt('hit', 0, -0.1)); text('unnamed', 770, 345, 32, '#555', wt('man', 0, 0.3));
stamp('ALLEGATION', 470, 410, 380, ORG, wt('hit', 0, 0.6), -4, 50);
highlight(60, 500, 840, 80, wt('categorically', 0, -0.4));
text('Kushner: “categorically false”', 75, 560, 56, RED, wt('categorically', 0, -0.3));
icon('2696', 880, 540, 80, wt('sue', 0, -0.1));
text('Cole: stands by it', 75, 660, 56, BLUE, wt('stands', 0, -0.3)); icon('270D', 560, 640, 70, wt('stands', 0, 0.2));

CUR = SC.rashad;
icon('1F1EA-1F1EC', 120, 110, 110, wt('Egypt', 0, -0.1));
text('Hassan Rashad', 200, 105, 64, INK, wt('Rashad', 0, -0.4));
text('Egypt’s intelligence chief', 200, 160, 40, '#555', wt('intelligence', 0, -0.1));
draw(rc.rectangle(60, 230, 230, 110, o()), wt('August', 0, -0.3), 0.4); draw(rc.rectangle(60, 230, 230, 34, o({ stroke: RED, fill: RED, fillStyle: 'hachure', hachureGap: 6 })), wt('August', 0, -0.1), 0.3, RED);
text('Aug 2026', 175, 320, 48, INK, wt('August'), 0.5, 'middle');
draw(rc.ellipse(600, 400, 420, 190, o({ fill: '#c9b38a', fillStyle: 'hachure', hachureGap: 9 })), wt('table', 0, -0.3), 0.6);
icon('1F1FA-1F1F8', 430, 270, 70, wt('Kushner', 0, -0.1)); text('Kushner', 430, 240, 38, BLUE, wt('Kushner', 0, 0), 0.4, 'middle');
icon('1F5E3', 770, 270, 70, wt('Hamas', 0, -0.1)); text('Hamas', 770, 240, 38, INK, wt('Hamas', 0, 0), 0.4, 'middle');
icon('1F1EA-1F1EC', 600, 525, 70, wt('Rashad', 0, 1.2)); text('Rashad', 600, 600, 38, ORG, wt('table', 0, 0.2), 0.4, 'middle');
text('Gaza ceasefire', 600, 410, 44, INK, wt('Gaza', 0, -0.2), 0.6, 'middle'); icon('1F54A', 470, 400, 60, wt('ceasefire', 0, 0));
text('official talks', 60, 690, 42, GREEN, wt('Hamas', 0, 0.1)); text('· how close?', 320, 690, 42, BLUE, wt('Gaza', 0, 0.1));

CUR = SC.plane;
text('Provo, Utah · Sept 10', 60, 80, 50, INK, wt('Provo', 0, -0.3)); icon('2708', 620, 62, 80, wt('Egyptian', 0, 0)); text('SU-BTT', 680, 80, 44, ORG, wt('military', 0, 0));
draw(rc.line(70, 200, 900, 200, o({ strokeWidth: 5 })), wt('Flight', 0, -0.3), 0.6);
draw(rc.line(220, 180, 220, 220, o({ stroke: ORG, strokeWidth: 6 })), TL.events.clock - 0.3, 0.2, ORG);
text('7:08 AM', 220, 265, 48, ORG, TL.events.clock - 0.1, 0.5, 'middle'); text('jet departs', 220, 160, 34, ORG, TL.events.clock + 0.2, 0.4, 'middle');
draw(rc.line(700, 180, 700, 220, o({ stroke: RED, strokeWidth: 6 })), wt('shooting', 0, -0.4), 0.2, RED);
text('midday', 700, 265, 48, RED, wt('shooting', 0, -0.2), 0.4, 'middle'); text('shooting', 700, 160, 34, RED, wt('shooting', 0, 0), 0.4, 'middle');
draw(rc.path('M 240 290 Q 460 340 680 290', o({ stroke: BLUE })), wt('hours', 0, -0.2), 0.5, BLUE); text('hours before', 460, 345, 40, BLUE, wt('hours', 0, 0), 0.4, 'middle');
icon('1F570', 860, 120, 70, TL.events.clock);
text('Owens: jets crossed Erika Kirk’s path', 60, 420, 42, INK, wt('Candace', 0, -0.2));
draw(rc.circle(140, 515, 110, o()), wt('analysis', 0, -0.2), 0.4);
draw(rc.path('M 140 515 L 140 460 A 55 55 0 1 1 92 543 Z', o({ stroke: RED, fill: RED, fillStyle: 'hachure', hachureGap: 6 })), wt('two', 0, -0.1), 0.5, RED);
text('~2/3 don’t hold', 220, 530, 46, RED, wt('thirds', 0, -0.1)); text('Erika Kirk: rejects it', 560, 530, 38, BLUE, wt('rejects', 0, -0.2));
highlight(55, 600, 860, 85, wt('Still', 0, -0.3));
text('OPEN: why was the jet in Provo?', 70, 665, 56, INK, wt('Still', 0, -0.1)); icon('2753', 890, 640, 70, wt('why', 0, 0));

CUR = SC.case;
icon('2696', 130, 120, 120, wt('Robinson', 0, -0.2));
text('Utah v. Robinson', 220, 110, 62, INK, wt('Robinson', 0, -0.4));
text('aggravated murder · pleads not guilty', 60, 230, 42, INK, wt('aggravated', 0, -0.2));
icon('1F4C5', 140, 345, 100, wt('Trial', 0, -0.1)); text('Trial: June 2028', 220, 365, 60, BLUE, wt('Trial', 0, -0.1));
text('Link to …', 60, 480, 48, '#555', wt('found', 0, -0.4));
[['Egypt', 'Egypt', 120], ['Kushner', 'Kushner', 400], ['the book', 'book', 680]].forEach(([lab, tok, x]) => { text(lab, x, 570, 50, INK, wt(tok, 0, -0.2)); });
highlight(55, 610, 860, 80, wt('nothing', 0, -0.2));
text('none found in reporting', 70, 670, 56, INK, wt('nothing', 0, -0.1));

CUR = SC.verdict;
[['1F4D6', 'book', 130], ['1F575', 'spy chief', 365], ['2708', 'plane', 600], ['2696', 'trial', 835]].forEach(([c, lab, x], i) => {
  icon(c, x, 140, 100, wt('piece', 0, -0.2 + i * 0.2)); text(lab, x, 240, 38, INK, wt('piece', 0, i * 0.2), 0.3, 'middle');
  check(x - 25, 300, 50, wt('real', 0, -0.1 + i * 0.15)); });
[245, 480, 715].forEach((x, i) => { dashed(x - 45, 140, x + 45, wt('links', 0, i * 0.15), RED); text('?', x, 115, 46, RED, wt('links', 0, 0.3 + i * 0.15), 0.2, 'middle'); });
stamp('NOT PROVEN', 480, 420, 470, RED, TL.events.snap - 0.2, -5, 58);
text('coincidence', 70, 580, 56, INK, wt('Coincidence', 0, -0.2)); text('or', 445, 580, 44, '#555', wt('or', 0, 0)); text('connection?', 520, 580, 56, INK, wt('connection', 0, -0.2));
highlight(200, 625, 560, 75, wt('decide', 0, -0.3));
text('YOU DECIDE – on evidence', 480, 680, 54, BLUE, wt('decide', 0, -0.2), 0.8, 'middle');
icon('1F914', 870, 560, 90, wt('Coincidence', 0, 0.3));

CUR = SC.cta;
highlight(150, 170, 660, 120, wt('Verify', 0, -0.3));
text('VERIFY ME!', 480, 270, 130, RED, wt('Verify', 0, -0.1), 0.7, 'middle');
draw(rc.ellipse(480, 225, 760, 210, o({ stroke: RED, strokeWidth: 5 })), wt('Verify', 0, 0.5), 0.6, RED);
text('Sources ↓ in the description', 480, 460, 58, INK, wt('source'), 1.0, 'middle');
text('THE DECODER', 480, 600, 64, BLUE, wt('Verify', 0, 0.9), 0.8, 'middle');
icon('1F50E', 150, 445, 90, wt('source', 0, -0.2)); icon('270D', 800, 600, 90, wt('Verify', 0, 1.2));
} else if (EP === 'airspace_en') {

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
text('a.m. · Japan', 105, 500, 46, INK, wt('Japan'));
draw(rc.path('M 560 120 q 40 -30 90 -10 t 90 20 t 60 60', o({ stroke: '#888', strokeWidth: 2 })), wt('asleep'), 0.6, '#888');
text('Zzz', 740, 120, 60, '#888', wt('asleep', 0, 0.3));
draw(rc.path('M 470 520 Q 520 380 640 330 Q 760 290 880 330 Q 820 420 700 470 Q 600 520 470 520 Z', o(LAND)), wt("Japan's", 0, -0.4), 0.8, '#2e5e3a');
text('JAPAN', 620, 450, 50, '#2e5e3a', wt("Japan's", 0, -0.1));
draw(rc.path('M 440 560 Q 520 300 700 270 Q 860 250 920 300', o({ stroke: RED, strokeLineDash: [12, 9] })), wt('airspace', 0, -0.2), 0.6, RED);
jet(560, 240, 2.2, 34, wt('Russian')); jet(640, 200, 2.2, 34, wt('military'));
text("didn't turn back!", 400, 650, 64, RED, wt('turn', 0, -0.1));

CUR = SC.route;
// map: Korea, Japan (Kyushu/Honshu), Taiwan, Yonaguni
draw(rc.path('M 170 40 Q 230 60 240 140 Q 250 230 210 300 Q 170 320 150 260 Q 130 160 170 40 Z', o(LAND)), SC.route.s.start + 0.1, 0.7, '#2e5e3a');
draw(rc.path('M 330 330 Q 380 290 420 300 Q 440 360 400 410 Q 350 420 330 330 Z', o(LAND)), SC.route.s.start + 0.4, 0.6, '#2e5e3a');
draw(rc.path('M 420 290 Q 520 230 640 170 Q 760 110 860 40 L 880 70 Q 790 150 660 220 Q 540 280 440 320 Z', o(LAND)), SC.route.s.start + 0.6, 0.7, '#2e5e3a');
draw(rc.ellipse(170, 600, 70, 150, o(LAND)), SC.route.s.start + 0.9, 0.5, '#2e5e3a');
text('Korea', 110, 340, 36, '#2e5e3a', SC.route.s.start + 0.5); text('Japan', 640, 290, 40, '#2e5e3a', SC.route.s.start + 0.8); text('Taiwan', 60, 700, 38, '#2e5e3a', SC.route.s.start + 1.0);
draw(rc.circle(330, 250, 14, o({ stroke: RED, fill: RED, fillStyle: 'solid' })), wt('Okinoshima'), 0.3, RED);
text('Okinoshima · 3 min', 345, 225, 40, RED, wt('Okinoshima', 0, 0.1));
draw(rc.path('M 560 40 Q 430 120 330 250', o({ stroke: RED, strokeWidth: 4, strokeLineDash: [14, 9] })), wt('Three', 0, 0), 0.8, RED);
jet(470, 330, -0.6, 22, wt('fighter'), BLUE); jet(510, 360, -0.6, 22, wt('fighter', 0, 0.2), BLUE);
text('radio warning', 520, 410, 36, BLUE, wt('warnings', 0, -0.2));
draw(rc.path('M 330 250 Q 290 280 285 330', o({ stroke: RED, strokeWidth: 4, strokeLineDash: [14, 9] })), wt('Tsushima', 0, -0.3), 0.5, RED);
text('Tsushima', 200, 395, 34, INK, wt('Tsushima'));
jet(120, 210, 0.8, 18, wt('Korea'), BLUE); text('S. Korea: jets ↑', 20, 180, 32, BLUE, wt('also', 0, 0));
draw(rc.path('M 285 330 Q 300 450 245 560', o({ stroke: RED, strokeWidth: 4, strokeLineDash: [14, 9] })), wt('gap', 0, -0.3), 0.6, RED);
draw(rc.circle(265, 585, 12, o({ fill: INK, fillStyle: 'solid' })), wt('Yonaguni', 0, -0.2), 0.2); text('Yonaguni', 280, 595, 32, INK, wt('Yonaguni'));
draw(rc.path('M 245 560 Q 225 620 250 660', o({ stroke: RED, strokeWidth: 4, strokeLineDash: [14, 9] })), wt('coast', 0, -0.4), 0.5, RED);
text('Taiwan tracks', 20, 520, 34, INK, wt('tracks', 0, -0.1));
arrow(255, 665, 640, 650, wt('Pacific', 0, -0.4), RED); text('Pacific', 650, 665, 48, BLUE, wt('Pacific'));
text('Moscow: …', 600, 560, 56, INK, wt('Moscow')); draw(rc.line(640, 520, 860, 520, o({ stroke: '#888' })), wt('Silence'), 0.3, '#888');

CUR = SC.china;
text('100+', 60, 160, 130, RED, wt('100'));
for (let i = 0; i < 18; i++) ship(330 + (i % 6) * 95, 70 + Math.floor(i / 6) * 60, 70, wt('warships') + i * 0.07);
text('vessels in the W. Pacific', 330, 290, 46, INK, wt('Western', 0, -0.2));
text('no announcement', 330, 340, 40, RED, wt('announcement', 0, -0.3));
draw(rc.ellipse(230, 560, 300, 70, o({ fill: '#555c6a', fillStyle: 'hachure', hachureGap: 6 })), wt('submarine', 0, -0.2), 0.6);
draw(rc.rectangle(215, 500, 50, 30, o()), wt('submarine', 0, 0.2), 0.3);
draw(rc.path('M 240 495 Q 260 380 340 380', o({ stroke: RED, strokeLineDash: [10, 8] })), TL.events.rakete, 0.6, RED);
draw(rc.path(rocket(340, 350, 70), o({ stroke: RED })), TL.events.rakete + 0.4, 0.4, RED);
text('ICBM?', 400, 420, 70, RED, TL.events.rakete + 0.5);
text('“says one official”', 420, 480, 38, INK, wt('official', 0, -0.3));
{ const st = document.createElementNS(NS, 'g'); st.setAttribute('transform', 'rotate(-8 710 600)'); CUR.g.appendChild(st);
  const n = rc.rectangle(560, 560, 300, 80, o({ stroke: '#e0a100', strokeWidth: 6 })); st.appendChild(n); draw(n, wt('not', 0, -0.1), 0.4, '#e0a100'); st.appendChild(CUR.g.lastChild);
  text('UNCONFIRMED', 710, 620, 58, '#e0a100', wt('not', 0, 0.2), 0.5, 'middle', -8); }

CUR = SC.timing;
draw(rc.rectangle(60, 60, 220, 220, o()), wt('timing'), 0.6); draw(rc.rectangle(60, 60, 220, 55, o({ stroke: RED, fill: RED, fillStyle: 'hachure', hachureGap: 6 })), wt('timing', 0, 0.4), 0.4, RED);
text('Nov 19', 80, 220, 78, INK, wt('November', 0, -0.2));
draw(rc.circle(640, 330, 260, o({ fill: '#c9b38a', fillStyle: 'hachure', hachureGap: 9 })), wt('hours'), 0.7);
[['Trump', 640, 150], ['Xi', 820, 400], ['Putin', 460, 400]].forEach(([n, x, y], i) => { draw(rc.circle(x, y, 60, o({ stroke: BLUE })), wt(n === 'Xi' ? 'Xi' : n), 0.3, BLUE); text(n, x, y + (y < 300 ? -45 : 75), 44, BLUE, wt(n === 'Xi' ? 'Xi' : n, 0, 0.1), 0.4, 'middle'); });
text('Shenzhen', 640, 340, 48, RED, wt('Shenzhen'), 0.6, 'middle');
draw(rc.circle(640, 560, 60, o({ stroke: '#888', strokeLineDash: [8, 8] })), wt('Europe', 0, -0.2), 0.4, '#888');
text('Europe?', 640, 650, 50, '#888', wt('Europe'), 0.5, 'middle'); cross(615, 535, 50, wt('table'), RED, 5);

CUR = SC.decode;
text('“Cyberattacks!”', 60, 140, 80, INK, wt('cyberattacks', 0, -0.3));
draw(rc.circle(780, 160, 150, o({ stroke: BLUE, strokeWidth: 5 })), wt('checked', 0, -0.3), 0.5, BLUE); draw(rc.line(835, 215, 910, 290, o({ stroke: BLUE, strokeWidth: 9 })), wt('checked'), 0.3, BLUE);
text('Officials: technical failure', 60, 330, 58, BLUE, wt('officials'));
text('≠ attack', 60, 410, 70, RED, wt('attack', 1));
highlight(60, 520, 560, 80, wt('story', 0, -0.3));
text('story ≠ analysis', 70, 585, 72, INK, wt('story', 0, -0.2));

CUR = SC.fazit;
text('Russia', 60, 170, 64, RED, wt('Russia')); text('China', 60, 330, 64, RED, wt('China'));
[['Washington', 160], ['Tokyo', 300], ['Taipei', 440]].forEach(([n, y]) => { arrow(330, 240, 580, y - 15, wt(n, 0, -0.3)); text(n, 600, y, 56, BLUE, wt(n)); });
draw(rc.path('M 300 200 q 15 40 0 80', o({ stroke: RED })), wt('showing'), 0.3, RED); draw(rc.path('M 320 185 q 25 55 0 110', o({ stroke: RED })), wt('showing', 0, 0.15), 0.3, RED);
highlight(60, 560, 840, 90, wt('leverage', 0, -0.5));
text('= leverage', 80, 630, 76, INK, wt('leverage', 0, -0.4));
text('no secret plan', 60, 520, 46, '#888', wt('secret', 0, -0.2));

CUR = SC.cta;
highlight(150, 170, 660, 120, wt('Verify', 0, -0.3));
text('VERIFY ME!', 480, 270, 130, RED, wt('Verify', 0, -0.1), 0.7, 'middle');
draw(rc.ellipse(480, 225, 760, 210, o({ stroke: RED, strokeWidth: 5 })), wt('Verify', 0, 0.5), 0.6, RED);
text('Sources ↓ in the description', 480, 460, 58, INK, wt('Sources'), 1.0, 'middle');
text('Next: after Shenzhen', 480, 600, 54, BLUE, wt('Shenzhen', 0, -0.2), 0.9, 'middle');

} else if (EP === 'luftraum') {

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
  board.style.transform = `translateY(${(1 - drop) * -(BH + 100)}px) rotate(${Math.sin(t * 0.5) * 0.35 - 0.6}deg) scaleY(${0.92 + 0.08 * ease(flip)})`;
  let penPos = null, penCol = INK, latest = -1, penKind = null;
  for (const k in SC) {
    const sc = SC[k]; const vis = sc.s === s; sc.g.style.display = vis ? '' : 'none'; if (!vis) continue;
    for (const it of sc.items) {
      const p = clamp((t - it.t0) / it.dur);
      if (it.kind === 'icon') {
        const sc = p > 0 ? back(p) : 0; it.node.style.opacity = p > 0 ? 1 : 0;
        it.node.setAttribute('transform', `translate(${it.x} ${it.y}) rotate(${it.rot}) scale(${it.size / 72 * sc}) translate(-36 -36)`);
        continue;
      }
      if (it.kind === 'paths') {
        let L = p * it.total, cur = null;
        it.paths.forEach((pa, i) => {
          if (!it.lens[i]) { pa.style.opacity = p > 0.6 ? Math.min(1, (p - 0.6) / 0.4) : 0; return; }
          const v = clamp(L, 0, it.lens[i]); L -= it.lens[i];
          pa.style.strokeDashoffset = it.lens[i] - v;
          if (v > 0 && v < it.lens[i]) cur = [pa, v];
        });
        if (p > 0 && p < 1 && cur && it.t0 >= latest) { const pt = cur[0].getPointAtLength(cur[1]); penPos = toSvg(cur[0], pt.x, pt.y); penCol = it.color; latest = it.t0; penKind = 'draw'; }
      } else {
        it.r.setAttribute('width', (it.bb.width + 8) * p);
        if (p > 0 && p < 1 && it.t0 >= latest) { penPos = toSvg(it.tx, it.bb.x + it.bb.width * p, it.bb.y + it.bb.height * 0.72); penCol = it.color; latest = it.t0; penKind = 'write'; }
      }
    }
  }
  if (penPos) { pen.style.display = ''; pen.setAttribute('transform', `translate(${penPos.x} ${penPos.y})`); penCap.setAttribute('fill', penCol); penTip.setAttribute('fill', penCol); }
  else pen.style.display = 'none';
  return penPos ? { x: penPos.x, y: penPos.y, k: penKind } : null;
};
await Promise.all(ICON_LOADS);
window.READY = true;
