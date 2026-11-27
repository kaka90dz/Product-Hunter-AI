# Décisions techniques et limitations

**D1 — Architecture (27/11/2026).** Python + SQLite + GitHub Actions + Streamlit Community Cloud. Coût : 0 €.
Le serveur Claude Code n'héberge rien (éphémère).

**D2 — Stockage.** Deux bases SQLite dans une branche `data` du dépôt privé, séparée du code :
`market.db` (écrite uniquement par GitHub Actions) et `user.db` (écrite uniquement par le tableau de bord).
Un seul écrivain par fichier ⇒ pas de conflit. Écritures simultanées : `concurrency: data-write` côté Actions,
contrôle de version (sha) côté tableau de bord, avec un nouvel essai.
Croissance : historique de la branche `data` compacté chaque semaine (un seul commit), après sauvegarde.
Sauvegardes : release GitHub privée hebdomadaire (8 conservées) + test de restauration automatique (`phai verify`).
Migration possible : tout l'accès passe par `phai/db.py` et `phai/app_data.py` ; remplacer SQLite par une base
distante (PostgreSQL, libSQL/Turso) ne toucherait que ces modules. À envisager si `market.db` dépasse ~50 Mo.

**D3 — Découverte de produits sans nom fourni.** Source principale : recherche YouTube (API officielle) sur des
requêtes à intention d'achat en 9 langues × régions, et par niche. Les noms de produits sont extraits des titres
par règles linguistiques (aucune IA). Un produit candidat est créé quand le même groupe nominal est observé chez
≥ 2 créateurs différents. Les produits découverts deviennent à leur tour des requêtes (« boule de neige ») :
la base s'enrichit d'elle-même. Google Trends RSS (surtout de l'actualité) ne crée jamais un produit seul.

**D4 — Règles YouTube** (Developer Policies, sections III.E.4, lues le 27/11/2026).
Données de l'API supprimées ou rafraîchies sous 30 jours (`retention_days.youtube_api_data: 29`).
Pas d'indicateurs dérivés calculés à partir des statistiques YouTube (vues/jour, vues/abonnés, croissance) :
les statistiques sont affichées brutes, avec leur source. Le score n'utilise que le nombre de créateurs et de
régions de recherche où un produit apparaît (interprétation prudente ; à revoir si Google précise ce point).
L'API ne signale pas les Shorts : on affiche un indice de format (durée, #shorts), jamais une certitude.
Aucun accès aux pages youtube.com en dehors de l'API. La région de recherche ≠ pays de l'audience.

**D5 — TikTok / Instagram.** Pas d'accès gratuit automatisé et conforme aux statistiques (Research API réservée aux
chercheurs académiques ; oEmbed TikTok ne renvoie plus titre ni auteur ; Instagram Graph exige compte pro + app
validée ; Trendtrack payant). ⇒ Saisie manuelle assistée. Les indicateurs (vues/jour, vues/abonnés) ne sont
calculés que sur ces saisies et marqués « estimation ».

**D6 — Scores.** Score produit partiel : une composante sans preuve vaut 0 et est affichée « manquante » ;
on affiche « points / points évaluables ». Confiance « Élevée » impossible tant que fournisseurs et rentabilité
ne sont pas vérifiés. Statut par défaut : « candidat à approfondir », jamais « gagnant ».

**D7 — Budget 0 €.** Pas d'API IA. Quotas : YouTube ≤ 3 000 unités/recherche et ≤ 8 000/jour (gratuit : 10 000).
GitHub Actions : 1 recherche/jour + boutons, 15 min max par exécution, maintenance 10 min/semaine
(≈ 150 à 300 min/mois sur 2 000 gratuites). Délais entre requêtes et cache par source.

**D8 — Données personnelles.** Aucune donnée personnelle (pays de résidence, statut) dans le dépôt.
Elles seront demandées au moment des calculs fiscaux et gardées hors de Git.

## Limitations connues
- Extraction par règles : du bruit possible (ex. « hunger games » vient des tendances) ; seuil de 2 créateurs.
- Un même produit dans deux langues = deux fiches tant qu'il n'est pas fusionné.
- Les serveurs de GitHub peuvent être bloqués par certaines sources (constaté depuis Claude : Reddit, TikTok,
  Amazon, Etsy, Trustpilot).
- Le proxy de la session Claude interdit l'écriture par l'API GitHub : les écritures du tableau de bord
  se vérifient une fois celui-ci en ligne avec le jeton de l'utilisateur.
