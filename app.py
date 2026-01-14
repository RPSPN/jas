import streamlit as st
import pandas as pd
from datetime import datetime
import os
import pytz
import json

# --- CONFIGURATION INITIALE ---
FICHIER_CSV = "distribution_alimentaire.csv"
FICHIER_CONFIG = "config_active.json"
MOT_DE_PASSE_MAITRE = "admin123"

LISTE_ITEMS_PREDEFINIS = [
    "Oranges", "Pommes", "Patates", "Onions", "Carottes", "Legumes (conserve)", "Thon (conserve)", "Huile", "Chips", "Riz", "Pates", "Biscuits", "Lait", "Oeufs", "Tofu", "Sauce Tomate (conserve)", "Soupe (conserve)", "Fruits (conserve)", "Café", "Base à soupe", "Poulet (congelé)", "Boeuf (congelé)", "Porc (congelé)", "Poisson (congelé)", "Viande Autres (congelé)", "Bagels", "Quinoa (pour Végé)", "Pois chiches (pour Végé)", "Lentilles (pour Végé)", "Extra"
]

# --- FONCTIONS UTILITAIRES ---

def charger_config_disque():
    if os.path.exists(FICHIER_CONFIG):
        try:
            with open(FICHIER_CONFIG, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    return {}

def sauvegarder_config_disque(config):
    with open(FICHIER_CONFIG, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=4)

def sauvegarder_transaction(dossier, nb_membres, items_donnes):
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

def effacer_donnees():
    """Supprime le fichier CSV."""
    if os.path.exists(FICHIER_CSV):
        os.remove(FICHIER_CSV)

# --- INITIALISATION STATE ---
if 'config_du_jour' not in st.session_state:
    st.session_state.config_du_jour = charger_config_disque()

if 'est_connecte_maitre' not in st.session_state:
    st.session_state.est_connecte_maitre = False

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
        
        items_actuels = list(st.session_state.config_du_jour.keys())
        
        items_du_jour = st.multiselect(
            "Quels items sont disponibles aujourd'hui ?",
            LISTE_ITEMS_PREDEFINIS,
            default=items_actuels
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
                sauvegarder_config_disque(config_temp)
                st.success("Configuration mise à jour et sauvegardée en mémoire !")

        st.markdown("---")
        st.subheader("2. Rapports & Nettoyage")
        
        df = charger_donnees()
        if not df.empty:
            st.write(f"Total des paniers distribués : **{len(df)}**")
            
            # Bouton de téléchargement
            st.download_button(
                label="📥 Télécharger le fichier CSV complet",
                data=df.to_csv(index=False, sep=';', encoding='utf-8-sig').encode('utf-8-sig'),
                file_name=f"rapport_{datetime.now(pytz.timezone('America/Montreal')).strftime('%Y-%m-%d')}.csv",
                mime="text/csv"
            )
            
            st.markdown("---")
            st.markdown("### ⚠️ Zone de Danger")
            # Protection contre l'effacement accidentel
            if st.checkbox("Je confirme vouloir effacer TOUTES les données enregistrées", key="confirm_delete"):
                if st.button("🗑️ Effacer définitivement les données", type="primary"):
                    effacer_donnees()
                    st.success("Toutes les données ont été effacées.")
                    st.rerun()
        else:
            st.info("Aucune donnée enregistrée pour le moment.")

# --- PAGE AGENT ---
elif choix_page == "Agent (Distribution)":
    st.header("Préparation de panier")

    if not st.session_state.config_du_jour:
        st.warning("⚠️ L'utilisateur maître n'a pas encore configuré la liste.")
    else:
        st.info("Étape 1 : Informations Famille")
        col_famille, col_vide = st.columns([1, 1])
        with col_famille:
            nb_famille = st.number_input("Nombre de membres", min_value=1, value=1)

        type_famille = "small" if nb_famille <= 6 else "large"
        
        st.markdown("---")
        st.info(f"Étape 2 : Remplissage du Panier (Mode : {'Grande Famille' if type_famille == 'large' else 'Petite Famille'})")

        with st.form("formulaire_panier", clear_on_submit=True):
            dossier = st.text_input("Numéro de dossier bénéficiaire")
            
            st.markdown("### Liste des items à donner")
            items_selectionnes_dans_form = []

            for item, quants in st.session_state.config_du_jour.items():
                quantite = quants[type_famille]
                
                if quantite > 0:
                    col_check, col_text = st.columns([0.1, 0.9])
                    with col_check:
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