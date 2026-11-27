import streamlit as st

from phai import queries

st.title("🔌 Sources de données")
st.caption("État réel de chaque source, vérifié depuis le serveur. Aucune protection n'est contournée.")
labels = {"actif": "✅ Actif", "a_configurer": "🔑 À configurer", "manuel": "✋ Manuel",
          "bloque": "⛔ Bloqué", "exclu": "🚫 Exclu"}
df = queries.sources()
df["statut"] = df["statut"].map(lambda s: labels.get(s, s))
df["cle_requise"] = df["cle_requise"].map({1: "Oui", 0: "Non"})
st.dataframe(df, hide_index=True, use_container_width=True,
             column_config={"source": "Source", "categorie": "Catégorie", "statut": "Statut", "acces": "Accès",
                            "cle_requise": "Clé", "quota": "Quota gratuit", "notes": "Notes",
                            "verifie_le": "Vérifié le"})

st.subheader("Quota YouTube aujourd'hui")
used = queries.youtube_units_today()
from phai import config
cap = config.settings()["discovery"]["youtube_units_per_day"]
st.progress(min(used / cap, 1.0), text=f"{used} / {cap} unités (plafond fixé sous le quota gratuit de 10 000)")
