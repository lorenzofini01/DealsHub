from .celery_app import celery
from .database import async_session
from .models import Offer
from sqlalchemy import select, delete
import httpx
from bs4 import BeautifulSoup
import asyncio
import re
from datetime import datetime
from urllib.parse import urlparse, urlencode

# --- 1. CONFIGURAZIONE HEADERS & COOKIES ---
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "it-IT,it;q=0.9,en-US;q=0.8,en;q=0.7",
    "Cache-Control": "no-cache",
}

# FONDAMENTALE: Bypass Age Gate (Alcolici) e setta valuta
COOKIES = {
    "i18n-prefs": "EUR",
    "lc-acbit": "it_IT",
    "av-timezone": "Europe/Rome"
}

VALID_SHOPS = ["amazon", "amzn", "ebay"]

BAD_PATHS = [
    "/deals", "/music/", "/prime", "/gp/video", "/gp/prime",
    "/audible", "/kindle-dbs", "/cart", "/sign-in", "/login",
    "aws.amazon.com", "/b/", "/s?", "search", "blackfriday", "subscribe",
    "primeexclusives", "warehouse-deals", "/haul", "/minitv"
]

# --- 2. CONFIGURAZIONE CATEGORIE (FORMATO DIZIONARIO) ---
CATEGORIES = {
    "Videogiochi": ["ps5", "xbox", "switch", "nintendo", "playstation", "console", "videogioco", "game", "zelda",
                    "mario", "fifa", "cod", "dualsense", "controller", "oculus", "vr"],
    "Smartwatch & Orologi": ["apple watch", "garmin", "amazfit", "smartwatch", "orologio", "band", "fitbit", "casio",
                             "seiko", "huawei watch", "galaxy watch"],
    "Alimentari": ["mentos", "caramelle", "gomme", "cioccolato", "biscotti", "caffè", "capsule", "borbone", "lavazza",
                   "kimbo", "pasta", "olio", "vino", "birra", "acqua", "bibita", "energy drink", "red bull", "snack",
                   "proteine", "integratori", "tonno", "cibo", "gin", "rum", "whisky"],
    "Bellezza & Salute": ["profumo", "crema", "siero", "capelli", "shampoo", "bagnoschiuma", "dentifricio",
                          "spazzolino", "rasoio", "gillette", "trucco", "mascara", "make up", "cosmetici", "solare",
                          "integratore", "vitamina"],
    "Telefonia": ["iphone", "samsung galaxy", "xiaomi", "redmi", "oppo", "realme", "pixel", "smartphone", "cellulare",
                  "telefono", "cover", "vetro temperato", "pellicola", "caricatore", "powerbank", "magsafe"],
    "Audio": ["cuffie", "auricolari", "airpods", "buds", "sony", "bose", "jbl", "soundbar", "speaker",
              "cassa bluetooth", "altoparlante", "microfono"],
    "Informatica": ["notebook", "laptop", "macbook", "pc", "computer", "monitor", "tastiera", "mouse", "ipad", "tablet",
                    "ssd", "hard disk", "ram", "scheda video", "gpu", "cpu", "stampante", "toner", "cartucce", "router",
                    "wifi", "webcam", "usb", "chiavetta"],
    "Fai da Te": ["trapano", "avvitatore", "cacciavite", "makita", "bosch", "einhell", "black+decker", "bricolage",
                  "attrezzi", "cassetta", "led", "lampadina", "smart home", "presa", "interruttore", "idraulico",
                  "martello", "sega", "flex", "generatore"],
    "Casa & Cucina": ["friggitrice", "airfryer", "aspirapolvere", "robot", "roomba", "dreame", "scopa elettrica",
                      "lavatrice", "asciugatrice", "detersivo", "padella", "pentola", "cucina", "materasso", "cuscino",
                      "lenzuola", "sedie", "mobile", "arredo", "bagno", "climatizzatore", "deumidificatore"],
    "Moda": ["scarpe", "sneakers", "stivali", "t-shirt", "maglia", "felpa", "pantaloni", "jeans", "giacca", "piumino",
             "nike", "adidas", "puma", "levi's", "vans", "borsa", "zaino", "portafoglio", "cintura", "boxer", "intimo",
             "calzini"],
    "Sport": ["palestra", "fitness", "pesi", "manubri", "tapis roulant", "bici", "bicicletta", "nuoto", "calcio",
              "pallone", "tenda", "campeggio"],
    "Elettronica": ["elettronica", "tech", "gadget", "cavo", "adattatore", "batterie", "pile", "tv", "televisione",
                    "smart tv"],
}

