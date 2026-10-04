// CHECK 3 redo — real keyboard test with CORRECT coordinates (query fresh element AFTER any re-render).
import { spawn } from 'node:child_process';
const CDP_PORT = 9334;
const APP = 'http://127.0.0.1:8787';
const CHROME = 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe';
const sleep = ms => new Promise(r => setTimeout(r, ms));
const udd = process.env.TEMP + '\\wi_confirmC3_' + Date.now();
const cp = spawn(CHROME, ['--headless=new', `--remote-debugging-port=${CDP_PORT}`, `--user-data-dir=${udd}`, '--no-first-run', '--window-size=1400,900', 'about:blank'], { stdio: 'ignore' });
let version = null;
for (let i = 0; i < 50; i++) { try { version = await (await fetch(`http://127.0.0.1:${CDP_PORT}/json/version`)).json(); break; } catch { await sleep(200); } }
if (!version) { console.log('chrome-cdp-unavailable'); process.exit(2); }
const j = async (url, opts) => (await fetch(url, opts)).json();
const { id: targetId } = await j(`http://127.0.0.1:${CDP_PORT}/json/new?${encodeURIComponent(APP + '/#/kol')}`, { method: 'PUT' });
await sleep(400);
const tab = (await j(`http://127.0.0.1:${CDP_PORT}/json/list`)).find(t => t.id === targetId);
const ws = new WebSocket(tab.webSocketDebuggerUrl);
let mid = 0; const pending = new Map();
const send = (m, p = {}) => new Promise((res, rej) => { const i = ++mid; pending.set(i, { res, rej }); ws.send(JSON.stringify({ id: i, method: m, params: p })); });
ws.onmessage = ev => { const m = JSON.parse(ev.data); if (m.id && pending.has(m.id)) { pending.get(m.id).res(m.result); pending.delete(m.id); } };
await new Promise((r, e) => { ws.onopen = r; ws.onerror = e; });
const evl = async expression => { const r = await send('Runtime.evaluate', { expression, returnByValue: true }); if (r.exceptionDetails) return 'EVAL-ERROR:' + JSON.stringify(r.exceptionDetails).slice(0, 200); return r.result.value; };

let ready = null;
for (let i = 0; i < 60; i++) { await sleep(500); ready = await evl(`!!document.querySelector('#kol-q')`); if (ready) break; }
console.log('kol view rendered?', ready);
console.log('profile count:', await evl(`document.querySelector('.toolbar .t2').textContent.trim()`));

// 1. fresh rect from the LIVE element (no input dispatched before this)
const rc = JSON.parse(await evl(`(() => { const r = document.querySelector('#kol-q').getBoundingClientRect(); return JSON.stringify({ x: Math.round(r.x + 30), y: Math.round(r.y + r.height / 2), w: r.width, h: r.height }); })()`));
console.log('input rect:', JSON.stringify(rc));
await send('Input.dispatchMouseEvent', { type: 'mouseMoved', x: rc.x, y: rc.y });
await send('Input.dispatchMouseEvent', { type: 'mousePressed', x: rc.x, y: rc.y, button: 'left', clickCount: 1 });
await send('Input.dispatchMouseEvent', { type: 'mouseReleased', x: rc.x, y: rc.y, button: 'left', clickCount: 1 });
await sleep(150);
console.log('AFTER REAL CLICK:', await evl(`JSON.stringify({ active: document.activeElement === document.body ? 'BODY' : document.activeElement.tagName + '#' + document.activeElement.id, focused: document.activeElement === document.querySelector('#kol-q') })`));

// 2. clear via real Ctrl+A + Delete (fires input -> draw() -> another focus drop expected)
await send('Input.dispatchKeyEvent', { type: 'rawKeyDown', modifiers: 2, windowsVirtualKeyCode: 65, code: 'KeyA', key: 'a' });
await send('Input.dispatchKeyEvent', { type: 'keyUp', modifiers: 2, windowsVirtualKeyCode: 65, code: 'KeyA', key: 'a' });
await send('Input.dispatchKeyEvent', { type: 'rawKeyDown', windowsVirtualKeyCode: 46, code: 'Delete', key: 'Delete' });
await send('Input.dispatchKeyEvent', { type: 'keyUp', windowsVirtualKeyCode: 46, code: 'Delete', key: 'Delete' });
await sleep(300);
console.log('AFTER REAL CLEAR (Ctrl+A, Del):', await evl(`JSON.stringify({ active: document.activeElement === document.body ? 'BODY' : document.activeElement.tagName + '#' + document.activeElement.id, value: document.querySelector('#kol-q').value })`));

// 3. THE ask's user scenario: click again (user must), then type ONE real character
await send('Input.dispatchMouseEvent', { type: 'mousePressed', x: rc.x, y: rc.y, button: 'left', clickCount: 1 });
await send('Input.dispatchMouseEvent', { type: 'mouseReleased', x: rc.x, y: rc.y, button: 'left', clickCount: 1 });
await sleep(150);
console.log('AFTER RE-CLICK (user forced):', await evl(`JSON.stringify({ focused: document.activeElement === document.querySelector('#kol-q') })`));
await send('Input.dispatchKeyEvent', { type: 'keyDown', key: 'g', code: 'KeyG', text: 'g', unmodifiedText: 'g', windowsVirtualKeyCode: 71 });
await send('Input.dispatchKeyEvent', { type: 'keyUp', key: 'g', code: 'KeyG', windowsVirtualKeyCode: 71 });
const after1 = JSON.parse(await evl(`(() => { const q = document.querySelector('#kol-q'); return JSON.stringify({ active: document.activeElement === document.body ? 'BODY' : document.activeElement.tagName + '#' + document.activeElement.id, focused: document.activeElement === q, value: q.value, count: document.querySelector('.toolbar .t2').textContent.trim() }); })()`));
console.log('AFTER ONE REAL KEYSTROKE "g":', JSON.stringify(after1));
console.log('VERDICT one-keystroke-focus-loss:', after1.active === 'BODY' && after1.focused === false && after1.value === 'g');

ws.close(); cp.kill(); process.exit(0);
