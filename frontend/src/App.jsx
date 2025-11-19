import { useState, useEffect } from 'react'
import './App.css'

// Componente Scheletro per il caricamento
const SkeletonCard = () => (
  <div className="offer-card">
    <div className="card-image skeleton" style={{height: '180px'}}></div>
    <div className="card-body">
      <div className="skeleton" style={{height: '15px', width: '60px', marginBottom: '10px'}}></div>
      <div className="skeleton" style={{height: '20px', width: '100%', marginBottom: '5px'}}></div>
      <div className="skeleton" style={{height: '20px', width: '80%'}}></div>
      <div style={{marginTop: 'auto', display: 'flex', justifyContent: 'space-between'}}>
        <div className="skeleton" style={{height: '30px', width: '80px'}}></div>
        <div className="skeleton" style={{height: '35px', width: '60px', borderRadius: '6px'}}></div>
      </div>
    </div>
  </div>
)

function App() {
  const [offers, setOffers] = useState([])
  const [categories, setCategories] = useState([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [selectedCat, setSelectedCat] = useState('Tutte')
  const [debounceTimer, setDebounceTimer] = useState(null)

  // 1. Carica le categorie dal backend all'avvio
  useEffect(() => {
    fetch('http://localhost:8000/api/v2/categories')
      .then(res => res.json())
      .then(data => setCategories(data))
      .catch(() => setCategories(["Tutte", "Elettronica", "Altro"])) // Fallback
  }, [])

  // 2. Funzione Fetch Offerte
  const fetchOffers = (cat, searchTerm) => {
    setLoading(true)
    let url = `http://localhost:8000/api/v2/offers?limit=100`

    // Se category ha un'emoji (es. "🍎 Mondo Apple"), dobbiamo encodarla bene
    if (cat && cat !== 'Tutte') url += `&category=${encodeURIComponent(cat)}`
    if (searchTerm) url += `&search=${encodeURIComponent(searchTerm)}`

    fetch(url)
      .then(res => res.json())
      .then(data => {
        // API v2 ritorna {total, limit, offset, offers: [...]}
        setOffers(data.offers || [])
        setLoading(false)
      })
      .catch(() => setLoading(false))
  }

  // 3. Trigger al cambio categoria
  useEffect(() => {
    fetchOffers(selectedCat, search)
  }, [selectedCat])

  // 4. Gestione Ricerca
  const handleSearch = (e) => {
    const val = e.target.value
    setSearch(val)
    if (debounceTimer) clearTimeout(debounceTimer)
    setDebounceTimer(setTimeout(() => fetchOffers(selectedCat, val), 600))
  }

  // Funzione helper "Tempo fa"
  const timeAgo = (dateString) => {
    const diff = Math.floor((new Date() - new Date(dateString)) / 1000);
    if (diff < 60) return 'Adesso';
    if (diff < 3600) return `${Math.floor(diff/60)} min fa`;
    if (diff < 86400) return `${Math.floor(diff/3600)} ore fa`;
    return `${Math.floor(diff/86400)} gg fa`;
  }

  // Track user click (per analytics e recommendation)
  const trackClick = (offerId) => {
    fetch(`http://localhost:8000/api/v2/offers/${offerId}/track`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ event_type: 'click' })
    }).catch(err => console.warn('Track failed:', err))
  }

  return (
    <div className="dashboard">
      {/* SIDEBAR */}
      <aside className="sidebar">
        <div className="logo">⚡ DealsHub Pro</div>
        <nav className="nav-list">
          {categories.map(cat => (
            <button 
              key={cat} 
              className={`nav-item ${selectedCat === cat ? 'active' : ''}`}
              onClick={() => setSelectedCat(cat)}
            >
              {cat}
            </button>
          ))}
        </nav>
      </aside>

      {/* MAIN CONTENT */}
      <main className="main-content">
        <div className="top-bar">
          <h2 style={{margin:0}}>
            {selectedCat === 'Tutte' ? 'Tutte le Offerte' : selectedCat}
          </h2>
          
          <div style={{display: 'flex', gap: '15px'}}>
            <input 
              type="text" 
              className="search-bar"
              placeholder="Cerca offerte..." 
              value={search}
              onChange={handleSearch}
            />
            <button onClick={() => fetchOffers(selectedCat, search)} className="refresh-btn">
              🔄
            </button>
          </div>
        </div>

        <div className="offers-grid">
          {loading ? (
            // Mostra 8 scheletri durante il caricamento
            [...Array(8)].map((_, i) => <SkeletonCard key={i} />)
          ) : offers.length === 0 ? (
            <div style={{gridColumn: '1/-1', textAlign: 'center', padding: '50px', color: '#64748b'}}>
              Nessuna offerta trovata in questa categoria. 🦗
            </div>
          ) : (
            offers.map((offer) => (
              <div key={offer.id} className="offer-card">
                <div className="card-image">
                  {offer.image_url ? (
                    <img src={offer.image_url} alt={offer.title} loading="lazy" />
                  ) : (
                    <div style={{fontSize: '3rem'}}>📦</div>
                  )}
                  
                  {offer.discount > 10 && (
                    <div className="discount-badge">-{offer.discount}%</div>
                  )}
                </div>

                <div className="card-body">
                  <div style={{display:'flex', justifyContent:'space-between'}}>
                    <span className="cat-badge">{offer.category}</span>
                    <span style={{fontSize:'0.75rem', color:'#64748b'}}>{timeAgo(offer.created_at)}</span>
                  </div>

                  <h3 className="card-title" title={offer.title}>
                    {offer.title}
                  </h3>

                  <div className="card-footer">
                    <div className="price-box">
                      {offer.original_price > offer.price && (
                        <span className="old-price">€{offer.original_price}</span>
                      )}
                      <span className="current-price">
                        €{offer.price ? offer.price : '???'}
                      </span>
                    </div>
                    <a
                      href={offer.product_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="btn-buy"
                      onClick={() => trackClick(offer.id)}
                    >
                      Vedi
                    </a>
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
      </main>
    </div>
  )
}

export default App