# Lista compatibile per l'API main.py
CATEGORY_RULES = [{"id": k.lower(), "name": k, "keywords": v} for k, v in CATEGORIES.items()]


# --- 3. FUNZIONI HELPER ---

def detect_category(text):
    if not text: return "Altro"
    text = text.lower()
    for cat, keywords in CATEGORIES.items():
        if any(k in text for k in keywords): return cat
    return "Altro"


def extract_asin(url):
    match = re.search(r'/(?:dp|gp/product)/([A-Z0-9]{10})', url)
    if match: return match.group(1)
    return None


def clean_amazon_url(url, asin=None):
    if not asin: asin = extract_asin(url)
    if asin: return f"https://www.amazon.it/dp/{asin}"
    return url.split('?')[0]


def parse_price_str(text):
    if not text: return None
    try:
        clean = text.replace("€", "").replace("EUR", "").strip()
        if "," in clean and "." in clean:
            clean = clean.replace(".", "").replace(",", ".")
        elif "," in clean:
            clean = clean.replace(",", ".")
        return float(clean)
    except:
        return None


def clean_scraped_title(title):
    if not title: return None
    title = title.strip()
    for r in [" : Amazon.it", "Amazon.it: ", "Amazon.it", " | eBay", " - Acquista ora"]:
        title = title.replace(r, "")
    if len(title) < 5 or "Captcha" in title: return None
    return title


def extract_title_from_context(full_text, url):
    if not full_text: return "Offerta"
    lines = [l.strip() for l in full_text.split('\n') if l.strip()]
    url_slug = url.split('/')[-1] if '/' in url else "http"
    target_index = -1
    for i, line in enumerate(lines):
        if url in line or (len(url_slug) > 4 and url_slug in line):
            target_index = i
            break
    if target_index == -1: return re.sub(r'[^\w\s,.-]', '', lines[0])[:100]
    candidate = ""
    if target_index > 0:
        prev = lines[target_index - 1]
        if any(x in prev.lower() for x in ["passa da", "€", "sconto", "clicca", "👉", "invece di"]):
            if target_index > 1:
                candidate = lines[target_index - 2]
            else:
                candidate = prev
        else:
            candidate = prev
    cleaned = re.sub(r'^(Offerta|Sconto|Super|Prezzo|Minimo)\s+', '', candidate, flags=re.IGNORECASE)
    return cleaned if len(cleaned) > 3 else "Offerta del Giorno"


# --- 4. MOTORE DI CACCIA DATI (REGEX + SELECTORS) ---

def hunt_for_title(soup, html_text):
    # 1. Selettori
    for sel in ["#productTitle", "#title", ".product-title-word-break"]:
        t = soup.select_one(sel)
        if t: return t.get_text(strip=True)
    # 2. OpenGraph
    og = soup.select_one('meta[property="og:title"]')
    if og: return og.get("content")
    # 3. Title Tag
    if soup.title: return soup.title.string
    return None


def hunt_for_image(soup, html_text):
    # 1. Selettori
    img = soup.select_one("#landingImage, #imgBlkFront, #ebooksImgBlkFront, #main-image")
    if img: return img.get("src") or img.get("data-old-hires")
    # 2. OpenGraph
    og = soup.select_one('meta[property="og:image"]')
    if og: return og.get("content")
    # 3. Regex JSON (Fashion/Alimentari)
    patterns = [r'"hiRes":"(https://[^"]+?\.jpg)"', r'"large":"(https://[^"]+?\.jpg)"',
                r'"mainUrl":"(https://[^"]+?\.jpg)"', r'"u":"(https://[^"]+?\.jpg)"']
    for p in patterns:
        m = re.search(p, html_text)
        if m: return m.group(1).replace(r"\/", "/")
    return None


