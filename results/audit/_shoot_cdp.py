# Temp script: CDP screenshots untuk audit UI WalletIntel.
# Hanya membuka 1 tab baru di browser Brave yang sudah jalan (CDP 9222), tidak launch browser baru.
import gzip
import json
import urllib.request

from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:8787"
CDP = "http://127.0.0.1:9222"
OUT = r"C:\Users\ROG\Documents\ClaudeCode\AlphaIntel\WalletIntel\results\audit"


def fetch_dataset():
    raw = urllib.request.urlopen(BASE + "/api/dataset").read()
    try:
        txt = gzip.decompress(raw).decode("utf-8")
    except Exception:
        txt = raw.decode("utf-8")
    return json.loads(txt)


def page_status(page):
    body = page.inner_text("body")
    return {
        "title": page.title(),
        "url": page.url,
        "has_dataset_unavailable": "Dataset unavailable" in body,
        "body_snippet": body.strip()[:300].replace("\n", " | "),
    }


with sync_playwright() as p:
    browser = p.chromium.connect_over_cdp(CDP)
    print("contexts:", len(browser.contexts))
    ctx = browser.contexts[0]
    page = ctx.new_page()
    try:
        # 1) #/kol
        page.goto(BASE + "/#/kol")
        page.bring_to_front()
        page.wait_for_timeout(8000)
        page.bring_to_front()
        page.screenshot(path=OUT + r"\shot_kol.png", timeout=60000, animations="disabled")
        print("KOL:", json.dumps(page_status(page)))

        # 2) #/leaderboard (tab sama)
        page.goto(BASE + "/#/leaderboard")
        page.bring_to_front()
        page.wait_for_timeout(8000)
        page.bring_to_front()
        page.screenshot(path=OUT + r"\shot_leaderboard.png", timeout=60000, animations="disabled")
        print("LEADERBOARD:", json.dumps(page_status(page)))

        # 3) ambil 1 address dengan x_primary dari /api/dataset
        data = fetch_dataset()
        addr = None
        for a, info in data["social"].items():
            xp = info.get("x_primary") or ""
            if xp.strip():
                addr = a
                break
        if addr is None:
            raise RuntimeError("tidak ada address dengan x_primary di data.social")
        print("ADDR:", addr, "x_primary:", data["social"][addr]["x_primary"])

        page.goto(BASE + "/#/address/" + addr)
        page.bring_to_front()
        page.wait_for_timeout(8000)
        page.bring_to_front()
        page.screenshot(path=OUT + r"\shot_address.png", timeout=60000, animations="disabled")
        print("ADDRESS:", json.dumps(page_status(page)))
    finally:
        page.close()  # tutup tab yang dibuat script ini saja; browser & tab lain tetap hidup
        browser.close()  # hanya memutus koneksi CDP, tidak mematikan browser
