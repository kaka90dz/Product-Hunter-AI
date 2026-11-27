import streamlit as st

from phai import queries

st.title("🔎 Product Hunter AI")
st.caption("Recherche internationale de produits e-commerce — version 0.1 (étape 1 : fondations)")

c = queries.counts()
last = queries.last_collect_time()
cols = st.columns(4)
cols[0].metric("Tendances collectées", c["tendances"])
cols[1].metric("Pays couverts", c["pays_tendances"])
cols[2].metric("Vidéos analysées", c["videos"])
cols[3].metric("Produits analysés", c["produits"])
st.caption(f"Dernière collecte réussie : {last or 'aucune'} (UTC)")

st.info(
    "**Ce qui fonctionne aujourd'hui** : collecte automatique des recherches en hausse "
    "(Google Trends, 19 pays), taux de change BCE, pouvoir d'achat (Banque mondiale).  \n"
    "**Pas encore disponible** : détection de produits, scores, fournisseurs, favoris — prévus aux étapes suivantes. "
    "Aucune donnée fictive n'est affichée.",
    icon="ℹ️",
)

st.subheader("Tendances présentes dans plusieurs pays (7 derniers jours)")
mc = queries.multi_country_terms(7)
if mc.empty:
    st.write("Aucune recherche commune à plusieurs pays pour le moment.")
else:
    st.dataframe(mc.head(20), hide_index=True, use_container_width=True,
                 column_config={"recherche": "Recherche", "nb_pays": "Nb pays", "pays": "Pays",
                                "trafic_max": st.column_config.NumberColumn("Trafic max (≥)", format="%d")})
st.caption("Source : Google Trends, flux RSS « Recherches en hausse ». Le trafic est une estimation minimale "
           "fournie par Google, pas un volume exact. Ces tendances concernent surtout l'actualité : le filtrage "
           "orienté produits arrive à l'étape 2.")

st.subheader("Journal des collectes")
st.dataframe(queries.last_runs(15), hide_index=True, use_container_width=True)
