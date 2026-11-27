"""Point d'entrée du tableau de bord : streamlit run streamlit_app.py"""
import importlib
import os
import sys

import streamlit as st

# Après une mise à jour du code sur GitHub, Streamlit Cloud relance cette page sans toujours
# recharger les modules déjà importés : on recharge ceux dont le fichier a changé.
_loaded = st.session_state.setdefault("_module_mtimes", {})
for _name in sorted(n for n in list(sys.modules) if n == "phai" or n.startswith("phai.")):
    _mod = sys.modules[_name]
    _file = getattr(_mod, "__file__", None)
    if _file and os.path.exists(_file):
        _mt = os.path.getmtime(_file)
        if _name in _loaded and _loaded[_name] != _mt:
            importlib.reload(_mod)
        _loaded[_name] = _mt

from phai import app_data

st.set_page_config(page_title="Product Hunter AI", page_icon="🔎", layout="wide")
st.markdown("""<style>
[data-testid="stMetricValue"]{font-size:1.8rem}
.block-container{padding-top:2rem;max-width:1300px}
@media (max-width:640px){.block-container{padding-left:.8rem;padding-right:.8rem}}
</style>""", unsafe_allow_html=True)

if not app_data.hosted() and app_data.on_streamlit_cloud():
    names = app_data.secret_names()
    st.error("**Jeton GitHub introuvable** : le tableau de bord ne peut ni lire vos données ni lancer de recherche.  \n"
             "Secrets détectés (noms uniquement) : " + (", ".join(names) if names else "aucun") + ".  \n"
             "Dans **Manage app → ⋮ → Settings → Secrets**, collez exactement le modèle du guide "
             "(section `[github]` avec `token = \"…\"`), puis **Save**.")
try:
    app_data.sync()
except Exception as e:  # noqa: BLE001
    st.error(f"Impossible de charger les données depuis GitHub : {e}")
    st.stop()

pages = [
    st.Page("pages/accueil.py", title="Accueil", icon="🏠", default=True),
    st.Page("pages/produits.py", title="Produits", icon="🛍️"),
    st.Page("pages/videos.py", title="Vidéos", icon="🎬"),
    st.Page("pages/tendances.py", title="Tendances", icon="📈"),
    st.Page("pages/marches.py", title="Marchés", icon="🌍"),
    st.Page("pages/favoris.py", title="Favoris", icon="⭐"),
    st.Page("pages/sources.py", title="Sources", icon="🔌"),
    st.Page("pages/parametres.py", title="Paramètres", icon="⚙️"),
]
with st.sidebar:
    st.caption("Mode : **Eco** (aucune IA)")
    if not app_data.hosted():
        st.caption("⚠️ Mode local : les modifications ne sont pas enregistrées dans GitHub.")
st.navigation(pages).run()
