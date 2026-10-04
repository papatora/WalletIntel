// Independent confirmation — Area C: kol.js:113 search input loses focus per keystroke.
// Launch own headless Chrome (CDP 9333) -> open http://127.0.0.1:8787/#/kol ->
// focus #kol-q, set value, dispatch input (exactly the ask's check) -> read document.activeElement.
// Then a real-keyboard check via CDP Input domain, then the same check on #/tokens (#tok-q) as comparator.
import { spawn } from 'node:child_process';

const CDP_PORT = 9333;
const APP = 'http://127.0.0.1:8787';
const CHROME = 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe';
const sleep = ms => new Promise(r => setTimeout(r, ms));

// 1. launch own chrome
const udd = process.env.TEMP + '\\wi_confirmC_' + Date.now();
const cp = spawn(CHROME, [
  '--headless=new', `--remote-debugging-port=${CDP_PORT}`, `--user-data-dir=${udd}`,
  '--no-first-run', '--no-default-browser-check', '--window-size=1400,900', 'about:blank',
], { stdio: 'ignore', detached: false });
try { process.on('exit', () => { try { cp.kill(); } catch {} }); } catch {}

// 2. wait for CDP
let version = null;
for (let i = 0; i < 50; i++) {
  try { version = await (await fetch(`http://127.0.0.1:${CDP_PORT}/json/version`)).json(); break; }
  catch { await sleep(200); }
}
if (!version) { console.log('RESULT: chrome-cdp-unavailable'); process.exit(2); }
console.log('chrome up:', version.Browser);

const j = async (url, opts) => (await fetch(url, opts)).json();
const { id: targetId } = await j(`http://127.0.0.1:${CDP_PORT}/json/new?${encodeURIComponent(APP + '/#/kol')}`, { method: 'PUT' });
await sleep(400);
const tab = (await j(`http://127.0.0.1:${CDP_PORT}/json/list`)).find(t => t.id === targetId);
const ws = new WebSocket(tab.webSocketDebuggerUrl);
let mid = 0; const pending = new Map(); const events = [];
const send = (method, params = {}) => new Promise((res, rej) => {
  const i = ++mid; pending.set(i, { res, rej }); ws.send(JSON.stringify({ id: i, method, params }));
});
ws.onmessage = ev => {
  const m = JSON.parse(ev.data);
  if (m.id && pending.has(m.id)) { pending.get(m.id).res(m.result); pending.delete(m.id); }
  else if (m.method) events.push(m);
};
await new Promise((r, e) => { ws.onopen = r; ws.onerror = e; });
const evl = async expression => {
  const r = await send('Runtime.evaluate', { expression, returnByValue: true, awaitPromise: true });
  if (r.exceptionDetails) return 'EVAL-ERROR: ' + JSON.stringify(r.exceptionDetails).slice(0, 300);
  return r.result.value;
};

// 3. wait for KOL view rendered (dataset ~49MB may take a while)
let ready = null;
for (let i = 0; i < 60; i++) {
  await sleep(500);
  ready = await evl(`!!document.querySelector('#kol-q') && !!document.querySelector('#kol-q').closest('.toolbar')`);
  if (ready) break;
}
console.log('kol view rendered?', ready);
if (!ready) { console.log('BODY:', await evl(`document.body.innerText.slice(0,300)`)); process.exit(2); }

const state = `(() => {
  const q = document.querySelector('#kol-q');
  const cnt = document.querySelector('.toolbar .t2');
  const firstRow = document.querySelector('.tbl tbody tr td:nth-child(3)');
  return JSON.stringify({
    active: document.activeElement ? (document.activeElement.tagName + (document.activeElement.id ? '#' + document.activeElement.id : '')) : String(document.activeElement),
    inputValue: q ? q.value : null,
    focused: document.activeElement === q,
    count: cnt ? cnt.textContent.trim() : null,
    firstRowText: firstRow ? firstRow.textContent.trim().slice(0, 40) : null,
  });
})()`;

console.log('\n=== CHECK 1: the ask\'s exact check (focus, set value, dispatch input) ===');
console.log('BEFORE', await evl(state));

const check1 = await evl(`(() => {
  const q = document.querySelector('#kol-q');
  q.focus();
  const focusedBefore = document.activeElement === q;
  q.value = 'gmgn';
  q.dispatchEvent(new Event('input', { bubbles: true }));   // handler runs draw() synchronously inside this
  const q2 = document.querySelector('#kol-q');              // the NEW element after innerHTML replacement
  return JSON.stringify({
    focusedBefore,
    afterDispatch_activeElement: document.activeElement ? (document.activeElement.tagName + (document.activeElement.id ? '#' + document.activeElement.id : '')) : String(document.activeElement),
    activeElementIsBody: document.activeElement === document.body,
    oldInputStillConnected: q.isConnected,                   // element that received the event, post-handler
    newValueElementValue: q2 ? q2.value : null,              // state st.q persisted into re-render
    focusRestoredToNewInput: q2 ? document.activeElement === q2 : false,
  });
})()`);
console.log('AFTER ', check1);
console.log('STATE ', await evl(state));

