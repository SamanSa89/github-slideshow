// usage: node render.js <outdir> [w h] [--times t1,t2,...] [--from f0 --to f1]
const { chromium } = require('playwright');
const http = require('http'), fs = require('fs'), path = require('path');
const args = process.argv.slice(2); const out = args[0]; fs.mkdirSync(out, { recursive: true });
const W = +(args[1] || 720), H = +(args[2] || 1280);
const opt = k => { const i = args.indexOf(k); return i >= 0 ? args[i + 1] : null; };
const types = { '.html': 'text/html', '.js': 'text/javascript', '.json': 'application/json' };
const root = __dirname;
const srv = http.createServer((q, r) => { const p = path.join(root, decodeURIComponent(q.url.split('?')[0])); fs.readFile(p, (e, d) => { if (e) { r.writeHead(404); r.end(); return; } r.writeHead(200, { 'Content-Type': types[path.extname(p)] || 'application/octet-stream' }); r.end(d); }); }).listen(0);
(async () => {
  const port = srv.address().port;
  const b = await chromium.launch({ args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
  const p = await b.newPage({ viewport: { width: W, height: H } });
  p.on('console', m => { if (m.type() === 'error') console.error('page:', m.text()); }); p.on('pageerror', e => console.error('pageerror:', e.message));
  await p.goto(`http://127.0.0.1:${port}/${opt('--page') || 'index.html'}?w=${W}&h=${H}&tl=./${opt('--tl') || 'work/timeline.json'}&mode=${opt('--mode') || ''}`);
  await p.waitForFunction('window.READY === true', null, { timeout: 120000 });
  const TLP = opt('--tl') || 'work/timeline.json'; const tl = JSON.parse(fs.readFileSync(path.join(root, TLP)));
  let times;
  if (opt('--times')) times = opt('--times').split(',').map(Number);
  else { const f0 = +(opt('--from') || 0), f1 = +(opt('--to') || Math.floor(tl.total * tl.fps)); times = []; for (let f = f0; f < f1; f++) times.push(f / tl.fps); }
  const t0 = Date.now();
  for (let i = 0; i < times.length; i++) {
    const url = await p.evaluate(t => window.renderAt(t), times[i]);
    const name = opt('--times') ? `still_${times[i]}.jpg` : `f${String(Math.round(times[i] * tl.fps)).padStart(5, '0')}.jpg`;
    fs.writeFileSync(path.join(out, name), Buffer.from(url.split(',')[1], 'base64'));
    if (i % 100 === 0) console.log(`frame ${i}/${times.length} ${((Date.now() - t0) / (i + 1)).toFixed(0)} ms/frame`);
  }
  await b.close(); srv.close();
})();
