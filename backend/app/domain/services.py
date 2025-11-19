"""
Domain Services - Business Logic complessa che non appartiene a una singola Entity
"""
from typing import List, Optional
from .entities import Offer, DealQuality
from .value_objects import CategoryScore
import re


class CategoryDetectionService:
    """
    Service per detection intelligente delle categorie.
    Versione base con keyword matching, poi sostituiremo con ML.
    """

    CATEGORIES = {
        "🎮 Gaming": ["ps5", "xbox", "switch", "nintendo", "playstation", "console", "videogioco", "game"],
        "⌚ Smartwatch": ["apple watch", "garmin", "amazfit", "smartwatch", "orologio", "band", "fitbit"],
        "🍎 Food & Drink": ["mentos", "caramelle", "cioccolato", "caffè", "capsule", "vino", "birra", "snack"],
        "💄 Beauty": ["profumo", "crema", "shampoo", "bagnoschiuma", "dentifricio", "rasoio", "trucco"],
        "📱 Smartphone": ["iphone", "samsung galaxy", "xiaomi", "redmi", "pixel", "smartphone", "cellulare"],
        "🎧 Audio": ["cuffie", "auricolari", "airpods", "buds", "sony", "bose", "jbl", "soundbar"],
        "💻 Tech": ["notebook", "laptop", "macbook", "pc", "monitor", "tastiera", "mouse", "ipad", "tablet"],
        "🔧 DIY": ["trapano", "avvitatore", "makita", "bosch", "attrezzi", "led", "smart home"],
        "🏠 Home": ["friggitrice", "aspirapolvere", "robot", "roomba", "padella", "materasso", "arredo"],
        "👟 Fashion": ["scarpe", "sneakers", "t-shirt", "felpa", "nike", "adidas", "zaino", "borsa"],
        "🏋️ Sport": ["palestra", "fitness", "pesi", "manubri", "bici", "tenda", "campeggio"],
    }

    def detect(self, text: str, title: Optional[str] = None) -> CategoryScore:
        """
        Rileva la categoria con confidence score.
        Combina testo messaggio + titolo prodotto.
        """
        combined_text = f"{text or ''} {title or ''}".lower()

        best_match = ("📦 Altro", 0.0)

        for category, keywords in self.CATEGORIES.items():
            matches = sum(1 for kw in keywords if kw in combined_text)
            if matches > 0:
                # Confidence basata su numero di keyword matchate
                confidence = min(matches / 3.0, 1.0)  # Max 3 keywords per full confidence
                if confidence > best_match[1]:
                    best_match = (category, confidence)

        return CategoryScore(category_name=best_match[0], confidence=best_match[1])


class DuplicateDetectionService:
    """
    Service per rilevare duplicati intelligentemente.
    Usa ASIN per Amazon, URL normalization per altri shop.
    """

    @staticmethod
    def extract_asin(url: str) -> Optional[str]:
        """Estrae ASIN da URL Amazon"""
        match = re.search(r'/(?:dp|gp/product)/([A-Z0-9]{10})', url)
        return match.group(1) if match else None

    @staticmethod
    def normalize_url(url: str) -> str:
        """Normalizza URL per confronto"""
        # Rimuovi query params e trailing slashes
        clean = url.split('?')[0].rstrip('/')

        # Per Amazon, usa solo ASIN
        asin = DuplicateDetectionService.extract_asin(url)
        if asin:
            return f"amazon:{asin}"

        return clean.lower()

    @staticmethod
    def are_duplicates(url1: str, url2: str) -> bool:
        """Confronta due URL per capire se sono duplicati"""
        return DuplicateDetectionService.normalize_url(url1) == \
               DuplicateDetectionService.normalize_url(url2)


class DealScoringService:
    """
    Service avanzato per scoring delle offerte.
    Considera molteplici fattori oltre al semplice sconto.
    """

    @staticmethod
    def calculate_base_score(offer: Offer) -> int:
        """Score di base 0-100 basato solo sui dati dell'offerta stessa"""
        score = 0

        # 1. Discount weight (50 punti max)
        if offer.discount_percentage > 0:
            # Curve non lineare: sconti alti valgono di più
            discount_score = min(offer.discount_percentage * 0.8, 50)
            score += discount_score

        # 2. Price reasonability (20 punti max)
        if offer.price:
            # Penalizza prezzi troppo bassi (probabilmente errori) o troppo alti
            price_val = float(offer.price)
            if 5 <= price_val <= 500:
                score += 20
            elif 1 <= price_val < 5 or 500 < price_val <= 2000:
                score += 10

        # 3. Completeness bonus (15 punti max)
        completeness = 0
        if offer.title and len(offer.title) > 10:
            completeness += 5
        if offer.image_url:
            completeness += 5
        if offer.category and offer.category != "📦 Altro":
            completeness += 5
        score += completeness

        # 4. Freshness bonus (15 punti max)
        from datetime import datetime, timedelta
        age = datetime.now() - offer.created_at
        if age < timedelta(hours=1):
            score += 15
        elif age < timedelta(hours=6):
            score += 10
        elif age < timedelta(hours=24):
            score += 5

        return min(int(score), 100)

    @staticmethod
    def adjust_for_engagement(base_score: int, offer: Offer) -> int:
        """Aggiusta score basato su engagement utenti"""
        adjusted = base_score

        # CTR Boost: se la gente clicca, è un buon deal
        ctr = offer.get_ctr()
        if ctr > 10:
            adjusted += 10
        elif ctr > 5:
            adjusted += 5

        # Save Boost: se molti salvano, è interessante
        if offer.save_count > 20:
            adjusted += 10
        elif offer.save_count > 10:
            adjusted += 5

        return min(adjusted, 100)


class PriceAlertService:
    """
    Service per gestire gli alert di prezzo.
    Controlla se un'offerta trigghera alert per qualche utente.
    """

    @staticmethod
    def should_trigger_alert(offer: Offer, target_price: float) -> bool:
        """Ritorna True se il prezzo è sotto la soglia target"""
        if not offer.price:
            return False
        return float(offer.price) <= target_price

    @staticmethod
    def calculate_deal_urgency(offer: Offer) -> str:
        """Calcola l'urgenza di un deal per prioritizzare notifiche"""
        if offer.deal_score >= 80:
            return "CRITICAL"  # Invia subito
        elif offer.deal_score >= 60:
            return "HIGH"      # Invia entro 5 minuti
        elif offer.deal_score >= 40:
            return "MEDIUM"    # Invia entro 30 minuti
        else:
            return "LOW"       # Batch giornaliero
