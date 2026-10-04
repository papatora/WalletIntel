// Independent confirmation — Area C: KOL column-header sort dead.
// CDP 9222: new tab -> http://127.0.0.1:8787/#/kol, read state, click th[data-sort], read state again.
const CDP = 'http://127.0.0.1:9222';

async function j(url, opts) { const r = await fetch(url, opts); return r.json(); }
const sleep = ms => new Promise(r => setTimeout(r, ms));

// 1. open a fresh tab
const { id: targetId } = await j(`${CDP}/json/new?${encodeURIComponent('http://127.0.0.1:8787/#/kol')}`, { method: 'PUT' });
console.log('tab', targetId);

await sleep(300);
const tabInfo = (await j(`${CDP}/json/list`)).find(t => t.id === targetId);
console.log('tab url', tabInfo && tabInfo.url, '| ws', tabInfo && tabInfo.webSocketDebuggerUrl);
const ws = new WebSocket(tabInfo.webSocketDebuggerUrl);
ws.onerror = e => console.log('WS ERROR', e.message || e);
let mid = 0; const pending = new Map();
const send = (method, params = {}) => new Promise((res, rej) => {
  const i = ++mid; pending.set(i, { res, rej });
  ws.send(JSON.stringify({ id: i, method, params }));
});
ws.onmessage = ev => {
  const m = JSON.parse(ev.data);
  if (m.id && pending.has(m.id)) { pending.get(m.id).res(m.result); pending.delete(m.id); }
};
await new Promise(r => { ws.onopen = r; });

const evl = async expression => (await send('Runtime.evaluate', { expression, returnByValue: true })).result.value;

// wait for the KOL table to render (dataset may take a while to load)
let ready = null;
for (let i = 0; i < 40; i++) {
  await sleep(500);
  ready = await evl(`!!document.querySelector('#app th[data-sort="fans"]')`);
  if (ready) break;
}
console.log('table rendered?', ready);
if (!ready) console.log('BODY SNIPPET', (await evl(`document.querySelector('#app').innerText.slice(0,300)`)));

// state probe: which header is active (is-on + arrow) and first row address
const PROBE = `(() => {
  const on = document.querySelector('#app th.is-on');
  const first = document.querySelector('#app tbody tr td:nth-child(2) a');
  const ths = [...document.querySelectorAll('#app th[data-sort]')].map(t => t.dataset.sort + ':' + (t.querySelector('.sort')?.textContent ?? ''));
  return JSON.stringify({ on: on ? on.textContent.trim() : null, first: first ? first.textContent.trim() : null, ths });
})()`;

const before = await evl(PROBE);
console.log('BEFORE', before);

// 2. click th[data-sort=pnl] like a user would (bubbles, so delegation would catch it)
const clickPnl = await evl(`(() => {
  const th = document.querySelector('#app th[data-sort="pnl"]');
  if (!th) return 'NO th[data-sort=pnl]';
  th.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true }));
  const on = document.querySelector('#app th.is-on');
  const first = document.querySelector('#app tbody tr td:nth-child(2) a');
  return JSON.stringify({ afterClickPnl: { on: on ? on.textContent.trim() : null, first: first ? first.textContent.trim() : null } });
})()`);
console.log('AFTER pnl ', clickPnl);

// 3. click th[data-sort=win]
const clickWin = await evl(`(() => {
  const th = document.querySelector('#app th[data-sort="win"]');
  if (!th) return 'NO th[data-sort=win]';
  th.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true }));
  const on = document.querySelector('#app th.is-on');
  const first = document.querySelector('#app tbody tr td:nth-child(2) a');
  return JSON.stringify({ afterClickWin: { on: on ? on.textContent.trim() : null, first: first ? first.textContent.trim() : null } });
})()`);
console.log('AFTER win ', clickWin);

const after = await evl(PROBE);
console.log('AFTER(all)', after);

// 4. sanity: does the sort logic itself work? set st via the module isn't accessible (module-scope st),
//    but we can verify rows() ordering is driven by st.sort by checking the page is actually interactive
//    (e.g. search input works) — proving the page itself is alive, only header clicks are dead.
const sanity = await evl(`(() => {
  const q = document.querySelector('#kol-q');
  if (!q) return 'NO #kol-q';
  q.value = '0x3475';
  q.dispatchEvent(new Event('input', { bubbles: true }));
  const rows = document.querySelectorAll('#app tbody tr').length;
  const on = document.querySelector('#app th.is-on');
  return JSON.stringify({ searchWorks: rows, onAfterSearch: on ? on.textContent.trim() : null });
})()`);
console.log('SANITY(search binds)', sanity);

await send('Page.close');
ws.close();
