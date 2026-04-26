import os
import time
import json
import requests
from datetime import datetime

# ── CONFIG ──
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "8349807507:AAFoAH1o2KI8Sat40qAzrEKycsI_88eBDmY")
CHAT_ID        = os.environ.get("CHAT_ID", "7527717890")
ANTHROPIC_KEY  = os.environ.get("ANTHROPIC_KEY", "")
CHECK_INTERVAL = int(os.environ.get("CHECK_INTERVAL", "900"))  # 15 minutes default

KEYWORDS = [
    "equipment operator light vehicle",
    "equipment operator",
    "light vehicle",
]

EMIRATES_URL = "https://www.emiratesgroupcareers.com/search-and-apply/?jobcategory=Airline%20--%20Airport%20Operations"

# ── SEND TELEGRAM MESSAGE ──
def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": "HTML",
        "disable_web_page_preview": False
    }
    try:
        r = requests.post(url, json=data, timeout=10)
        print(f"Telegram sent: {r.status_code}")
    except Exception as e:
        print(f"Telegram error: {e}")

# ── SEARCH VIA ANTHROPIC API ──
def search_jobs():
    if not ANTHROPIC_KEY:
        print("No Anthropic key set!")
        return []

    kw_list = "\n".join([f'Search Google for: site:emiratesgroupcareers.com "{kw}"' for kw in KEYWORDS])

    prompt = f"""You are a job search assistant. Search Google right now for these specific jobs on Emirates Careers website.

{kw_list}

For EACH keyword, respond in this EXACT format:

KEYWORD: [keyword]
STATUS: FOUND or NOT_FOUND
DETAIL: [exact job title if found, or "Not currently listed"]

Only say FOUND if you can confirm the exact job is currently live on emiratesgroupcareers.com right now."""

    headers = {
        "Content-Type": "application/json",
        "x-api-key": ANTHROPIC_KEY,
        "anthropic-version": "2023-06-01"
    }

    body = {
        "model": "claude-opus-4-5",
        "max_tokens": 500,
        "tools": [{"type": "web_search_20250305", "name": "web_search"}],
        "messages": [{"role": "user", "content": prompt}]
    }

    try:
        r = requests.post("https://api.anthropic.com/v1/messages", headers=headers, json=body, timeout=60)
        if r.status_code != 200:
            print(f"API error {r.status_code}: {r.text}")
            return []

        data = r.json()
        text_blocks = [b["text"] for b in data.get("content", []) if b.get("type") == "text"]
        reply = "\n".join(text_blocks).strip()
        print(f"AI reply:\n{reply}")
        return parse_results(reply)

    except Exception as e:
        print(f"Search error: {e}")
        return []

# ── PARSE RESULTS ──
def parse_results(text):
    results = []
    blocks = text.split("KEYWORD:")
    for block in blocks:
        block = block.strip()
        if not block:
            continue
        lines = block.split("\n")
        keyword = lines[0].strip().strip('"\'')
        status = "NOT_FOUND"
        detail = "Not currently listed"
        for line in lines:
            if "STATUS:" in line.upper():
                if "FOUND" in line.upper() and "NOT_FOUND" not in line.upper():
                    status = "FOUND"
            if "DETAIL:" in line.upper():
                detail = line.split(":", 1)[-1].strip()
        if keyword:
            results.append({"keyword": keyword, "status": status, "detail": detail})
    return results

# ── MAIN LOOP ──
def main():
    print("🚀 Emirates Job Radar Bot started!")
    print(f"📋 Watching for: {', '.join(KEYWORDS)}")
    print(f"⏱ Checking every {CHECK_INTERVAL} seconds ({CHECK_INTERVAL//60} minutes)")

    # Send startup message
    send_telegram(
        "✅ <b>Emirates Job Radar Started!</b>\n\n"
        f"👀 Watching for:\n" +
        "\n".join([f"• {kw}" for kw in KEYWORDS]) +
        f"\n\n⏱ Checking every {CHECK_INTERVAL//60} minutes\n"
        f"🔗 {EMIRATES_URL}"
    )

    check_count = 0

    while True:
        check_count += 1
        now = datetime.now().strftime("%H:%M:%S")
        print(f"\n[{now}] Check #{check_count} — searching...")

        results = search_jobs()

        found = [r for r in results if r["status"] == "FOUND"]

        if found:
            for r in found:
                msg = (
                    f"🚨 <b>JOB FOUND!</b>\n\n"
                    f"✅ <b>{r['keyword'].title()}</b> is now live on Emirates Careers!\n\n"
                    f"📋 Job: {r['detail']}\n\n"
                    f"👇 <b>Apply NOW:</b>\n"
                    f"{EMIRATES_URL}\n\n"
                    f"⏰ Found at: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}"
                )
                send_telegram(msg)
                print(f"✅ FOUND: {r['keyword']}")
        else:
            print(f"✗ Not found yet. Next check in {CHECK_INTERVAL//60} minutes.")
            # Send silent status every 2 hours (8 checks at 15 min)
            if check_count % 8 == 0:
                send_telegram(
                    f"📊 <b>Status Update</b>\n\n"
                    f"✓ {check_count} checks done\n"
                    f"❌ Job not posted yet\n"
                    f"👀 Still watching every {CHECK_INTERVAL//60} minutes\n"
                    f"🕐 Last check: {datetime.now().strftime('%H:%M')}"
                )

        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()