def hunt_for_price(soup, html_text):
    # 1. Selettori
    selectors = ["#corePrice_desktop .a-price-whole", "#corePriceDisplay_desktop_feature_div .a-price-whole",
                 ".a-price .a-offscreen", "#price_inside_buybox", ".apexPriceToPay .a-offscreen",
                 "#priceblock_ourprice", "#priceblock_dealprice"]
    for s in selectors:
        e = soup.select_one(s)
        if e:
            val = parse_price_str(e.get_text(strip=True))
            if val: return val
    # 2. Regex
    m = re.search(r'"priceToPay":{"amount":(\d+\.?\d*)', html_text)
    if m: return float(m.group(1))
    m = re.search(r'"buyingPrice":\s*(\d+\.?\d*)', html_text)
    if m: return float(m.group(1))
    m = re.search(r'(\d+[,.]\d{2})\s?€\s*-\s*', html_text)
    if m: return parse_price_str(m.group(1))
    return None


# --- 5. LOGICA PRINCIPALE SCRAPING ---

async def scrape_metadata(client, url):
    try:
        r = await client.get(url, headers=HEADERS, cookies=COOKIES, timeout=30, follow_redirects=True)
        final_url = str(r.url)

        is_valid_shop = any(shop in urlparse(final_url).netloc for shop in VALID_SHOPS)
        is_bad_path = any(bp in final_url for bp in BAD_PATHS)
        if not is_valid_shop or is_bad_path: return False, None, None, None, None, final_url
        if r.status_code >= 400: return True, None, None, None, None, final_url

        html = r.text
        soup = BeautifulSoup(html, "html.parser")

        is_active = True
        if "amazon" in final_url:
            if soup.select_one("#outOfStock") or "attualmente non disponibile" in html.lower(): is_active = False
        if not is_active: return False, None, None, None, None, final_url

        price = hunt_for_price(soup, html)
        image = hunt_for_image(soup, html)
        title = hunt_for_title(soup, html)

        original_price = None
        if price:
            orig_selectors = [".a-text-price .a-offscreen", "span[data-a-strike='true'] .a-offscreen",
                              ".basisPrice .a-offscreen"]
            for s in orig_selectors:
                e = soup.select_one(s)
                if e:
                    val = parse_price_str(e.get_text(strip=True))
                    if val and val > price:
                        original_price = val
                        break

        title = clean_scraped_title(title)
        return True, price, original_price, title, image, final_url
    except Exception as e:
        print(f"Err scraping: {e}")
        return True, None, None, None, None, url


# --- 6. TASK CELERY ---

@celery.task(name="app.tasks.verify_offers_task")
def verify_offers_task():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(_verify())
    finally:
        loop.close()


async def _verify():
    from .database import async_session
    async with async_session() as session:
        try:
            # Ordina per: Senza Titolo, Senza Immagine, Più vecchi
            q = select(Offer).where(Offer.status != "expired").order_by(
                Offer.title.is_(None).desc(),
                Offer.image_url.is_(None).desc(),
                Offer.updated_at.asc()
            ).limit(40)

            res = await session.execute(q)
            offers = res.scalars().all()
            if not offers: return

            async with httpx.AsyncClient() as client:
                for o in offers:
                    print(f"🚀 Processing: {o.id}...")
                    active, price, orig_price, title, image, clean_url = await scrape_metadata(client, o.product_url)

                    # Anti-Duplicati
                    asin = extract_asin(clean_url) if clean_url else None
                    if asin:
                        dup_q = select(Offer).where(Offer.product_url.contains(asin), Offer.id != o.id)
                        dup_res = await session.execute(dup_q)
                        existing = dup_res.scalars().first()
                        if existing:
                            print(f"♻️ Merge ASIN {asin}")
                            existing.updated_at = datetime.now()
                            existing.status = "active" if active else "expired"
                            if price: existing.price = price
                            await session.delete(o)
                            await session.commit()
                            continue

                    if clean_url and clean_url != o.product_url: o.product_url = clean_url

                    if not active:
                        o.status = "expired"
                    else:
                        o.status = "active"
                        if price: o.price = price
                        if orig_price: o.original_price = orig_price

                        ref_orig = orig_price or o.original_price
                        ref_price = price or o.price
                        if ref_price and ref_orig and ref_orig > ref_price:
                            o.discount = int(((ref_orig - ref_price) / ref_orig) * 100)
                        else:
                            o.discount = 0

                        if image: o.image_url = image
                        if title:
                            o.title = title
                        elif not o.title or o.title == "Offerta":
                            o.title = extract_title_from_context(o.text, o.product_url)

                        o.category = detect_category((o.title or "") + " " + (o.text or ""))

                    session.add(o)
            await session.commit()
        except Exception as e:
            print(f"Error verify: {e}")
            await session.rollback()