const { chromium } = require('playwright-core');

(async () => {
  const base = 'http://127.0.0.1:8787';
  const targets = [
    { url: base + '/#/kol', out: 'results/audit/v2_kol.png' },
    { url: base + '/#/leaderboard', out: 'results/audit/v2_lb.png' },
  ];

  // Cek 9222 lalu 9224
  let port = null;
  for (const p of [9222, 9224]) {
    try {
      const r = await fetch(`http://127.0.0.1:${p}/json/version`);
      if (r.ok) { port = p; break; }
    } catch (e) { /* lanjut */ }
  }
  if (!port) { console.error('NO_CDP_PORT'); process.exit(1); }
  console.log('CDP_PORT=' + port);

  const browser = await chromium.connectOverCDP(`http://127.0.0.1:${port}`);
  const ctx = browser.contexts()[0] || await browser.newContext();
  const pages = [];

  for (const t of targets) {
    const page = await ctx.newPage();
    pages.push(page);
    await page.setViewportSize({ width: 1440, height: 950 });
    await page.goto(t.url, { waitUntil: 'load', timeout: 30000 });
    // tunggu SPA render
    await page.waitForTimeout(5000);
    await page.screenshot({ path: t.out, fullPage: true });
    console.log('SHOT_OK ' + t.out);
  }

  for (const p of pages) {
    try { await p.close(); } catch (e) {}
  }
  await browser.close();
  console.log('DONE');
})().catch(e => { console.error('ERR ' + e.message); process.exit(1); });
