from datetime import date

import streamlit as st

from phai import app_data, config, db, oembed, queries

st.title("🎬 Vidéos")
tab1, tab2 = st.tabs(["Ajouter une vidéo (TikTok, Instagram…)", "Vidéos YouTube trouvées"])

with tab1:
    st.caption("TikTok et Instagram ne proposent pas d'accès gratuit à ces statistiques : vous les relevez sur la vidéo, "
               "le logiciel fait les calculs. Ces données sont marquées « saisie manuelle ».")
    url = st.text_input("Adresse de la vidéo", placeholder="https://www.tiktok.com/@compte/video/…")
    pre = oembed.fetch(url) if url else {}
    if url:
        st.caption(f"Plateforme détectée : **{oembed.platform_of(url)}**")
    known = sorted(queries.products()["produit"].tolist()) if not queries.products().empty else []
    with st.form("manual", clear_on_submit=True):
        c1, c2 = st.columns(2)
        prod_sel = c1.selectbox("Produit associé", ["➕ Nouveau produit…"] + known)
        prod_new = c2.text_input("Nom du nouveau produit (si nouveau)")
        c1, c2, c3 = st.columns(3)
        title = c1.text_input("Titre / description", value=pre.get("title") or "")
        author = c2.text_input("Compte", value=pre.get("author") or "")
        lang = c3.selectbox("Langue de la vidéo", ["en", "fr", "de", "es", "it", "nl", "pt", "pl", "sv"])
        c1, c2, c3, c4 = st.columns(4)
        views = c1.number_input("Vues", min_value=0, step=1000, value=None)
        likes = c2.number_input("Likes", min_value=0, step=100, value=None)
        comments = c3.number_input("Commentaires", min_value=0, step=10, value=None)
        shares = c4.number_input("Partages", min_value=0, step=10, value=None)
        c1, c2, c3 = st.columns(3)
        followers = c1.number_input("Abonnés du compte", min_value=0, step=1000, value=None)
        published = c2.date_input("Date de publication", value=None, format="DD/MM/YYYY")
        duration = c3.number_input("Durée (secondes)", min_value=0, step=1, value=None)
        c1, c2 = st.columns(2)
        is_ad = c1.radio("Publicité ?", ["inconnu", "oui", "non"], horizontal=True,
                         help="« non » seulement si c'est vérifiable (pas de mention Sponsorisé / Partenariat).")
        audience = c2.selectbox("Pays de l'audience (si réellement connu)", ["inconnu"] + [c["code"] for c in config.countries()])
        hook = st.text_input("Accroche (premières secondes)")
        notes = st.text_area("Notes")
        if st.form_submit_button("Enregistrer la vidéo", type="primary"):
            name = (prod_new.strip() if prod_sel.startswith("➕") else prod_sel).strip()
            if not url or not name:
                st.error("L'adresse et le produit sont obligatoires.")
            else:
                def add(con):
                    con.execute(
                        "INSERT INTO manual_videos(url, platform, title, author, product_name, language, audience_country, "
                        "published_at, observed_at, views, likes, comments, shares, account_followers, duration_s, hook, "
                        "is_ad, notes, created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?) "
                        "ON CONFLICT(url) DO UPDATE SET views=excluded.views, likes=excluded.likes, comments=excluded.comments, "
                        "shares=excluded.shares, account_followers=excluded.account_followers, observed_at=excluded.observed_at",
                        (url.strip(), oembed.platform_of(url), title or None, author or None, name, lang,
                         None if audience == "inconnu" else audience, published.isoformat() if published else None,
                         date.today().isoformat(), views, likes, comments, shares, followers, duration, hook or None,
                         is_ad, notes or None, db.now_iso()))
                try:
                    app_data.write_user(add)
                    st.success("Vidéo enregistrée. Elle sera prise en compte dans les scores à la prochaine recherche.")
                except Exception as e:  # noqa: BLE001
                    st.error(f"Échec de l'enregistrement : {e}")
    m = queries.manual_videos()
    if not m.empty:
        st.subheader("Vidéos saisies")
        st.dataframe(m[["product_name", "platform", "author", "views", "likes", "comments", "shares", "account_followers",
                        "vues_par_jour (calcul)", "vues/abonnés (calcul)", "is_ad", "observed_at", "url"]],
                     hide_index=True, use_container_width=True,
                     column_config={"url": st.column_config.LinkColumn("Lien", display_text="Ouvrir"),
                                    "product_name": "Produit", "is_ad": "Publicité ?", "observed_at": "Relevé le"})
        st.caption("Les vues ne prouvent pas des ventes. Vues/jour = moyenne depuis la publication (estimation).")

with tab2:
    v = queries.youtube_videos()
    if v.empty:
        st.info("Aucune vidéo YouTube : la clé YouTube n'est pas encore configurée.")
    else:
        st.dataframe(v, hide_index=True, use_container_width=True,
                     column_config={"url": st.column_config.LinkColumn("Lien", display_text="Ouvrir"),
                                    "region_recherche": "Région de recherche", "format": "Format (indice)"})
        st.caption("Données YouTube brutes (vues, likes, commentaires, abonnés), sans calcul dérivé, conservées moins de "
                   "30 jours conformément aux règles YouTube. L'API ne signale pas les Shorts : le format est un indice.")
