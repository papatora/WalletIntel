import { S, walletName } from '../lib/store.js';
import { esc, nf, usd } from '../lib/fmt.js';
import { icon, thead, emptyRow, walletHref } from '../lib/ui.js';

// KOL & X — wallet ber-identitas sosial (GMGN rank + Arkham, dual-scan).
// Sumber: dataset.social (tabel wallet_social). Konflik X gmgn-vs-arkham
// ditampilkan APA ADANYA (keduanya), bukan dipilih diam-diam.

const st = { src: 'all', sort: 'fans', dir: -1, page: 0, per: 50, q: '' };

const SRC_OPTIONS = [
  { v: 'all', l: 'Semua sumber' },
  { v: 'gmgn', l: 'GMGN (rank/OpenAPI)' },
  { v: 'arkham', l: 'Arkham' },
  { v: 'both', l: 'Dual-verified (keduanya)' },
  { v: 'conflict', l: '⚠ Konflik handle' },
  { v: 'caller', l: 'TopCallers' },
];

const COLS = [
  { k: 'r', label: '#' },
  { k: 'a', label: 'Wallet' },
  { k: 'x', label: 'X (Twitter)' },
  { k: 'tags', label: 'Tags' },
  { k: 'fans', label: 'Followers', rt: 1, sort: 1 },
  { k: 'pnl', label: 'Realized 30d (GMGN)', rt: 1, sort: 1 },
  { k: 'win', label: 'Winrate 30d', rt: 1, sort: 1 },
  { k: 'src', label: 'Sumber' },
];

function rows() {
  const soc = S.social || {};
  let list = Object.entries(soc);
  if (st.q) {
    const q = st.q.toLowerCase();
    list = list.filter(([a, e]) => a.includes(q)
      || (e.x_primary || '').toLowerCase().includes(q)
      || (e.name || '').toLowerCase().includes(q));
  }
  if (st.src === 'gmgn') list = list.filter(([, e]) => e.x_gmgn);
  else if (st.src === 'arkham') list = list.filter(([, e]) => e.x_arkham);
  else if (st.src === 'both') list = list.filter(([, e]) => e.x_gmgn && e.x_arkham);
  else if (st.src === 'conflict') list = list.filter(([, e]) => e.x_conflict);
  else if (st.src === 'caller') list = list.filter(([, e]) => (e.tags || []).includes('caller'));
  else list = list.filter(([, e]) => e.x_primary);

  const key = st.sort;
  const val = ([, e]) => {
    if (key === 'fans') return e.fans || 0;
    if (key === 'pnl') {
      const v = parseFloat(e.rank?.realized_profit_30d); return isNaN(v) ? -1e18 : v;
    }
    if (key === 'win') {
      const v = parseFloat(e.rank?.winrate_30d); return isNaN(v) ? -1e18 : v;
    }
    return 0;
  };
  list.sort((a, b) => (val(b) - val(a)) * -st.dir);
  return list;
}

function xCell(e) {
  const parts = [];
  if (e.x_gmgn) parts.push(`<a class="link mono" href="https://x.com/${esc(e.x_gmgn)}" target="_blank" rel="noopener">@${esc(e.x_gmgn)}</a><span class="t2">·g</span>`);
  if (e.x_arkham) parts.push(`<a class="link mono" href="https://x.com/${esc(e.x_arkham)}" target="_blank" rel="noopener">@${esc(e.x_arkham)}</a><span class="t2">·a</span>`);
  if (e.x_conflict) parts.push(`<span class="fchip is-off" title="GMGN dan Arkham melaporkan handle berbeda — keduanya ditampilkan">⚠ beda</span>`);
  return parts.join(' ') || '<span class="t2">—</span>';
}

