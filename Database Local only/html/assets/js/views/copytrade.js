import { S } from '../lib/store.js';
import { esc, nf, usd, short } from '../lib/fmt.js';
import { thead, emptyRow } from '../lib/ui.js';

// CopyTrade (S-53) — permukaan explorer utk panen GMGN CopyTrade yang
// selama ini cuma hidup di file results/gmgn_web/ dan dilebur ke KOL & X.
//   Rank  = results/gmgn_web/rank_robinhood_<tag>_<period>.json (posisi row
//           dalam file = posisi rank utk period itu; GMGN tidak expose field
//           khusus 1d — order file JUJUR adalah ranking-nya).
//   TopCallers = wallet_social dgn extra caller_* (endpoint callout rank).
// Angka GMGN = klaim eksternal (belum verifier R1-R3) — jangan dianggap final.

const st = { view: 'rank', tag: 'smart_degen', period: '1d', sort: 'rank', dir: 1, page: 0, per: 50 };

const TAG_LABEL = {
  smart_degen: 'Smart Money', kol: 'KOL', renowned: 'Renowned',
  dev: 'Dev', pump_smart: 'Pump Smart', fresh_wallet: 'Fresh Wallet',
};
const PERIODS = ['1d', '7d', '30d'];

const RANK_COLS = [
  { k: 'rank', label: '#' },
  { k: 'a', label: 'Wallet' },
  { k: 'x', label: 'X' },
  { k: 'r30', label: 'Realized 30d', rt: 1, sort: 1 },
  { k: 'p30', label: 'PnL mult 30d', rt: 1, sort: 1 },
  { k: 'p7', label: 'PnL mult 7d', rt: 1, sort: 1 },
  { k: 'w30', label: 'Winrate 30d', rt: 1, sort: 1 },
  { k: 'v30', label: 'Volume 30d', rt: 1, sort: 1 },
  { k: 'tx', label: 'Txs 30d', rt: 1, sort: 1 },
  { k: 'trk', label: 'Tracked', rt: 1, sort: 1 },
  { k: 't', label: 'Tags' },
];

const CALLER_COLS = [
  { k: 'r', label: '#' },
  { k: 'a', label: 'Wallet' },
  { k: 'x', label: 'X' },
  { k: 'calls', label: 'Calls', rt: 1, sort: 1 },
  { k: 'mult', label: 'Avg multiplier', rt: 1, sort: 1 },
  { k: 'net', label: 'Net flow est.', rt: 1, sort: 1 },
  { k: 'p30', label: 'PnL mult 30d', rt: 1, sort: 1 },
];

const num = v => { const f = parseFloat(v); return isNaN(f) ? null : f; };

function tagKeys() {
  const t = Object.keys(S.copytrade?.tags || {});
  // urutan enak dibaca; tag di luar daftar tetap ikut di belakang
  const pref = ['smart_degen', 'kol', 'renowned', 'dev', 'pump_smart', 'fresh_wallet'];
  return [...pref.filter(p => t.includes(p)), ...t.filter(x => !pref.includes(x))];
}

function rankRows() {
  const tags = S.copytrade?.tags || {};
  const slot = tags[st.tag] || {};
  let rows = (slot[st.period] || []).map((r, i) => ({ ...r, rank: i + 1 }));
  if (st.sort !== 'rank') {
    const key = st.sort;
    const val = r => {
      if (key === 'r30') return num(r.realized_profit_30d) ?? -1e18;
      if (key === 'p30') return num(r.pnl_30d) ?? -1e18;
      if (key === 'p7') return num(r.pnl_7d) ?? -1e18;
      if (key === 'w30') return num(r.winrate_30d) ?? -1e18;
      if (key === 'v30') return num(r.volume_30d) ?? -1e18;
      if (key === 'tx') return num(r.txs_30d) ?? -1e18;
      if (key === 'trk') return num(r.follow_count) ?? -1e18;
      return -1e18;
    };
    rows = [...rows].sort((a, b) => (val(b) - val(a)) * (st.dir === 1 ? -1 : 1));
    rows = rows.map((r, i) => ({ ...r, rank: i + 1 }));
  }
  return rows;
}

