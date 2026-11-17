// usage: node render_sketch.js <outdir> [--times a,b] [--from f0 --to f1]  -> transparent PNG frames of the Leinwand layer
const { chromium } = require('playwright');
const http = require('http'), fs = require('fs'), path = require('path');
const args = process.argv.slice(2); const out = args[0]; fs.mkdirSync(out, { recursive: true });
const opt = k => { const i = args.indexOf(k); return i >= 0 ? args[i + 1] : null; };
const types = { '.html': 'text/html', '.js': 'text/javascript', '.json': 'application/json', '.woff2': 'font/woff2' };
const root = __dirname;
const srv = http.createServer((q, r) => { const p = path.join(root, decodeURIComponent(q.url.split('?')[0])); fs.readFile(p, (e, d) => { if (e) { r.writeHead(404); r.end(); return; } r.writeHead(200, { 'Content-Type': types[path.extname(p)] || 'application/octet-stream' }); r.end(d); }); }).listen(0);
(async () => {
  const b = await chromium.launch();
  const p = await b.newPage({ viewport: { width: 1080, height: 860 } });
  p.on('pageerror', e => console.error('pageerror:', e.message)); p.on('console', m => { if (m.type() === 'error') console.error('page:', m.text()); });
  await p.goto(`http://127.0.0.1:${srv.address().port}/sketch.html?tl=./${opt('--tl') || 'work/timeline.json'}&ep=${opt('--ep') || ''}`);
  await p.waitForFunction('window.READY === true', null, { timeout: 60000 });
  const TLP = opt('--tl') || 'work/timeline.json'; const tl = JSON.parse(fs.readFileSync(path.join(root, TLP)));
  let times;
  if (opt('--times')) times = opt('--times').split(',').map(Number);
  else { const f0 = +(opt('--from') || 0), f1 = +(opt('--to') || Math.floor(tl.total * tl.fps)); times = []; for (let f = f0; f < f1; f++) times.push(f / tl.fps); }
  const el = await p.$('#stage'); const t0 = Date.now();
  for (let i = 0; i < times.length; i++) {
    await p.evaluate(t => window.renderAt(t), times[i]);
    const name = opt('--times') ? `still_${times[i]}.png` : `s${String(Math.round(times[i] * tl.fps)).padStart(5, '0')}.png`;
    await el.screenshot({ path: path.join(out, name), omitBackground: true });
    if (i % 200 === 0) console.log(`frame ${i}/${times.length} ${((Date.now() - t0) / (i + 1)).toFixed(0)} ms/frame`);
  }
  await b.close(); srv.close();
})();
