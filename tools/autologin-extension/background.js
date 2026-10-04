// Background: buka tab ketiga situs & pastikan content script jalan +
// pantau state login semua tab (untuk popup & debugging CDP).

const SITES = {
  arkham: "https://arkm.com/",
  gmgn: "https://gmgn.ai/?chain=robinhood",
  cielo: "https://app.cielo.finance/tracking",
};

chrome.runtime.onInstalled.addListener(() => {
  chrome.storage.local.set({installed_at: Date.now()});
});

chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (msg && msg.type === "wi-state") {
    chrome.storage.local.set({
      ["state_" + msg.site]: {state: msg.state, url: sender.tab?.url, ts: Date.now()},
    });
    sendResponse({ok: true});
  } else if (msg && msg.type === "wi-open-all") {
    for (const url of Object.values(SITES)) chrome.tabs.create({url, active: false});
    sendResponse({ok: true});
  }
  return false;
});
