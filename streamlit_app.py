"""Point d'entrée du tableau de bord : streamlit run streamlit_app.py"""
import streamlit as st

from phai import app_data

st.set_page_config(page_title="Product Hunter AI", page_icon="🔎", layout="wide")
st.markdown("""<style>
[data-testid="stMetricValue"]{font-size:1.8rem}
.block-container{padding-top:2rem;max-width:1300px}
@media (max-width:640px){.block-container{padding-left:.8rem;padding-right:.8rem}}
</style>""", unsafe_allow_html=True)

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
