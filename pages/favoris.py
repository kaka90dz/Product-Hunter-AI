import streamlit as st

from phai import app_data, queries

st.title("⭐ Favoris")
LISTES = {"favori": "⭐ Favoris", "a_tester": "🧪 À tester", "elimine": "🗑️ Éliminés", "marche_favori": "🌍 Marchés favoris"}
f = queries.favorites()
if f.empty:
    st.info("Aucun élément. Ajoutez des produits depuis leur fiche (page Produits).")
    st.stop()
for key, label in LISTES.items():
    sub = f[f["liste"] == key]
    if sub.empty:
        continue
    st.subheader(f"{label} ({len(sub)})")
    for _, r in sub.iterrows():
        c1, c2 = st.columns([5, 1])
        c1.markdown(f"**{r['produit']}**" + (f" — {r['pays']}" if r["pays"] else "") + (f"  \n{r['note']}" if r["note"] else ""))
        if c2.button("Retirer", key=f"del{r['id']}"):
            try:
                app_data.write_user(lambda con, i=int(r["id"]): con.execute("DELETE FROM favorites WHERE id=?", (i,)))
                st.rerun()
            except Exception as e:  # noqa: BLE001
                st.error(str(e))
st.download_button("Exporter en CSV", f.to_csv(index=False).encode("utf-8"), "favoris.csv", "text/csv")
