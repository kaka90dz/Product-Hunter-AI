import streamlit as st

from phai import queries

st.title("🌍 Marchés internationaux")
st.caption("Données de base par pays. Les scores de marché par produit arrivent à l'étape 3.")

df = queries.markets()
st.dataframe(
    df, hide_index=True, use_container_width=True,
    column_config={
        "code": "Code", "pays": "Pays", "region": "Région", "langues": "Langues", "devise": "Devise",
        "taux_eur": st.column_config.NumberColumn("1 € =", format="%.4f"),
        "date_taux": "Date du taux (BCE)",
        "pib_hab_ppa_usd": st.column_config.NumberColumn("PIB/hab. PPA ($ int.)", format="%.0f"),
        "annee_pib": "Année PIB",
    },
)
st.caption("Sources : taux de référence BCE via api.frankfurter.dev ; Banque mondiale, indicateur "
           "NY.GDP.PCAP.PP.CD. La zone euro n'a pas de taux (1 € = 1 €).")
st.download_button("Exporter en CSV", df.to_csv(index=False).encode("utf-8"), file_name="marches.csv", mime="text/csv")
