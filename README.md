# Product Hunter AI

Recherche internationale de produits e-commerce (dropshipping, marketing organique).

- Besoin complet : [`CAHIER_DES_CHARGES.md`](CAHIER_DES_CHARGES.md)
- Avancement : [`docs/AVANCEMENT.md`](docs/AVANCEMENT.md)

## Utilisation
- **Tableau de bord** : Streamlit Community Cloud (fichier principal `streamlit_app.py`).
- **Collecte automatique** : GitHub Actions, chaque jour (onglet *Actions* → *Collecte quotidienne* → *Run workflow*
  pour la lancer à la main). Sans IA, donc sans crédits Claude.

## Développement
```bash
pip install -r requirements-dev.txt
python -m phai collect
streamlit run streamlit_app.py
```
