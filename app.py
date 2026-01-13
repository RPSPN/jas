import streamlit as st
import pandas as pd
from datetime import datetime
import os

# --- CONFIGURATION INITIALE ---
FICHIER_CSV = "distribution_alimentaire.csv"
MOT_DE_PASSE_MAITRE = "admin123"  # <--- CHANGEZ LE MOT DE PASSE ICI

LISTE_ITEMS_PREDEFINIS = [
    "Lait", "Oranges", "Huile", "Café", "Pâtes", 
    "Riz", "Conserves", "Pain", "Oeufs", "Oignons", 
    "Carottes", "Poulet", "Boeuf", "Lentilles",
    "Chips", "Céréales", "Extra"
]

# Initialisation de l'état de l'application (Session State)
if 'config_du_jour' not in st.session_state:
    st.session_state.config_du_jour = {}
if 'est_connecte_maitre' not in st.session_state:
    st.session_state.est_connecte_maitre = False

# --- FONCTIONS UTILITAIRES ---

def sauvegarder_transaction(dossier, nb_membres, items_donnes):
    """Sauvegarde les données dans le fichier CSV."""
    date_heure = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    nouvelle_donnee = {
        "Date/Heure": date_heure,
        "Dossier Client": dossier,
        "Membres Famille": nb_membres,
        "Items Donnés": ", ".join(items_donnes)
    }
    
    df_new = pd.DataFrame([nouvelle_donnee])
    
    # Si le fichier n'existe pas, on le crée avec les en-têtes
    if not os.path.isfile(FICHIER_CSV):
        df_new.to_csv(FICHIER_CSV, index=False, sep=';', encoding='utf-8-sig')
    else:
        # Sinon on ajoute à la suite
        df_new.to_csv(FICHIER_CSV, mode='a', header=False, index=False, sep=';', encoding='utf-8-sig')

def charger_donnees():
    """Charge les données pour l'exportation."""
    if os.path.isfile(FICHIER_CSV):
        return pd.read_csv(FICHIER_CSV, sep=';', encoding='utf-8-sig')
    return pd.DataFrame()

# --- INTERFACE UTILISATEUR ---

st.title("🍎 Centre de Distribution Alimentaire")

# Navigation dans la barre latérale
st.sidebar.title("Navigation")
choix_page = st.sidebar.radio("Aller vers :", ["Utilisateur Maître (Config)", "Agent (Distribution)"])

# --- PAGE MAITRE (SÉCURISÉE) ---
if choix_page == "Utilisateur Maître (Config)":
    st.header("Administration")

    # Vérification du mot de passe
    if not st.session_state.est_connecte_maitre:
        mdp_saisi = st.text_input("Entrez le mot de passe administrateur", type="password")
        if st.button("Se connecter"):
            if mdp_saisi == MOT_DE_PASSE_MAITRE:
                st.session_state.est_connecte_maitre = True
                st.rerun() # Recharge la page pour afficher le contenu
            else:
                st.error("Mot de passe incorrect.")
    
    else:
        # CONTENU DE LA PAGE MAITRE (Une fois connecté)
        if st.button("Se déconnecter"):
            st.session_state.est_connecte_maitre = False
            st.rerun()

        st.markdown("---")
        st.subheader("1. Configuration de la journée")
        st.info("Sélectionnez les produits disponibles aujourd'hui et définissez les limites.")

        # Sélection des items
        items_du_jour = st.multiselect(
            "Quels items sont disponibles aujourd'hui ?",
            LISTE_ITEMS_PREDEFINIS,
            default=list(st.session_state.config_du_jour.keys()) # Garde la sélection actuelle si existe
        )

        # Définition des quantités
        config_temp = {}
        
        if items_du_jour:
            st.markdown("##### Définir les quantités limites")
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("🟢 **Petite Famille (≤ 6)**")
            with col2:
                st.markdown("🔵 **Grande Famille (≥ 7)**")

            for item in items_du_jour:
                c1, c2 = st.columns(2)
                # On essaie de récupérer les anciennes valeurs si elles existent
                val_old_p = st.session_state.config_du_jour.get(item, {}).get("small", 1)
                val_old_g = st.session_state.config_du_jour.get(item, {}).get("large", 2)

                with c1:
                    q_petite = st.number_input(f"{item} (≤ 6)", min_value=0, value=val_old_p, key=f"p_{item}")
                with c2:
                    q_grande = st.number_input(f"{item} (≥ 7)", min_value=0, value=val_old_g, key=f"g_{item}")
                
                config_temp[item] = {"small": q_petite, "large": q_grande}

            if st.button("💾 Sauvegarder la configuration du jour", type="primary"):
                st.session_state.config_du_jour = config_temp
                st.success("Configuration mise à jour ! Les agents verront ces quantités.")

        st.markdown("---")
        st.subheader("2. Rapports et Téléchargement")
        
        # Téléchargement du CSV
        df = charger_donnees()
        if not df.empty:
            st.write(f"Total des paniers distribués : **{len(df)}**")
            st.dataframe(df.tail(5)) # Montre les 5 derniers
            st.download_button(
                label="📥 Télécharger le fichier Excel/CSV complet",
                data=df.to_csv(index=False, sep=';', encoding='utf-8-sig').encode('utf-8-sig'),
                file_name=f"rapport_distribution_{datetime.now().strftime('%Y-%m-%d')}.csv",
                mime="text/csv"
            )
        else:
            st.warning("Aucune donnée enregistrée pour le moment.")

# --- PAGE AGENT (OUVERTE) ---
elif choix_page == "Agent (Distribution)":
    st.header("Préparation de panier")

    if not st.session_state.config_du_jour:
        st.warning("⚠️ ATTENTION : L'utilisateur maître n'a pas encore configuré la liste du jour. Veuillez patienter.")
    else:
        # On utilise un conteneur pour rafraîchir le formulaire proprement après soumission
        placeholder = st.empty()

        with placeholder.form("formulaire_panier", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                dossier = st.text_input("Numéro de dossier bénéficiaire")
            with col2:
                nb_famille = st.number_input("Nombre de membres", min_value=1, value=1)

            st.markdown("### Liste des items à donner")
            
            # Logique de sélection (Petite vs Grande famille)
            type_famille = "small" if nb_famille <= 6 else "large"
            items_selectionnes = []

            # Affichage dynamique
            for item, quants in st.session_state.config_du_jour.items():
                quantite = quants[type_famille]
                if quantite > 0:
                    st.markdown(f"**{item}** : {quantite}")
                    # Checkbox invisible pour la logique, ou visible si l'agent doit confirmer manuellement
                    # Ici je pars du principe que si c'est affiché, c'est donné, sauf si décoché
                    if st.checkbox(f"Donné ({item})", value=True, key=f"check_{item}"):
                        items_selectionnes.append(f"{item} ({quantite})")
            
            st.markdown("---")
            submitted = st.form_submit_button("✅ Terminer et Sauvegarder le panier")

            if submitted:
                if not dossier:
                    st.error("Erreur : Le numéro de dossier est obligatoire.")
                else:
                    sauvegarder_transaction(dossier, nb_famille, items_selectionnes)
                    st.success(f"Panier pour le dossier **{dossier}** enregistré !")