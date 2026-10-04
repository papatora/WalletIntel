// Cielo (app.cielo.finance) login keeper.
// Logout: /api/session body "null" atau tombol Connect.
// Login ulang: klik Connect → Rabby → (burn wallet user).

(function () {
  const SITE = "cielo";
  let lastState = "";
  let busy = false;

  async function querySession() {
    try {
      const r = await fetch("/api/session", {credentials: "include"});
      const t = await r.text();
      return !(t === "null" || t.trim() === "");
    } catch (e) { return lastState === "ok"; }
  }

  function findConnectButton() {
    for (const el of document.querySelectorAll("button, a, div[role='button']")) {
      const t = (el.innerText || "").trim().toLowerCase();
      if (t === "connect" || t === "connect wallet") return el;
    }
    return null;
  }

  async function tryLogin() {
    if (busy) return;
    busy = true;
    window.__wiSetState("working");
    try {
      const b = findConnectButton();
      if (b) {
        b.click();
        await new Promise(r => setTimeout(r, 2500));
      }
      for (let i = 0; i < 12; i++) {
        let picked = false;
        for (const el of document.querySelectorAll("button, div[role='button'], li")) {
          const t = (el.innerText || "").trim().toLowerCase();
          if (t === "rabby" || t.startsWith("rabby")) { el.click(); picked = true; break; }
        }
        if (picked) break;
        await new Promise(r => setTimeout(r, 1000));
      }
      await new Promise(r => setTimeout(r, 6000));
      await detect();
    } finally {
      busy = false;
    }
  }

  async function detect() {
    if (location.hostname !== "app.cielo.finance") return;
    const ok = await querySession();
    lastState = ok ? "ok" : "logged_out";
    window.__wiSetState(lastState);
  }

  window.__wiSite = SITE;
  window.__wiDetect = detect;
  window.__wiTryLogin = tryLogin;
})();
