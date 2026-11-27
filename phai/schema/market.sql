-- Données collectées. Toute valeur porte sa source et sa date de collecte.
CREATE TABLE IF NOT EXISTS collection_runs(
  id INTEGER PRIMARY KEY,
  collector TEXT NOT NULL,
  scope TEXT,
  mode TEXT NOT NULL DEFAULT 'eco',
  started_at TEXT NOT NULL,
  finished_at TEXT,
  status TEXT NOT NULL DEFAULT 'en_cours',   -- en_cours | ok | erreur | ignore
  items INTEGER NOT NULL DEFAULT 0,
  message TEXT
);
CREATE TABLE IF NOT EXISTS sources(
  key TEXT PRIMARY KEY, name TEXT, category TEXT, access_method TEXT, status TEXT,
  needs_key INTEGER, free_quota TEXT, notes TEXT, last_checked TEXT
);
CREATE TABLE IF NOT EXISTS countries(
  code TEXT PRIMARY KEY, name_fr TEXT, currency TEXT, languages TEXT, region TEXT
);
CREATE TABLE IF NOT EXISTS country_indicators(
  country TEXT NOT NULL, indicator TEXT NOT NULL, year INTEGER NOT NULL, value REAL,
  source TEXT NOT NULL, source_url TEXT, collected_at TEXT NOT NULL,
  PRIMARY KEY(country, indicator, year)
);
CREATE TABLE IF NOT EXISTS fx_rates(
  rate_date TEXT NOT NULL, base TEXT NOT NULL, quote TEXT NOT NULL, rate REAL NOT NULL,
  source TEXT NOT NULL, collected_at TEXT NOT NULL,
  PRIMARY KEY(rate_date, base, quote)
);
CREATE TABLE IF NOT EXISTS trend_signals(
  id INTEGER PRIMARY KEY,
  source TEXT NOT NULL, country TEXT NOT NULL, term TEXT NOT NULL,
  approx_traffic TEXT, traffic_min INTEGER, started_at TEXT, url TEXT,
  news_json TEXT, collected_at TEXT NOT NULL, run_id INTEGER,
  UNIQUE(source, country, term, started_at)
);
CREATE TABLE IF NOT EXISTS niches(
  id INTEGER PRIMARY KEY, slug TEXT UNIQUE NOT NULL, name_fr TEXT NOT NULL,
  parent_id INTEGER REFERENCES niches(id), created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS products(
  id INTEGER PRIMARY KEY,
  canonical_name TEXT NOT NULL,
  language TEXT,
  keyword_id INTEGER,
  origin TEXT NOT NULL DEFAULT 'decouverte',   -- decouverte | manuel
  dedup_key TEXT UNIQUE NOT NULL,          -- clé normalisée pour la déduplication
  niche_id INTEGER REFERENCES niches(id),
  description TEXT,
  status TEXT NOT NULL DEFAULT 'candidat',  -- candidat (à approfondir) | en_attente | elimine | preselectionne | finaliste
  status_reason TEXT,
  first_seen TEXT NOT NULL, updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS product_aliases(
  product_id INTEGER NOT NULL REFERENCES products(id), alias TEXT NOT NULL, language TEXT, source TEXT,
  PRIMARY KEY(product_id, alias)
);
CREATE TABLE IF NOT EXISTS evidence(               -- preuves rattachées aux scores
  id INTEGER PRIMARY KEY, product_id INTEGER REFERENCES products(id), country TEXT,
  kind TEXT NOT NULL, source TEXT NOT NULL, url TEXT,
  value_num REAL, value_text TEXT, is_estimate INTEGER NOT NULL DEFAULT 0,
  collected_at TEXT NOT NULL, run_id INTEGER
);
CREATE TABLE IF NOT EXISTS videos(
  id INTEGER PRIMARY KEY, platform TEXT NOT NULL, external_id TEXT NOT NULL, url TEXT NOT NULL,
  title TEXT, channel_id TEXT, channel_title TEXT, published_at TEXT, duration_s INTEGER,
  language TEXT, query TEXT, region TEXT, product_id INTEGER REFERENCES products(id),
  format_hint TEXT,             -- indice de format (YouTube ne signale pas les Shorts dans l'API)
  description TEXT, first_seen TEXT NOT NULL, UNIQUE(platform, external_id)
);
CREATE TABLE IF NOT EXISTS video_stats(            -- relevés bruts ; conservés < 30 jours (règles YouTube)
  video_id INTEGER NOT NULL REFERENCES videos(id) ON DELETE CASCADE, collected_at TEXT NOT NULL,
  views INTEGER, likes INTEGER, comments INTEGER, channel_subscribers INTEGER,
  PRIMARY KEY(video_id, collected_at)
);
CREATE TABLE IF NOT EXISTS suppliers(
  id INTEGER PRIMARY KEY, name TEXT NOT NULL, platform TEXT, url TEXT, ships_from TEXT,
  notes TEXT, first_seen TEXT NOT NULL, UNIQUE(platform, name)
);
CREATE TABLE IF NOT EXISTS supplier_offers(
  id INTEGER PRIMARY KEY, supplier_id INTEGER REFERENCES suppliers(id),
  product_id INTEGER REFERENCES products(id), url TEXT NOT NULL, destination TEXT,
  unit_price REAL, shipping_cost REAL, currency TEXT, delivery_days_min INTEGER,
  delivery_days_max INTEGER, moq INTEGER, rating REAL, orders_count INTEGER,
  source TEXT NOT NULL, collected_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS competitors(
  id INTEGER PRIMARY KEY, product_id INTEGER REFERENCES products(id), shop_name TEXT,
  url TEXT NOT NULL, country TEXT, price REAL, currency TEXT, offer TEXT,
  strengths TEXT, weaknesses TEXT, source TEXT NOT NULL, collected_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS risks(
  id INTEGER PRIMARY KEY, product_id INTEGER REFERENCES products(id), country TEXT,
  kind TEXT NOT NULL, severity TEXT NOT NULL,      -- faible | moyen | majeur
  description TEXT, source TEXT, collected_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS scores(                 -- historisé : une ligne par calcul
  id INTEGER PRIMARY KEY, product_id INTEGER REFERENCES products(id), country TEXT,
  score_type TEXT NOT NULL,                        -- produit | marche | global
  score REAL, confidence TEXT, details_json TEXT, weights_json TEXT, computed_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS reports(
  id INTEGER PRIMARY KEY, kind TEXT NOT NULL, title TEXT, content_md TEXT,
  data_json TEXT, created_at TEXT NOT NULL, mode TEXT
);
CREATE INDEX IF NOT EXISTS idx_trend_country ON trend_signals(country, collected_at);
CREATE INDEX IF NOT EXISTS idx_runs_collector ON collection_runs(collector, finished_at);

-- Moteur de découverte -------------------------------------------------------
CREATE TABLE IF NOT EXISTS keywords(              -- groupes nominaux extraits (données propres)
  id INTEGER PRIMARY KEY,
  dedup_key TEXT UNIQUE NOT NULL,
  term TEXT NOT NULL, language TEXT NOT NULL, niche_slug TEXT,
  status TEXT NOT NULL DEFAULT 'observe',        -- observe | a_rechercher | recherche | produit | rejete
  first_seen TEXT NOT NULL, last_seen TEXT NOT NULL,
  last_searched_at TEXT
);
CREATE TABLE IF NOT EXISTS keyword_signals(       -- où le mot-clé a été observé
  keyword_id INTEGER NOT NULL REFERENCES keywords(id) ON DELETE CASCADE,
  source TEXT NOT NULL,                          -- youtube | google_trends | manuel
  ref TEXT NOT NULL,                             -- id vidéo YouTube, id tendance, id saisie
  country TEXT, observed_at TEXT NOT NULL,
  PRIMARY KEY(keyword_id, source, ref)
);
CREATE TABLE IF NOT EXISTS query_log(
  query TEXT NOT NULL, language TEXT NOT NULL, region TEXT NOT NULL,
  origin TEXT, niche_slug TEXT, last_searched_at TEXT, results INTEGER,
  PRIMARY KEY(query, language, region)
);
CREATE TABLE IF NOT EXISTS api_usage(
  day TEXT NOT NULL, api TEXT NOT NULL, units INTEGER NOT NULL DEFAULT 0,
  PRIMARY KEY(day, api)
);
CREATE TABLE IF NOT EXISTS search_runs(           -- une ligne par recherche (bouton ou planifiée)
  id INTEGER PRIMARY KEY, trigger TEXT, mode TEXT, started_at TEXT NOT NULL, finished_at TEXT,
  status TEXT NOT NULL DEFAULT 'en_cours', sources_json TEXT, new_keywords INTEGER, new_products INTEGER,
  errors_json TEXT
);
CREATE INDEX IF NOT EXISTS idx_signals_source ON keyword_signals(source, ref);
