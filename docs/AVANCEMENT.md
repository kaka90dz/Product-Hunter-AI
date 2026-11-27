# Avancement

## Étape 1 — Fondations (27/11/2026)

### Fonctionne et testé
- Base SQLite `data/market.db` (schéma complet : tendances, produits, alias de déduplication, preuves,
  vidéos + relevés, fournisseurs, concurrents, risques, scores historisés, rapports) et `data/user.db` (favoris, réglages).
- Collecte réelle : Google Trends RSS (19 pays), taux BCE (Frankfurter), PIB/hab. PPA (Banque mondiale).
- Cache : une collecte récente n'est pas relancée (durées dans `config/settings.yaml`).
- Journal de chaque collecte (statut, nombre d'éléments, erreurs).
- Collecteur YouTube écrit et testé à vide ; collecte réelle dès que la clé est fournie.
- Tableau de bord Streamlit en français : Accueil, Tendances, Marchés, Sources, Paramètres (lecture seule), exports CSV.
- 8 tests automatiques.

### À faire / limites connues
- Mise en ligne Streamlit Community Cloud et clé YouTube : actions de l'utilisateur.
- Les tendances Google RSS concernent surtout l'actualité : filtrage produits à l'étape 2.
- Modification des paramètres et favoris depuis l'interface : étape 6.
