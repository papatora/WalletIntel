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
  window.addEventListener("wi-login-now", () => {
    if (typeof window.__wiTryLogin === "function") {
      window.__wiTryLogin();
    }
  });

  // polling ringan — SPA berubah-ubah tanpa reload
  setInterval(() => {
    if (typeof window.__wiDetect === "function") {
      try { window.__wiDetect(); } catch (e) { /* quiet */ }
    }
  }, 5000);

  if (typeof window.__wiDetect === "function") {
    try { window.__wiDetect(); } catch (e) { /* quiet */ }
  }
})();