console.log('\n=== CHECK 2: two simulated keystrokes — must refocus manually between them ===');
const check2 = await evl(`(() => {
  const log = [];
  let q = document.querySelector('#kol-q');
  q.focus(); q.value = 'g'; q.dispatchEvent(new Event('input', { bubbles: true }));
  log.push({ after_keystroke_1_active: document.activeElement === document.body ? 'BODY' : document.activeElement.tagName, stillFocused: document.activeElement === q });
  q = document.querySelector('#kol-q');
  q.focus(); q.value = 'gm'; q.dispatchEvent(new Event('input', { bubbles: true }));
  log.push({ after_keystroke_2_active: document.activeElement === document.body ? 'BODY' : document.activeElement.tagName, stillFocused: document.activeElement === q });
  return JSON.stringify(log);
})()`);
console.log('KEYSTROKES', check2);

console.log('\n=== CHECK 3: REAL keyboard typing via CDP Input domain ===');
const inp = await evl(`(() => { const q = document.querySelector('#kol-q'); q.value=''; q.dispatchEvent(new Event('input',{bubbles:true})); const r = q.getBoundingClientRect(); return JSON.stringify({x: r.x + 30, y: r.y + r.height/2}); })()`);
const { x, y } = JSON.parse(inp);
await send('Input.dispatchMouseEvent', { type: 'mousePressed', x, y, button: 'left', clickCount: 1 });
await send('Input.dispatchMouseEvent', { type: 'mouseReleased', x, y, button: 'left', clickCount: 1 });
await sleep(100);
console.log('after real click, active:', await evl(`document.activeElement.tagName + '#' + document.activeElement.id`));
// clear field with select-all + delete via real keys, then type ONE real character
await send('Input.dispatchKeyEvent', { type: 'keyDown', modifiers: 2, key: 'a', code: 'KeyA', windowsVirtualKeyCode: 65 });
await send('Input.dispatchKeyEvent', { type: 'keyUp', modifiers: 2, key: 'a', code: 'KeyA', windowsVirtualKeyCode: 65 });
await send('Input.dispatchKeyEvent', { type: 'keyDown', key: 'Delete', code: 'Delete', windowsVirtualKeyCode: 46 });
await send('Input.dispatchKeyEvent', { type: 'keyUp', key: 'Delete', code: 'Delete', windowsVirtualKeyCode: 46 });
await sleep(250);
const real1 = await evl(`JSON.stringify({ active: document.activeElement === document.body ? 'BODY' : document.activeElement.tagName + '#' + document.activeElement.id, focused: document.activeElement === document.querySelector('#kol-q'), value: document.querySelector('#kol-q').value })`);
console.log('after clear (real keys):', real1);
await send('Input.dispatchKeyEvent', { type: 'keyDown', key: 'g', code: 'KeyG', text: 'g', unmodifiedText: 'g', windowsVirtualKeyCode: 71 });
await send('Input.dispatchKeyEvent', { type: 'keyUp', key: 'g', code: 'KeyG', windowsVirtualKeyCode: 71 });
const real2 = await evl(`(() => { const q = document.querySelector('#kol-q'); return JSON.stringify({ active: document.activeElement === document.body ? 'BODY' : document.activeElement.tagName + '#' + document.activeElement.id, focused: document.activeElement === q, value: q.value }); })()`);
console.log('after ONE real keystroke "g":', real2);

console.log('\n=== CHECK 4: comparator — same test on #/tokens (#tok-q, tokens.js:78 restores focus) ===');
await evl(`location.hash = '#/tokens'`);
let tready = null;
for (let i = 0; i < 30; i++) {
  await sleep(500);
  tready = await evl(`!!document.querySelector('#tok-q')`);
  if (tready) break;
}
console.log('tokens view rendered?', tready);
if (tready) {
  const check4 = await evl(`(() => {
    const q = document.querySelector('#tok-q');
    q.focus(); q.value = 'gmgn'; q.dispatchEvent(new Event('input', { bubbles: true }));
    const immediate = document.activeElement === document.body ? 'BODY' : document.activeElement.tagName + '#' + document.activeElement.id;
    return JSON.stringify({ immediate_activeElement: immediate });
  })()`);
  console.log('tokens immediately after input event (debounce 160ms not elapsed):', check4);
  await sleep(400);
  const check4b = await evl(`(() => {
    const q = document.querySelector('#tok-q');
    return JSON.stringify({ after_debounce_activeElement: document.activeElement === document.body ? 'BODY' : document.activeElement.tagName + '#' + document.activeElement.id, focusRestoredToTokQ: document.activeElement === q });
  })()`);
  console.log('tokens after 400ms (draw+restore ran):', check4b);
}

console.log('\nDONE');
ws.close();
cp.kill();
process.exit(0);
