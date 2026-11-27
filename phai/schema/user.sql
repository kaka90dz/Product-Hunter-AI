-- Données personnelles de l'utilisateur (écrites par le tableau de bord).
CREATE TABLE IF NOT EXISTS favorites(
  id INTEGER PRIMARY KEY,
  product_id INTEGER, product_name TEXT NOT NULL, country TEXT,
  list_name TEXT NOT NULL CHECK(list_name IN ('favori','a_tester','elimine','marche_favori')),
  note TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS settings(
  key TEXT PRIMARY KEY, value_json TEXT NOT NULL, updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS manual_videos(        -- saisie manuelle assistée (TikTok, Instagram, autres)
  id INTEGER PRIMARY KEY, url TEXT UNIQUE NOT NULL, platform TEXT NOT NULL,
  title TEXT, author TEXT, product_name TEXT NOT NULL, language TEXT, audience_country TEXT,
  published_at TEXT, observed_at TEXT NOT NULL,
  views INTEGER, likes INTEGER, comments INTEGER, shares INTEGER, account_followers INTEGER,
  duration_s INTEGER, hook TEXT, is_ad TEXT NOT NULL DEFAULT 'inconnu',   -- oui | non | inconnu
  notes TEXT, created_at TEXT NOT NULL
);