function callerRows() {
  let rows = Object.entries(S.social || {})
    .map(([a, e]) => {
      const ck = e.rank || {};
      return {
        a, x: e.x_primary, name: e.name, fans: e.fans,
        calls: num(ck.caller_total_calls),
        mult: num(ck.caller_avg_multiplier),
        p30: num(e.rank?.pnl_30d),
      };
    })
    .filter(r => r.calls);
  const key = st.sort;
  const val = r => {
    if (key === 'calls') return r.calls ?? -1e18;
    if (key === 'mult') return r.mult ?? -1e18;
    if (key === 'p30') return r.p30 ?? -1e18;
    const ls = (S.addrIndex || new Map()).get(r.a);
    const s = ls != null ? S.statsAll.get(ls) : null;
    if (key === 'net') return s?.net ?? -1e18;
    return -1e18;
  };
  rows.sort((a, b) => (val(b) - val(a)) * (st.dir === 1 ? -1 : 1));
  return rows;
}

function xCell(x) {
  return x ? `<a class="link mono" href="https://x.com/${esc(x)}" target="_blank" rel="noopener">@${esc(x)}</a>`
           : '<span class="t2">—</span>';
}

export function render(root) {
  const tags = tagKeys();
  if (tags.length) {
    if (!tags.includes(st.tag)) st.tag = tags[0];
  }
  const draw = () => {
    const tags2 = S.copytrade?.tags || {};
    const nProfil = new Set();
    for (const tg of Object.values(tags2)) for (const per of Object.values(tg || {}))
      for (const r of per || []) nProfil.add(r.address);
    const isRank = st.view === 'rank';
    const rows = isRank ? rankRows() : callerRows();
    const cols = isRank ? RANK_COLS : CALLER_COLS;
    const pages = Math.max(1, Math.ceil(rows.length / st.per));
    st.page = Math.min(st.page, pages - 1);
    const slice = rows.slice(st.page * st.per, (st.page + 1) * st.per);
    const updated = (S.copytrade?.updated || '').slice(0, 16).replace('T', ' ');

    const body = isRank ? slice.map(r => `
      <tr>
        <td class="t2">${r.rank}</td>
        <td><a class="link mono" href="#/address/${r.address}">${esc(r.nickname || r.name || short(r.address))}</a><span class="t2" style="margin-left:6px">${short(r.address, 6, 4)}</span></td>
        <td>${xCell(r.twitter_username)}</td>
        <td class="rt">${r.realized_profit_30d != null ? usd(num(r.realized_profit_30d), true) : '<span class="t2">—</span>'}</td>
        <td class="rt">${r.pnl_30d != null ? (num(r.pnl_30d) * 100).toFixed(0) + '%' : '<span class="t2">—</span>'}</td>
        <td class="rt">${r.pnl_7d != null ? (num(r.pnl_7d) * 100).toFixed(0) + '%' : '<span class="t2">—</span>'}</td>
        <td class="rt">${r.winrate_30d != null ? (num(r.winrate_30d) * 100).toFixed(0) + '%' : '<span class="t2">—</span>'}</td>
        <td class="rt t2">${r.volume_30d != null ? usd(num(r.volume_30d), true) : '—'}</td>
        <td class="rt t2">${r.txs_30d != null ? nf(r.txs_30d) : '—'}</td>
        <td class="rt t2">${r.follow_count != null ? nf(r.follow_count) : '—'}</td>
        <td>${(r.tags || []).slice(0, 3).map(t => `<span class="fchip">${esc(t)}</span>`).join(' ') || '<span class="t2">—</span>'}</td>
      </tr>`).join('') : slice.map((r, i) => {
        const ls = (S.addrIndex || new Map()).get(r.a);
        const s = ls != null ? S.statsAll.get(ls) : null;
        return `
      <tr>
        <td class="t2">${st.page * st.per + i + 1}</td>
        <td><a class="link mono" href="#/address/${r.a}">${esc(r.name || short(r.a))}</a></td>
        <td>${xCell(r.x)}</td>
        <td class="rt">${r.calls ?? '—'}</td>
        <td class="rt">${r.mult != null ? r.mult.toFixed(2) + 'x' : '<span class="t2">—</span>'}</td>
        <td class="rt">${s ? `<span class="${s.net >= 0 ? 'pos' : 'neg'}">${usd(s.net, true)}</span>` : '<span class="t2">—</span>'}</td>
        <td class="rt">${r.p30 != null ? (r.p30 * 100).toFixed(0) + '%' : '<span class="t2">—</span>'}</td>
      </tr>`;}).join('');

    root.innerHTML = `
      <div class="page">
        <h1 class="page-title">GMGN CopyTrade — Robinhood</h1>
        <p class="t2" style="max-width:82ch">Hasil panen tab CopyTrade GMGN (Rank per tag &amp; periode + TopCallers) via endpoint
        <span class="mono">/api/v1/rank/…</span> &amp; callout — sama dengan tab Rank / TopCallers di gmgn.ai. Urutan baris file = posisi rank periode tsb.
        <b>Angka = klaim eksternal GMGN</b> (belum lewat verifier R1-R3 internal). Deep-harvest cursor masih dicabut sisi GMGN (depth 100/tag).</p>
        <div class="toolbar" style="display:flex;gap:10px;flex-wrap:wrap;align-items:center;margin:10px 0">
          <div class="seg">
            <button class="seg-btn ${isRank ? 'is-active' : ''}" data-view="rank">Rank</button>
            <button class="seg-btn ${!isRank ? 'is-active' : ''}" data-view="callers">TopCallers</button>
          </div>
          ${isRank ? `
          <select id="ct-tag" class="input">${tags.map(t => `<option value="${t}" ${st.tag === t ? 'selected' : ''}>${TAG_LABEL[t] || t}</option>`).join('')}</select>
          <div class="seg">${PERIODS.map(p => `<button class="seg-btn ${st.period === p ? 'is-active' : ''}" data-period="${p}">${p.toUpperCase()}</button>`).join('')}</div>` : ''}
          <span class="t2">${isRank
            ? `${nf(rows.length)} wallet · ${nProfil.size} profil unik · ${Object.keys(tags2).length} tag · update ${updated || '—'} UTC`
            : `${nf(rows.length)} caller ber-identitas`}</span>
        </div>
        <div class="card"><table class="table">
          <thead>${thead(cols, st)}</thead>
          <tbody>${body || emptyRow(cols.length, 'Belum ada data — jalankan scripts/gmgn_web_rank.py lalu rebuild dataset.')}</tbody>
        </table></div>
        ${pages > 1 ? `<div class="pager" style="display:flex;gap:6px;margin-top:10px">
          <button class="btn" id="ct-prev" ${st.page === 0 ? 'disabled' : ''}>‹ Prev</button>
          <span class="t2" style="align-self:center">halaman ${st.page + 1}/${pages}</span>
          <button class="btn" id="ct-next" ${st.page >= pages - 1 ? 'disabled' : ''}>Next ›</button>
        </div>` : ''}
      </div>`;

    root.querySelectorAll('[data-view]').forEach(b =>
      b.addEventListener('click', () => { st.view = b.dataset.view; st.sort = st.view === 'rank' ? 'rank' : 'calls'; st.dir = 1; st.page = 0; draw(); }));
    root.querySelector('#ct-tag')?.addEventListener('change', ev => { st.tag = ev.target.value; st.page = 0; draw(); });
    root.querySelectorAll('[data-period]').forEach(b =>
      b.addEventListener('click', () => { st.period = b.dataset.period; st.page = 0; draw(); }));
    root.querySelector('#ct-prev')?.addEventListener('click', () => { st.page--; draw(); });
    root.querySelector('#ct-next')?.addEventListener('click', () => { st.page++; draw(); });
  };
  draw();
  root.addEventListener('click', ev => {
    const th = ev.target.closest('th[data-sort]');
    if (!th) return;
    const k = th.dataset.sort;
    if (st.sort === k) { st.dir = -st.dir; } else { st.sort = k; st.dir = -1; }
    st.page = 0; draw();
  });
}
