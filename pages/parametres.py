import streamlit as st

from phai import config

st.title("⚙️ Paramètres")
st.info("Lecture seule pour l'instant. La modification depuis l'interface (enregistrée durablement) "
        "arrive à l'étape 6. Valeurs actuelles :", icon="ℹ️")
s = config.settings()
c1, c2 = st.columns(2)
with c1:
    st.subheader("Mode et budget")
    st.write(f"Mode de recherche : **{s['mode'].capitalize()}**")
    st.write(f"Budget de lancement maximal : **{s['budget']['total_eur_max']} €**")
    f = s["financial"]
    st.subheader("Critères financiers")
    st.write(f"Coût fournisseur livré : {f['supplier_cost_eur']['min']}–{f['supplier_cost_eur']['max']} €")
    st.write(f"Prix de vente : {f['sale_price_eur']['min']}–{f['sale_price_eur']['max']} €")
    st.write(f"Marge produit minimale : {f['min_product_margin_pct']} %")
    st.write(f"Échantillon max : {f['max_sample_cost_eur']} € — Livraison max : {f['max_delivery_days']} jours")
with c2:
    st.subheader("Pondérations — score produit")
    st.table({k: [v] for k, v in s["weights_product"].items()})
    st.subheader("Pondérations — score marché")
    st.table({k: [v] for k, v in s["weights_market"].items()})
st.subheader("Pays exclus")
st.write(", ".join(s["countries_excluded"]) or "Aucun")
