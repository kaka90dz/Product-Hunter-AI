# Product Hunter AI

Recherche internationale de produits e-commerce (dropshipping, marketing organique).

- Besoin complet : [`CAHIER_DES_CHARGES.md`](CAHIER_DES_CHARGES.md)
- Avancement : [`PROGRESS.md`](PROGRESS.md) · Décisions : [`DECISIONS.md`](DECISIONS.md)
- Installation : [`docs/GUIDE_INSTALLATION.md`](docs/GUIDE_INSTALLATION.md)

## Utilisation
- **Tableau de bord** : Streamlit Community Cloud (fichier principal `streamlit_app.py`).
- **Recherche automatique** : GitHub Actions, chaque jour, ou bouton « Trouver de nouveaux produits ».
  Sans IA, donc sans crédits Claude. Données dans la branche `data`.

## Développement
```bash
pip install -r requirements-dev.txt
python -m phai run
streamlit run streamlit_app.py
```
