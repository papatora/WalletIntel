// WalletIntel AutoLogin — shared state marker util.
// Konvensi (dibaca oleh CDP automation):
//   document.documentElement.dataset.wiLogin   = "ok" | "logged_out" | "working"
//   document.documentElement.dataset.wiSite     = "arkham" | "gmgn" | "cielo"
//   document.documentElement.dataset.wiUpdated  = epoch ms
// CDP bisa memicu login ulang: dispatch CustomEvent "wi-login-now" di window.

(function () {
  const root = document.documentElement;

  function setState(s) {
    root.dataset.wiSite = window.__wiSite || "unknown";
    root.dataset.wiLogin = s;
    root.dataset.wiUpdated = String(Date.now());
    // laporkan ke background utk popup
    try {
      chrome.runtime.sendMessage({type: "wi-state", site: window.__wiSite, state: s});
    } catch (e) { /* extension context invalid saat reload */ }
  }

  window.__wiSetState = setState;

  // S-50b: COMMAND CHANNEL via DOM attribute (isolated world tidak melihat
  // window/function main-world; dataset element = shared lintas world).
  // CDP: document.documentElement.dataset.wiCmd = "login"; .dataset.wiCmdTs = Date.now()
  let lastCmdTs = "0";
  setInterval(() => {
    const root2 = document.documentElement;
    const ts = root2.dataset.wiCmdTs || "0";
    if (ts !== lastCmdTs && root2.dataset.wiCmd === "login") {
      lastCmdTs = ts;
      root2.dataset.wiCmd = "";
      root2.dataset.wiState = "working";
      if (typeof window.__wiTryLogin === "function") {
        try { window.__wiTryLogin(); } catch (e) { /* quiet */ }
      }
    }
  }, 1000);

  // polling ringan — SPA berubah-ubah tanpa reload
  setInterval(() => {
    if (typeof window.__wiDetect === "function") {
      try { window.__wiDetect(); } catch (e) { /* quiet */ }
    }
  }, 5000);

  // S-51j AUTO-HEAL: selama logged_out, coba login ulang tiap 45 detik
  // (form kadang butuh beberapa attempt — Cloudflare/redirect/autofill timing).
  // Berhenti otomatis begitu state ok.
  setInterval(() => {
    const root2 = document.documentElement;
    if (root2.dataset.wiLogin === "logged_out" && typeof window.__wiTryLogin === "function") {
      try { window.__wiTryLogin(); } catch (e) { /* quiet */ }
    }
  }, 45000);

  if (typeof window.__wiDetect === "function") {
    try { window.__wiDetect(); } catch (e) { /* quiet */ }
  }
})();
