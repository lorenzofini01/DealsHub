# DealsHub 2.0 - Architecture Documentation

## 🏗️ Overview

DealsHub 2.0 è una **AI-Powered Deal Intelligence Platform** costruita con **Clean Architecture** e **Domain-Driven Design (DDD)**.

Non è più un semplice aggregatore: è un sistema intelligente che:
- ✅ **Anticipa** cosa vuoi prima che tu lo cerchi
- ✅ **Impara** dai tuoi comportamenti
- ✅ **Ti protegge** da fake deals
- ✅ **Scala** a milioni di offerte senza degrado di performance

---

## 📐 Architectural Layers

```
┌─────────────────────────────────────────┐
│   Presentation Layer (FastAPI)          │  ← API Routes, Middleware
├─────────────────────────────────────────┤
│   Application Layer (Use Cases)         │  ← Business Workflows
├─────────────────────────────────────────┤
│   Domain Layer (Entities, Services)     │  ← Core Business Logic
├─────────────────────────────────────────┤
│   Infrastructure Layer (Repos, Cache)   │  ← External Dependencies
└─────────────────────────────────────────┘
```

### 1. **Domain Layer** (`app/domain/`)
**Zero dipendenze esterne.** Cuore del sistema.

- **Entities** (`entities.py`):
  - `Offer`: Rich domain model con comportamenti (not anemic)
  - `UserPreference`: Preferenze utente per personalizzazione
  - `PriceHistory`: Storico prezzi per analytics

- **Value Objects** (`value_objects.py`):
  - `Price`: Type-safe price con validazione
  - `ProductURL`: URL prodotto con normalization
  - `CategoryScore`: Match categoria con confidence

- **Domain Services** (`services.py`):
  - `CategoryDetectionService`: Rilevamento categoria (keyword-based, poi ML)
  - `DuplicateDetectionService`: Deduplica intelligente (ASIN-based)
  - `DealScoringService`: Calcolo Deal Score 0-100
  - `PriceAlertService`: Gestione alert prezzi

- **Interfaces/Ports** (`interfaces.py`):
  - Contratti per infrastructure (Dependency Inversion Principle)
  - `IOfferRepository`, `ICacheService`, `IScraperService`, etc.

### 2. **Application Layer** (`app/application/`)
**Orchestrazione business workflows.**

- **DTOs** (`dtos.py`):
  - Input/Output data structures per API
  - Separati dalle Domain Entities (data marshalling)

- **Use Cases** (`use_cases/`):
  - `IngestOfferUseCase`: Workflow ingestione offerta
  - `SearchOffersUseCase`: Ricerca con caching multi-livello
  - `TrackUserEventUseCase`: Tracking eventi per recommendation
  - `VerifyOffersUseCase`: Verifica batch offerte (scraping)

### 3. **Infrastructure Layer** (`app/infrastructure/`)
**Implementazioni concrete dei servizi.**

- **Persistence** (`persistence/`):
  - `SQLAlchemyOfferRepository`: Implementa `IOfferRepository`
  - `UserPreferenceRepository`, `PriceHistoryRepository`
  - **Indici composti** per query performance:
    - `idx_status_score` → Per ordinamento offerte
    - `idx_category_status` → Per filtri categoria
    - `idx_asin_recorded` → Per price history queries

- **Cache** (`cache/`):
  - `RedisCacheService`: Cache multi-livello
    - L1: In-memory LRU (1000 items) → <1ms latency
    - L2: Redis → <10ms latency
  - Invalidazione intelligente con pattern matching

- **Scraping** (`scraping/`):
  - `HTTPXScraperService`: Async HTTP client
  - Retry logic, timeout optimization
  - Multi-shop support (Amazon, eBay)

### 4. **Presentation Layer** (`app/api_v2/`)
**API REST con security & performance.**

- **Dependency Injection** (`dependencies.py`):
  - Wiring di tutti i componenti
  - Factory patterns per Use Cases
  - Singleton services dove appropriato

- **Middleware** (`middleware.py`):
  - `RateLimitMiddleware`: 120 req/min per IP (in-memory, per prod usare Redis)
  - `PerformanceMiddleware`: Logging slow requests (>500ms)
  - `SecurityHeadersMiddleware`: X-Frame-Options, CSP, etc.

- **Routes** (`routes.py`):
  - `POST /api/v2/offers/ingest`: Ingestione da collector
  - `GET /api/v2/offers`: Ricerca offerte (cache-friendly)
  - `POST /api/v2/offers/{id}/track`: Tracking eventi (view, click, save)
  - `GET /api/v2/categories`: Lista categorie

---

## 🚀 Performance Optimizations

### 1. **Database Indexing**
```sql
-- Indici composti per query comuni
CREATE INDEX idx_status_score ON offers (status, deal_score);
CREATE INDEX idx_status_created ON offers (status, created_at);
CREATE INDEX idx_category_status ON offers (category, status);
```

### 2. **Multi-Level Caching**
```
User Request
    ↓
L1 Cache (in-memory) → HIT? Return (0.1ms)
    ↓ MISS
L2 Cache (Redis) → HIT? Populate L1, Return (5ms)
    ↓ MISS
Database Query → Populate L2, L1, Return (50ms)
```

### 3. **Query Optimization**
- **Limit queries** a top N results (no full table scans)
- **Eager loading** di relazioni con `joinedload()`
- **Async I/O** per parallelizzare DB + cache checks

