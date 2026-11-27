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
