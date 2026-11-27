import streamlit as st

from phai import config, queries

st.title("📈 Tendances")
st.caption("Recherches Google en forte hausse, par pays (source : flux RSS public Google Trends). Surtout de "
           "l'actualité : utilisées seulement pour confirmer des produits déjà repérés ailleurs.")

countries = {c["code"]: c["name_fr"] for c in config.countries()}
col1, col2 = st.columns([2, 1])
choice = col1.selectbox("Pays", ["Tous"] + list(countries), format_func=lambda k: "Tous les pays" if k == "Tous" else f"{countries[k]} ({k})")
days = col2.selectbox("Période de collecte", [1, 7, 30, 90], index=1, format_func=lambda d: f"{d} derniers jours")

df = queries.trends(None if choice == "Tous" else choice, days)
if df.empty:
    st.warning("Aucune donnée pour ce filtre.")
else:
    st.write(f"**{len(df)}** recherches")
    st.dataframe(
        df.drop(columns=["traffic_min"]), hide_index=True, use_container_width=True,
        column_config={
            "pays": "Code", "nom_pays": "Pays", "recherche": "Recherche", "trafic": "Trafic estimé",
            "debut": "Début de la hausse", "collecte_le": "Collecté le (UTC)",
            "url": st.column_config.LinkColumn("Google Trends", display_text="Ouvrir"),
            "article": st.column_config.LinkColumn("Article lié", display_text="Lire"),
        },
    )
    st.download_button("Exporter en CSV", df.to_csv(index=False).encode("utf-8"),
                       file_name="tendances.csv", mime="text/csv")
