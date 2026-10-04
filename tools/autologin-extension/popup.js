// Popup: tampilkan state login per situs + tombol aksi.

const CLS = {ok: "ok", logged_out: "out", working: "work"};

function refresh() {
  chrome.storage.local.get(null, (all) => {
    for (const site of ["arkham", "gmgn", "cielo"]) {
      const el = document.getElementById("s-" + site);
      const st = all["state_" + site];
      if (!st) { el.textContent = "belum dicek"; continue; }
      el.textContent = st.state;
      el.className = CLS[st.state] || "";
    }
  });
}
refresh();
setInterval(refresh, 2000);

document.getElementById("open").onclick = () => {
  chrome.runtime.sendMessage({type: "wi-open-all"});
};

document.getElementById("relogin").onclick = async () => {
  const [tab] = await chrome.tabs.query({active: true, currentWindow: true});
  if (!tab) return;
  await chrome.scripting.executeScript({
    target: {tabId: tab.id},
    func: () => window.dispatchEvent(new CustomEvent("wi-login-now")),
  });
};

document.getElementById("save").onclick = () => {
  const email = document.getElementById("wi-email").value.trim();
  const pass = document.getElementById("wi-pass").value;
  if (!email || !pass) return;
  chrome.storage.local.set({wi_arkham_email: email, wi_arkham_pass: pass}, () => {
    document.getElementById("saved-msg").textContent = "Tersimpan ✓ (lokal extension saja)";
    document.getElementById("wi-pass").value = "";
  });
};
