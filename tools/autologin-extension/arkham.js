// Arkham (arkm.com) login keeper — v1.1 (28 Okt 2026, permintaan user: "login
// tanpa di sentuh"). Perbaikan v1.0 yang gagal di lapangan: form login Arkham
// DUA LANGKAH (email → klik "Continue" → password → "Log In"), tapi v1.0 baru
// bertindak kalau input email+password muncul BERSAMAAN → autofill terisi,
// "Continue" tidak pernah diklik (laporan user: "udah autofill tinggal klik
// continue").
// Deteksi logout: tombol "Log In"/"Sign Up" terlihat ATAU /login di path.
// Login ulang: kredensial dari extension storage (popup, diisi sekali) →
// fallback WebCredential autofill browser → tidak ada dua-duanya = needs_human.
// Klik kokoh utk React: sekuens pointerdown/mousedown/pointerup/mouseup/click
// + fallback form.requestSubmit() + event Enter. Tombol SSO (Google/Apple/
// wallet) DIKELUARKAN dari kandidat submit.
// State utk CDP: ok | logged_out | working | needs_human.

(function () {
  const SITE = "arkham";
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  const visible = (el) => !!(el && (el.offsetParent !== null || el.getClientRects().length));

  function findLoginButton() {
    for (const el of document.querySelectorAll("button, a")) {
      const t = (el.innerText || "").trim().toLowerCase();
      if (t === "log in" || t === "login" || t === "sign in") return el;
    }
    return null;
  }

  function loggedIn() {
    if (location.pathname.startsWith("/login")) return false;
    const visibleLogin = [...document.querySelectorAll("button, a")]
      .filter((el) => (el.innerText || "").trim().toLowerCase() === "log in")
      .some((el) => el.offsetParent !== null && getComputedStyle(el).display !== "none");
    if (visibleLogin) return false;
    return true;
  }

  // ---- input finder (visible-only; email bisa type=text di beberapa langkah) ----
  function emailInput() {
    return [...document.querySelectorAll("input")].find(
      (i) => visible(i) && (i.type === "email" || /email/i.test(i.name || "") || /email/i.test(i.autocomplete || "") || /e-?mail/i.test(i.placeholder || ""))
    );
  }
  function passInput() {
    return [...document.querySelectorAll("input")].find((i) => visible(i) && i.type === "password");
  }

  // ---- klik kokoh: React dkk butuh sekuens pointer penuh, bukan cuma .click() ----
  function realClick(el) {
    try {
      const r = el.getBoundingClientRect();
      const base = { bubbles: true, cancelable: true, view: window, button: 0, buttons: 1,
        clientX: Math.round(r.x + r.width / 2), clientY: Math.round(r.y + r.height / 2) };
      el.dispatchEvent(new PointerEvent("pointerdown", base));
      el.dispatchEvent(new MouseEvent("mousedown", base));
      el.dispatchEvent(new PointerEvent("pointerup", { ...base, buttons: 0 }));
      el.dispatchEvent(new MouseEvent("mouseup", { ...base, buttons: 0 }));
    } catch (e) { /* older engine tanpa PointerEvent */ }
    el.click();
  }

  // ---- kandidat tombol submit: teks umum, TANPA tombol SSO/wallet ----
  const SSO_RE = /google|apple|wallet|metamask|rabby|phantom|coinbase|twitter|\bsso\b|single sign|microsoft|telegram|discord/i;
  function submitButton(anchor) {
    const all = [...document.querySelectorAll("button, [role='button'], input[type='submit']")]
      .filter((b) => visible(b) && !b.disabled)
      .filter((b) => !SSO_RE.test((b.innerText || b.value || "")));
    // prioritas: satu form dengan input anchor (kalau ada), baru sisanya
    const form = anchor && anchor.closest("form");
    const pool = form ? [...all.filter((b) => b.closest("form") === form), ...all.filter((b) => b.closest("form") !== form)] : all;
    const texts = ["continue", "log in", "login", "sign in", "submit", "next"];
    for (const want of texts) {
      const exact = pool.find((b) => (b.innerText || b.value || "").trim().toLowerCase() === want);
      if (exact) return exact;
    }
    for (const want of texts) {
      const pref = pool.find((b) => (b.innerText || b.value || "").trim().toLowerCase().startsWith(want));
      if (pref) return pref;
    }
    return pool.find((b) => (b.type || "") === "submit") || null;
  }

  function setter(el, val) {
    const proto = Object.getPrototypeOf(el);
    Object.getOwnPropertyDescriptor(proto, "value").set.call(el, val);
    el.dispatchEvent(new Event("input", { bubbles: true }));
    el.dispatchEvent(new Event("change", {bubbles: true}));
  }

  async function waitFor(fn, ms, step = 300) {
    const t0 = Date.now();
    while (Date.now() - t0 < ms) {
      const v = fn();
      if (v) return v;
      await sleep(step);
    }
    return null;
  }

  async function getCred() {
    try {
      const st = await chrome.storage.local.get(["wi_arkham_email", "wi_arkham_pass"]);
      if (st.wi_arkham_email && st.wi_arkham_pass) return { id: st.wi_arkham_email, password: st.wi_arkham_pass };
    } catch (e) { /* storage gagal → fallback */ }
    try {
      for (const f of [emailInput(), passInput()].filter(Boolean)) {
        f.focus();
        f.dispatchEvent(new Event("focus", { bubbles: true }));
        await sleep(300);
      }
      const c = await navigator.credentials.get({ password: true, mediation: "optional" });
      if (c && c.type === "password") return { id: c.id, password: c.password };
    } catch (e) { /* belum save / butuh gesture */ }
    return null;
  }

  let busy = false;
  async function tryLogin() {
    if (busy) return;
    busy = true;
    window.__wiSetState("working");
    try {
      if (!location.pathname.startsWith("/login")) {
        const b = findLoginButton();
        if (b) { realClick(b); await sleep(2500); }
      }
      if (!location.pathname.startsWith("/login")) {
        location.href = "https://arkm.com/login";
        return; // reload akan re-run content script
      }
      const cred = await getCred();
      if (!cred) { window.__wiSetState("needs_human"); return; }

      // LANGKAH 1 — email (form dua-langkah: password belum muncul)
      const email = await waitFor(emailInput, 8000);
      if (email) {
        if (!email.value) { setter(email, cred.id); await sleep(500); } // autofill sudah isi → skip
        if (!passInput()) {
          const b1 = submitButton(email);
          if (b1) { realClick(b1); } // "Continue" — inilah langkah yang dulu tidak pernah jalan
          else if (email.closest("form") && email.closest("form").requestSubmit) email.closest("form").requestSubmit();
        }
        // tunggu langkah 2 (password) muncul, atau ternyata langsung login (SSO cookie dsb)
        await waitFor(() => passInput() || loggedIn(), 10000);
      }

      // LANGKAH 2 — password (langsung satu form, maupun setelah Continue)
      const pass = passInput();
      if (pass && !loggedIn()) {
        if (!pass.value) { setter(pass, cred.password); await sleep(500); }
        const e2 = emailInput();
        if (e2 && !e2.value) { setter(e2, cred.id); await sleep(300); }
        const b2 = submitButton(pass);
        if (b2) realClick(b2);
        else {
          const form = pass.closest("form");
          if (form && form.requestSubmit) form.requestSubmit();
          else {
            for (const t of ["keydown", "keypress", "keyup"])
              pass.dispatchEvent(new KeyboardEvent(t, { key: "Enter", code: "Enter", bubbles: true }));
          }
        }
      }

      const okNow = await waitFor(loggedIn, 15000);
      if (!okNow) {
        // satu putaran gagal (mis. CF interstitial / timing) — auto-heal 45 dtk akan coba lagi
        window.__wiSetState("logged_out");
        return;
      }
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
