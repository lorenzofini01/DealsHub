import os
import re
import asyncio
import httpx
from telethon import TelegramClient, events
from urllib.parse import urlparse

# --- CONFIGURAZIONE ---
API_ID = int(os.getenv("TELEGRAM_API_ID"))
API_HASH = os.getenv("TELEGRAM_API_HASH")
SESSION = os.getenv("TELEGRAM_SESSION", "collector")
BACKEND = os.getenv("BACKEND_URL", "http://backend:8000")
PHONE = os.getenv("TELEGRAM_PHONE")
HISTORY_LIMIT = int(os.getenv("HISTORY_LIMIT", "100"))

# WhiteList: Domini sicuramente buoni
SHOP_DOMAINS = ["amazon", "amzn", "ebay", "unieuro", "mediaworld", "monclick", "zalando", "nike", "adidas"]
# GreyList: Shortener che potrebbero portare a shop (li teniamo e li controlla il worker)
SHORTENERS = ["bit.ly", "amzlink", "t.eeny", "offerte", "link", "cutt.ly", "tinyurl", "tr.ee"]
# BlackList: Domini da ignorare SEMPRE
BLOCKED_DOMAINS = ["t.me", "telegram.me", "youtube", "facebook", "instagram", "tiktok", "wa.me", "twitter"]

client = TelegramClient(SESSION, API_ID, API_HASH)
URL_PATTERN = re.compile(r'(https?://[a-zA-Z0-9.-]+(?:/[^\s()<>.,;]*)?)')


def is_useful_link(url):
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()

        # 1. Se è nella Blacklist, via subito
        if any(b in domain for b in BLOCKED_DOMAINS):
            return False

        # 2. Deve essere o uno Shop o uno Shortener
        is_shop = any(s in domain for s in SHOP_DOMAINS)
        is_short = any(s in domain for s in SHORTENERS)

        return is_shop or is_short
    except:
        return False


async def send_to_backend(http_client, payload):
    try:
        resp = await http_client.post(f"{BACKEND}/api/v2/offers/ingest", json=payload, timeout=10)
        if resp.status_code == 201:
            print(f"✅ Inviato: {payload['url'][:40]}...")
    except Exception as e:
        print(f"❌ Errore Backend: {e}")


async def process_message(message, http_client):
    if not message.text: return
    raw_links = URL_PATTERN.findall(message.text)
    unique_links = list(set(raw_links))

    for link in unique_links:
        # Pulizia finale del link (toglie parentesi o punti alla fine)
        link = link.rstrip(".,)]}")

        if is_useful_link(link):
            payload = {
                "source": "telegram",
                "chat_id": str(message.chat_id),
                "message_id": message.id,
                "text": message.text,
                "url": link,
            }
            await send_to_backend(http_client, payload)


@client.on(events.NewMessage)
async def handler(event):
    async with httpx.AsyncClient() as http_client:
        await process_message(event.message, http_client)


async def main():
    print("🔄 Avvio Collector v2.1...")
    await client.start(phone=PHONE)
    print(f"✅ Connesso come: {(await client.get_me()).first_name}")

    print(f"📚 Backfill ultimi {HISTORY_LIMIT} messaggi...")
    async with httpx.AsyncClient() as http_client:
        dialogs = await client.get_dialogs(limit=30)
        for d in dialogs:
            if d.is_channel or d.is_group:
                print(f"   ↳ {d.name}...")
                try:
                    msgs = await client.get_messages(d, limit=HISTORY_LIMIT)
                    for m in msgs: await process_message(m, http_client)
                except:
                    pass

    print("🚀 In ascolto...")
    await client.run_until_disconnected()


if __name__ == "__main__":
    asyncio.run(main())