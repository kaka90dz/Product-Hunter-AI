# Audit de l'environnement — 25/11/2026

## Environnement
- Cloud Claude Code (conteneur Ubuntu 24.04 éphémère), environnement « Kais », réseau illimité, 4 CPU, 15 Go RAM.
- Python 3.13.18, pip 24.0, Node.js 22.23.5, npm 10.9.9, Git 2.43.0, gh 2.89.0.
- Playwright 1.63 + Chromium préinstallés. Bibliothèques Python : requests, beautifulsoup4, pandas.

## Playwright MCP
- `@playwright/mcp@0.0.85` installé dans le projet (version figée), déclaré dans `.mcp.json`.
- Testé : le serveur démarre et expose 25 outils (navigation, clic, capture, snapshot…).
- Activation : chargé au démarrage d'une session ouverte sur ce dépôt (approbation demandée une fois).

## Accès aux sources (testés depuis le conteneur)
| Source | Résultat | Voie conforme recommandée |
|---|---|---|
| Google Trends — tendances du jour (page + RSS) | OK | RSS `trends.google.com/trending/rss?geo=XX` |
| Google Trends — Explore (comparaison mots-clés) | 429 Too Many Requests | Limiter fortement les appels ; API officielle Google Trends (accès sur demande) |
| YouTube (pages, flux RSS des chaînes) | OK | YouTube Data API v3 (clé gratuite, quota 10 000 unités/jour) |
| TikTok Creative Center | 403 bloqué | Consultation manuelle, ou connecteur Trendtrack (connexion à terminer) |
| Reddit (www et old) | 403 « blocked by network security » | API officielle Reddit avec application OAuth gratuite (usage non commercial) |
| AliExpress (recherche) | OK (page rendue, prix, ventes) | Navigation modérée ; programme affilié AliExpress (API officielle gratuite) |

## Persistance
- Le conteneur est effacé après inactivité : seul ce qui est poussé sur GitHub est conservé.
- Le dépôt GitHub n'a pas pu être créé automatiquement (403 de l'intégration) : à créer manuellement.
