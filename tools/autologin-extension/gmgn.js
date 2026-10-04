// GMGN (gmgn.ai) login keeper.
// Logout: tombol "Connect"/"Connect Wallet"/"Connect your wallet" terlihat.
// Login ulang: klik tombol Connect → pilih Rabby di modal wallet (burn wallet
// user khusus scraping) → Rabby inject provider; approval signature dilakukan
// di window Rabby — utk burn wallet user memilih auto-approve bila tersedia.
// Catatan: beberapa flow sign butuh klik manusia di popup Rabby — state
// "needs_human" memberi sinyal itu ke CDP/user.

(function () {
  const SITE = "gmgn";

  function findConnectButton() {
    for (const el of document.querySelectorAll("button, a, div[role='button']")) {
      const t = (el.innerText || "").trim().toLowerCase();
      if (t === "connect" || t === "connect wallet" || t === "connect your wallet"
          || t.startsWith("connect wallet")) {
        return el;
      }
    }
    return null;
  }

  function loggedIn() {
    // cookie sid + tidak ada tombol connect
    const hasSid = document.cookie.split(";").some(c => c.trim().startsWith("sid="));
    const connect = findConnectButton();
    if (connect && getComputedStyle(connect).display !== "none"
        && connect.offsetParent !== null) return false;
    return hasSid;
  }

  let busy = false;

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
      // modal wallet list: pilih Rabby
      let picked = false;
      for (let i = 0; i < 12 && !picked; i++) {
        for (const el of document.querySelectorAll("button, div[role='button'], li, a")) {
          const t = (el.innerText || "").trim().toLowerCase();
          if (t === "rabby" || t.startsWith("rabby")) {
            el.click(); picked = true; break;
          }
        }
        if (!picked) await new Promise(r => setTimeout(r, 1000));
      }
      await new Promise(r => setTimeout(r, 6000));
      window.__wiDetect();
    } finally {
      busy = false;
    }
  }

  function detect() {
    if (!/^(www\.)?gmgn\.ai$/.test(location.hostname)) return;
    const st = loggedIn() ? "ok" : "logged_out";
    window.__wiSetState(st);
  }

  window.__wiSite = SITE;
  window.__wiDetect = detect;
  window.__wiTryLogin = tryLogin;
})();