export function render(root) {
  const draw = () => {
    const list = rows();
    const pages = Math.max(1, Math.ceil(list.length / st.per));
    st.page = Math.min(st.page, pages - 1);
    const slice = list.slice(st.page * st.per, (st.page + 1) * st.per);
    const nX = Object.values(S.social || {}).filter(e => e.x_primary).length;
    const nBoth = Object.values(S.social || {}).filter(e => e.x_gmgn && e.x_arkham).length;
    const nConf = Object.values(S.social || {}).filter(e => e.x_conflict).length;

    root.innerHTML = `
      <div class="page">
        <h1 class="page-title">KOL &amp; X Identities</h1>
        <p class="t2" style="max-width:80ch">Wallet ber-identitas sosial dari <b>GMGN</b> (CopyTrade rank + wallet profile) dan <b>Arkham</b> (entity).
        Dual-scan: kedua sumber selalu diperiksa; bila handle-nya beda, keduanya ditampilkan + flag ⚠. Angka GMGN = klaim eksternal (belum verifier internal).</p>
        <div class="toolbar" style="display:flex;gap:10px;flex-wrap:wrap;align-items:center;margin:10px 0">
          <input id="kol-q" class="input" placeholder="cari address / @handle / nama" value="${esc(st.q)}" style="min-width:240px">
          <select id="kol-src" class="input">${SRC_OPTIONS.map(o => `<option value="${o.v}" ${st.src === o.v ? 'selected' : ''}>${o.l}</option>`).join('')}</select>
          <span class="t2">${nf(list.length)} profil · ${nf(nX)} punya X · ${nBoth} dual-verified · ${nConf} konflik</span>
        </div>
        <div class="card"><table class="tbl">
          ${thead(COLS, st, (k, dir) => { st.sort = k; st.dir = dir; st.page = 0; draw(); })}
          <tbody>
          ${slice.length ? slice.map(([a, e], i) => `
            <tr>
              <td class="t2">${st.page * st.per + i + 1}</td>
              <td>${walletHref(a, walletName(a))}</td>
              <td>${xCell(e)}${e.name ? `<div class="t2">${esc(e.name)}</div>` : ''}</td>
              <td>${(e.tags || []).slice(0, 4).map(t => `<span class="fchip">${esc(t)}</span>`).join(' ') || '<span class="t2">—</span>'}</td>
              <td class="rt t2">${e.fans ? nf(e.fans) : '—'}</td>
              <td class="rt">${e.rank?.realized_profit_30d != null ? usd(parseFloat(e.rank.realized_profit_30d), true) : '<span class="t2">—</span>'}</td>
              <td class="rt">${e.rank?.winrate_30d != null ? (100 * parseFloat(e.rank.winrate_30d)).toFixed(0) + '%' : '<span class="t2">—</span>'}</td>
              <td class="t2">${e.x_gmgn && e.x_arkham ? 'gmgn+arkham' : e.x_gmgn ? 'gmgn' : 'arkham'}</td>
            </tr>`).join('') : emptyRow(COLS.length, 'Tidak ada profil yang cocok — jalankan gmgn_web_rank.py / gmgn_social_rescan.py / merge_social_x.py lalu rebuild dataset.')}
          </tbody>
        </table></div>
        ${pages > 1 ? `<div class="pager" style="display:flex;gap:6px;margin-top:10px">
          <button class="btn" id="pg-prev" ${st.page === 0 ? 'disabled' : ''}>‹ Prev</button>
          <span class="t2" style="align-self:center">halaman ${st.page + 1}/${pages}</span>
          <button class="btn" id="pg-next" ${st.page >= pages - 1 ? 'disabled' : ''}>Next ›</button>
        </div>` : ''}
      </div>`;

    root.querySelector('#kol-q')?.addEventListener('input', ev => { st.q = ev.target.value; st.page = 0; draw(); });
    root.querySelector('#kol-src')?.addEventListener('change', ev => { st.src = ev.target.value; st.page = 0; draw(); });
    root.querySelector('#pg-prev')?.addEventListener('click', () => { st.page--; draw(); });
    root.querySelector('#pg-next')?.addEventListener('click', () => { st.page++; draw(); });
  };
  draw();
}
