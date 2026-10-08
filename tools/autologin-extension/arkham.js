// Arkham (arkm.com) login keeper.
// Deteksi logout: tombol "Log In"/"Sign Up" terlihat ATAU /login di path.
// Login ulang: klik "Log In" → email+password diisi via WebCredential
// (password tersimpan di Brave password manager profile ini — autofill
// browser yang mengisi, extension hanya memicu dan men-submit).
// Kalau autofill tidak mengisi dalam timeout → tandai "needs_human".

(function () {
  const SITE = "arkham";

  function findLoginButton() {
    for (const el of document.querySelectorAll("button, a")) {
      const t = (el.innerText || "").trim().toLowerCase();
      if (t === "log in" || t === "login" || t === "sign in") return el;
    }
    return null;
  }

  function loggedIn() {
    if (location.pathname.startsWith("/login")) return false;
    // S-50b: COOKIE DULU (paling andal) — tombol "Log In" hidden sering masih
    // ada di DOM homepage logged-in, sempat bikin deteksi false-negative.
    const visibleLogin = [...document.querySelectorAll("button, a")]
      .filter(el => (el.innerText || "").trim().toLowerCase() === "log in")
      .some(el => el.offsetParent !== null && getComputedStyle(el).display !== "none");
    if (visibleLogin) return false;
    return true;
  }

  let busy = false;

  async function tryLogin() {
    if (busy) return;
    busy = true;
    window.__wiSetState("working");
    try {
      if (!location.pathname.startsWith("/login")) {
        const b = findLoginButton();
        if (b) { b.click(); await new Promise(r => setTimeout(r, 2500)); }
      }
      if (!location.pathname.startsWith("/login")) {
        location.href = "https://arkm.com/login";
        return; // reload akan re-run content script
      }
      const email = document.querySelector("input[type='email'], input[name='email']");
      const pass = document.querySelector("input[type='password']");
      if (email && pass) {
        // Sumber 1: kredensial tersimpan di extension storage (diisi user
        // sekali via popup) — paling andal, tidak tergantung autofill browser.
        let cred = null;
        try {
          const st = await chrome.storage.local.get(["wi_arkham_email", "wi_arkham_pass"]);
          if (st.wi_arkham_email && st.wi_arkham_pass) {
            cred = {id: st.wi_arkham_email, password: st.wi_arkham_pass};
          }
        } catch (e) { /* storage gagal → fallback */ }
        // Sumber 2: WebCredential autofill browser
        if (!cred) {
          for (const f of [email, pass]) {
            f.focus();
            f.dispatchEvent(new Event("focus", {bubbles: true}));
            await new Promise(r => setTimeout(r, 400));
          }
          try {
            const c = await navigator.credentials.get({password: true, mediation: "optional"});
            if (c && c.type === "password") cred = {id: c.id, password: c.password};
          } catch (e) { /* belum save / butuh gesture */ }
        }
        if (cred) {
          const setter = (el, val) => {
            const proto = Object.getPrototypeOf(el);
            Object.getOwnPropertyDescriptor(proto, "value").set.call(el, val);
            el.dispatchEvent(new Event("input", {bubbles: true}));
            el.dispatchEvent(new Event("change", {bubbles: true}));
          };
          setter(email, cred.id);
          setter(pass, cred.password);
          await new Promise(r => setTimeout(r, 600));
          let submitted = false;
          for (const el of document.querySelectorAll("button")) {
            const t = (el.innerText || "").trim().toLowerCase();
            if (t === "log in" || t === "login" || t === "sign in"
                || t === "continue") { el.click(); submitted = true; break; }
          }
          if (!submitted) {
            // fallback: Enter di field password
            pass.dispatchEvent(new KeyboardEvent("keydown",
              {key: "Enter", code: "Enter", bubbles: true}));
            pass.dispatchEvent(new KeyboardEvent("keypress",
              {key: "Enter", code: "Enter", bubbles: true}));
            pass.dispatchEvent(new KeyboardEvent("keyup",
              {key: "Enter", code: "Enter", bubbles: true}));
          }
        }
      }
      await new Promise(r => setTimeout(r, 6000));
      window.__wiDetect();
    } finally {
      busy = false;
    }
  }

  function detect() {
    if (location.hostname !== "arkm.com") return;
    if (location.pathname.startsWith("/login")) {
      window.__wiSetState("logged_out");
      return;
    }
    window.__wiSetState(loggedIn() ? "ok" : "logged_out");
  }

  window.__wiSite = SITE;
  window.__wiDetect = detect;
  window.__wiTryLogin = tryLogin;
})();