### 4. **Rate Limiting**
- Protegge da abuse (DDoS, scraping aggressivo)
- 120 req/min per IP (tunable)
- In production: usare Redis-based limiter (distribuito)

---

## 🧠 AI/ML Features (Current & Planned)

### ✅ **Implemented**
1. **Deal Scoring Algorithm**:
   - Discount % (40 punti)
   - Price vs History (30 punti)
   - Sentiment (15 punti) [placeholder]
   - Category popularity (15 punti) [placeholder]

2. **User Tracking**:
   - View count, click-through rate (CTR)
   - Saved offers (watchlist)
   - Preferred categories learned via clicks

### 🔜 **Planned**
1. **ML-based Category Detection**:
   - TF-IDF + SVM classifier
   - Training su dataset storico
   - Accuracy target: >90%

2. **Recommendation Engine**:
   - Collaborative filtering (user-user similarity)
   - Content-based filtering (category/shop affinity)
   - Hybrid approach

3. **Sentiment Analysis**:
   - NLP su testo Telegram
   - Classifica: 😍 Hot Deal, 😐 Average, 😒 Skip

4. **Price Prediction**:
   - LSTM/Prophet per previsione trend prezzi
   - Alert "Compra ora" vs "Aspetta"

---

## 🔐 Security Improvements

### CORS Policy
❌ **OLD**: `allow_origins=["*"]` (CHIUNQUE può chiamare l'API!)
✅ **NEW**: Whitelist esplicita di domini trusted

### Rate Limiting
✅ 120 req/min per IP (configurable)
✅ Protegge da scraping bots e DDoS

### Security Headers
✅ `X-Frame-Options: DENY` → No clickjacking
✅ `X-Content-Type-Options: nosniff` → No MIME sniffing
✅ `Strict-Transport-Security` → Force HTTPS

---

## 📊 Monitoring & Observability

### Custom Metrics
- **Response Time**: Header `X-Process-Time` su ogni response
- **Slow Request Logging**: Alert se >500ms
- **Cache Hit Rate**: L1 vs L2 vs DB

### Future Integrations
- **Prometheus**: Metrics export per Grafana
- **Sentry**: Error tracking & alerting
- **OpenTelemetry**: Distributed tracing

---

## 🔄 Migration Path (Old → New)

### Backward Compatibility
- Old endpoints (`/api/offers/active`) → still work via old `main.py`
- New endpoints (`/api/v2/offers`) → use clean architecture

### Migration Steps
1. ✅ Deploy new code (both old & new APIs running)
2. ⏳ Migrate frontend to call `/api/v2/*`
3. ⏳ Deprecate old endpoints (add warning)
4. ⏳ Remove old code after 2 weeks

---

## 🧪 Testing Strategy

### Unit Tests
- Domain Services (pure business logic)
- Use Cases (mock repositories)

### Integration Tests
- API endpoints (with test DB)
- Repository implementations (SQLAlchemy)

### E2E Tests
- Full workflow: Ingest → Verify → Search
- Cache invalidation scenarios

---

## 📦 Deployment

### Docker Compose Services
```yaml
services:
  backend:    # FastAPI (new API v2)
  worker:     # Celery worker (scraping)
  beat:       # Celery beat (scheduler)
  redis:      # Cache + Task queue
  postgres:   # Database
  collector:  # Telegram scraper
  frontend:   # React UI
```

### Environment Variables
```env
DATABASE_URL=postgresql+asyncpg://user:pass@postgres/db
REDIS_URL=redis://redis:6379/0
SECRET_KEY=your-secret-key
```

---

## 🚀 Future Roadmap

### Phase 2 (Next 2 weeks)
- [ ] ML-based category detection (TF-IDF + SVM)
- [ ] Recommendation engine (collaborative filtering)
- [ ] WebSocket real-time updates (new deals push)

### Phase 3 (Next month)
- [ ] Sentiment analysis (NLP on Telegram text)
- [ ] Price prediction (LSTM)
- [ ] Advanced analytics dashboard

### Phase 4 (Long-term)
- [ ] Mobile app (React Native)
- [ ] AR product preview (WebXR)
- [ ] Voice search (Whisper API)
- [ ] Multi-language support

---

## 📚 Code Examples

### Using the new API
```python
# Ingest offer (from Telegram collector)
POST /api/v2/offers/ingest
{
  "source": "telegram",
  "chat_id": "123456",
  "message_id": 789,
  "text": "Super offerta iPhone 15 Pro!",
  "url": "https://amazon.it/dp/B0CHXABCD"
}

# Search offers (with caching)
GET /api/v2/offers?category=📱 Smartphone&min_score=70&limit=20

# Track user click (for recommendation)
POST /api/v2/offers/42/track
{
  "event_type": "click"
}
```

---

## 🏆 What Makes This Architecture Special

1. **Testability**: Domain logic è testabile senza DB/Redis/HTTP
2. **Maintainability**: Cambi a DB/cache NON toccano business logic
3. **Scalability**: Aggiungi cache layers, read replicas senza refactor
4. **Evolvability**: Aggiungi ML/AI senza riscrivere tutto
5. **Team Velocity**: Frontend/Backend team lavorano in parallelo

---

**Welcome to DealsHub 2.0. The future of deal aggregation is here.** 🚀
