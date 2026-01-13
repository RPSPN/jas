import streamlit as st
import pandas as pd
from datetime import datetime
import os
import pytz # Nécessaire pour l'heure de Montréal

# --- CONFIGURATION INITIALE ---
FICHIER_CSV = "distribution_alimentaire.csv"
MOT_DE_PASSE_MAITRE = "admin123"

LISTE_ITEMS_PREDEFINIS = [
    "Lait", "Oranges", "Huile", "Café", "Pâtes", 
    "Riz", "Conserves", "Pain", "Oeufs", "Oignons", 
    "Carottes", "Poulet", "Boeuf", "Lentilles",
    "Chips", "Céréales", "Extra"
]

# Initialisation de l'état de l'application
if 'config_du_jour' not in st.session_state:
    st.session_state.config_du_jour = {}
if 'est_connecte_maitre' not in st.session_state:
    st.session_state.est_connecte_maitre = False

# --- FONCTIONS UTILITAIRES ---

def sauvegarder_transaction(dossier, nb_membres, items_donnes):
    """Sauvegarde les données avec l'heure de Montréal."""
    # Définir le fuseau horaire de Montréal
    tz_mtl = pytz.timezone('America/Montreal')
    date_heure = datetime.now(tz_mtl).strftime("%Y-%m-%d %H:%M:%S")
    
    nouvelle_donnee = {
        "Date/Heure": date_heure,
        "Dossier Client": dossier,
        "Membres Famille": nb_membres,
        "Items Donnés": ", ".join(items_donnes)
    }
    
    df_new = pd.DataFrame([nouvelle_donnee])
    
    if not os.path.isfile(FICHIER_CSV):
        df_new.to_csv(FICHIER_CSV, index=False, sep=';', encoding='utf-8-sig')
    else:
        df_new.to_csv(FICHIER_CSV, mode='a', header=False, index=False, sep=';', encoding='utf-8-sig')

def charger_donnees():
    if os.path.isfile(FICHIER_CSV):
        return pd.read_csv(FICHIER_CSV, sep=';', encoding='utf-8-sig')
    return pd.DataFrame()

# --- INTERFACE UTILISATEUR ---

st.title("🍎 Centre de Distribution Alimentaire")

st.sidebar.title("Navigation")
choix_page = st.sidebar.radio("Aller vers :", ["Utilisateur Maître (Config)", "Agent (Distribution)"])

# --- PAGE MAITRE ---
if choix_page == "Utilisateur Maître (Config)":
    st.header("Administration")

    if not st.session_state.est_connecte_maitre:
        mdp_saisi = st.text_input("Entrez le mot de passe administrateur", type="password")
        if st.button("Se connecter"):
            if mdp_saisi == MOT_DE_PASSE_MAITRE:
                st.session_state.est_connecte_maitre = True
                st.rerun()
            else:
                st.error("Mot de passe incorrect.")
    
    else:
        if st.button("Se déconnecter"):
            st.session_state.est_connecte_maitre = False
            st.rerun()

        st.markdown("---")
        st.subheader("1. Configuration de la journée")
        
        items_du_jour = st.multiselect(
            "Quels items sont disponibles aujourd'hui ?",
            LISTE_ITEMS_PREDEFINIS,
            default=list(st.session_state.config_du_jour.keys())
        )

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
                val_old_p = st.session_state.config_du_jour.get(item, {}).get("small", 1)
                val_old_g = st.session_state.config_du_jour.get(item, {}).get("large", 2)

                with c1:
                    q_petite = st.number_input(f"{item} (≤ 6)", min_value=0, value=val_old_p, key=f"p_{item}")
                with c2:
                    q_grande = st.number_input(f"{item} (≥ 7)", min_value=0, value=val_old_g, key=f"g_{item}")
                
                config_temp[item] = {"small": q_petite, "large": q_grande}

            if st.button("💾 Sauvegarder la configuration", type="primary"):
                st.session_state.config_du_jour = config_temp
                st.success("Configuration mise à jour !")

        st.markdown("---")
        st.subheader("2. Rapports")
        
        df = charger_donnees()
        if not df.empty:
            st.write(f"Total des paniers distribués : **{len(df)}**")
            st.download_button(
                label="📥 Télécharger le fichier CSV complet",
                data=df.to_csv(index=False, sep=';', encoding='utf-8-sig').encode('utf-8-sig'),
                file_name=f"rapport_{datetime.now(pytz.timezone('America/Montreal')).strftime('%Y-%m-%d')}.csv",
                mime="text/csv"
            )

# --- PAGE AGENT ---
elif choix_page == "Agent (Distribution)":
    st.header("Préparation de panier")

    if not st.session_state.config_du_jour:
        st.warning("⚠️ L'utilisateur maître n'a pas encore configuré la liste.")
    else:
        # --- MODIFICATION IMPORTANTE ---
        # On place le nombre de membres HORS du formulaire pour que la mise à jour soit instantanée.
        st.info("Étape 1 : Informations Famille")
        col_famille, col_vide = st.columns([1, 1])
        with col_famille:
            # Changer ce nombre mettra à jour la liste en dessous immédiatement
            nb_famille = st.number_input("Nombre de membres", min_value=1, value=1)

        # Calcul dynamique immédiat
        type_famille = "small" if nb_famille <= 6 else "large"
        
        st.markdown("---")
        st.info(f"Étape 2 : Remplissage du Panier (Mode : {'Grande Famille' if type_famille == 'large' else 'Petite Famille'})")

        # Le reste est dans un formulaire pour grouper l'envoi
        with st.form("formulaire_panier", clear_on_submit=True):
            dossier = st.text_input("Numéro de dossier bénéficiaire")
            
            st.markdown("### Liste des items à donner")
            items_selectionnes_dans_form = []

            # Affichage dynamique basé sur le nb_famille externe
            for item, quants in st.session_state.config_du_jour.items():
                quantite = quants[type_famille]
                
                if quantite > 0:
                    col_check, col_text = st.columns([0.1, 0.9])
                    with col_check:
                        # Value=False pour que ce soit décoché par défaut
                        coche = st.checkbox("Ajout", value=False, key=f"check_{item}", label_visibility="collapsed")
                    with col_text:
                        st.write(f"**{item}** : {quantite} unité(s)")
                    
                    if coche:
                        items_selectionnes_dans_form.append(f"{item} ({quantite})")
            
            st.markdown("---")
            submitted = st.form_submit_button("✅ Terminer et Sauvegarder", type="primary")

            if submitted:
                if not dossier:
                    st.error("Erreur : Le numéro de dossier est obligatoire.")
                elif not items_selectionnes_dans_form:
                    st.warning("Attention : Aucun item n'a été sélectionné.")
                else:
                    sauvegarder_transaction(dossier, nb_famille, items_selectionnes_dans_form)
                    st.success(f"Panier pour le dossier **{dossier}** enregistré à {datetime.now(pytz.timezone('America/Montreal')).strftime('%H:%M')} !")