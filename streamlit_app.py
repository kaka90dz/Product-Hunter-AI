"""Point d'entrée du tableau de bord : streamlit run streamlit_app.py"""
import streamlit as st

from phai import db

st.set_page_config(page_title="Product Hunter AI", page_icon="🔎", layout="wide")
db.init_all()

pages = [
    st.Page("pages/accueil.py", title="Accueil", icon="🏠", default=True),
    st.Page("pages/tendances.py", title="Tendances", icon="📈"),
    st.Page("pages/marches.py", title="Marchés internationaux", icon="🌍"),
    st.Page("pages/sources.py", title="Sources", icon="🔌"),
    st.Page("pages/parametres.py", title="Paramètres", icon="⚙️"),
]
st.navigation(pages).run()
