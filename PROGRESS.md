# PROGRESS — Product Hunter AI

> À lire en début de session pour ne pas refaire le travail. Mettre à jour à chaque étape.

## État au 27/11/2026 — version 0.2 (première version minimale)

### Fonctionne et testé
| Élément | Test |
|---|---|
| Collecte Google Trends RSS (19 pays), taux BCE, PIB/hab. PPA | Réel, sur GitHub Actions (27/11) |
| Moteur de découverte YouTube (requêtes multilingues, niches, boule de neige, quota plafonné) | **Réel sur GitHub Actions (27/11)** : 58 recherches, 939 vidéos, ~530 mots-clés, 31 produits candidats découverts sans nom fourni |
| Extraction de noms de produits (9 langues, règles sans IA) | Tests unitaires |
| Filtres de risque (éliminatoires / en attente) | Tests unitaires |
| Création de produits candidats (≥ 2 créateurs, ou YouTube + Trends, ou saisie manuelle) | Tests |
| Score produit partiel justifié (composantes manquantes = 0 point, affichées comme manquantes) | Tests |
| Saisie manuelle TikTok/Instagram (vues/jour et vues/abonnés calculés) | Test + interface locale |
| Branche `data` (bases séparées du code), lecture via API GitHub | Réel |
| Écriture du tableau de bord dans GitHub (favoris, saisies) | Code testé localement ; **réel : en attente du jeton** |
| Bouton « Trouver de nouveaux produits » (déclenchement + suivi + anti-doublon) | **En attente du jeton** |
| Sauvegarde hebdomadaire + test de restauration + compactage | Workflow écrit ; premier essai réel : voir ci-dessous |
| Tableau de bord 8 pages (PC + mobile), exports CSV | Captures d'écran, 0 erreur |

### Reste à faire (prochaines étapes)
- Étape 3 : scores marchés par produit, prix locaux, simulateur financier.
- Étape 4 : concepts de vidéos (Claude, mode Standard), analyse des accroches.
- Étape 5 : fournisseurs (CJdropshipping API, AliExpress Affiliés), concurrents, rentabilité.
- Étape 6 : paramètres modifiables depuis l'interface, rapports quotidiens/hebdomadaires.
- Étape 7 : commandes Claude (/hunt, /validate-product…), modes Standard et Deep.
- Fusion des produits identiques entre langues (alias) : manuel ou Claude (mode Standard).

### Premiers produits découverts (27/11/2026, 2 recherches, confiance faible)
full-body / bubble umbrella, electric water dispenser, medicine dispenser, electric hot water bag, steering cover,
infuser basket, cane earrings, 2-in-1 cordless electric broom, phone holder, spout pouch… Bruit restant : termes
génériques (kitchen tools, water pump, dc fans) et matériel lourd (smith machine, power rack) — filtrés plus tard
par les critères fournisseurs/logistique (étape 5).

### Analyses déjà faites (ne pas refaire)
- Audit des sources (25 et 27/11/2026) : voir `config/sources.yaml`.
- Règles YouTube (27/11/2026) : voir `DECISIONS.md` D4.
- Trendtrack (27/11/2026) : API/MCP payants → exclu.
