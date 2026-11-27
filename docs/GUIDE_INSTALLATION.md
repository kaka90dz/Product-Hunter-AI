# Guide d'installation (sans programmation)

## 1. Clé YouTube (gratuite)
1. https://console.cloud.google.com → créer un projet « Product Hunter ».
2. Menu **API et services → Bibliothèque** → « YouTube Data API v3 » → **Activer**.
3. **API et services → Identifiants → Créer des identifiants → Clé API** → copier la clé.
4. (Conseillé) Cliquer sur la clé → **Restrictions relatives aux API** → n'autoriser que « YouTube Data API v3 ».
5. https://github.com/kaka90dz/Product-Hunter-AI/settings/secrets/actions → **New repository secret**
   → Name : `YOUTUBE_API_KEY` → Secret : la clé → **Add secret**.
Google ne facture rien sans compte de facturation : n'en créez pas.

## 2. Jeton GitHub pour le tableau de bord (permissions minimales)
1. https://github.com/settings/personal-access-tokens/new
2. Token name : `product-hunter-dashboard` · Expiration : 1 an.
3. **Repository access → Only select repositories → Product-Hunter-AI**.
4. **Permissions → Repository permissions** : **Actions : Read and write**, **Contents : Read and write**.
   (Metadata : lecture, ajouté automatiquement.) Rien d'autre.
5. **Generate token** → copier le jeton (il ne sera plus affiché). Ne le collez pas dans une conversation.

## 3. Tableau de bord privé sur Streamlit Community Cloud
1. https://share.streamlit.io → **Continue with GitHub** → autoriser l'accès aux dépôts privés.
2. **Create app → Deploy a public app from GitHub** : Repository `kaka90dz/Product-Hunter-AI`, Branch `main`,
   Main file path `streamlit_app.py`.
3. **Advanced settings → Secrets**, coller (en remplaçant la valeur du jeton) :
   ```
   [github]
   token = "VOTRE_JETON"
   repo = "kaka90dz/Product-Hunter-AI"
   data_branch = "data"
   ```
4. **Deploy**. Puis **Settings → Sharing** : « Only specific people can view this app » + votre e-mail.

## 4. Bloquer toute dépense GitHub
https://github.com/settings/billing → **Budgets and alerts** : vérifier que le budget Actions est à 0 $ avec
« Stop usage when budget limit is reached ». Sans moyen de paiement enregistré, GitHub ne peut rien facturer.
