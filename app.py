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
    if os.path.exists(FICHIER_CSV):
        os.remove(FICHIER_CSV)

# --- GESTION DE L'ÉTAT (SESSION STATE) ---
if 'config_du_jour' not in st.session_state:
    st.session_state.config_du_jour = charger_config_disque()

if 'est_connecte_maitre' not in st.session_state:
    st.session_state.est_connecte_maitre = False

# État pour gérer les sélections de l'agent (Panier courant)
if 'panier_courant' not in st.session_state:
    st.session_state.panier_courant = set() # Un 'set' contient les items uniques sélectionnés

# État pour gérer le champ dossier (pour pouvoir le vider après save)
if 'dossier_input' not in st.session_state:
    st.session_state.dossier_input = ""

# --- INTERFACE UTILISATEUR ---

st.title("🍎 Centre de Distribution")

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
        items_du_jour = st.multiselect("Quels items sont disponibles ?", LISTE_ITEMS_PREDEFINIS, default=items_actuels)

        config_temp = {}
        if items_du_jour:
            st.markdown("##### Quantités par famille")
            col1, col2 = st.columns(2)
            with col1: st.markdown("🟢 **Petite (≤ 6)**")
            with col2: st.markdown("🔵 **Grande (≥ 7)**")

            for item in items_du_jour:
                c1, c2 = st.columns(2)
                val_old_p = st.session_state.config_du_jour.get(item, {}).get("small", 1)
                val_old_g = st.session_state.config_du_jour.get(item, {}).get("large", 2)
                with c1: q_p = st.number_input(f"{item} (≤ 6)", 0, value=val_old_p, key=f"p_{item}")
                with c2: q_g = st.number_input(f"{item} (≥ 7)", 0, value=val_old_g, key=f"g_{item}")
                config_temp[item] = {"small": q_p, "large": q_g}

            if st.button("💾 Sauvegarder Config", type="primary"):
                st.session_state.config_du_jour = config_temp
                sauvegarder_config_disque(config_temp)
                st.success("Configuration sauvegardée !")

        st.markdown("---")
        st.subheader("2. Rapports & Nettoyage")
        df = charger_donnees()
        if not df.empty:
            st.write(f"Total paniers : **{len(df)}**")
            st.download_button("📥 Télécharger CSV", df.to_csv(index=False, sep=';', encoding='utf-8-sig').encode('utf-8-sig'), f"rapport.csv", "text/csv")
            
            st.markdown("---")
            if st.checkbox("Je confirme vouloir effacer TOUT", key="confirm_delete"):
                if st.button("🗑️ Effacer Données", type="primary"):
                    effacer_donnees()
                    st.success("Données effacées.")
                    st.rerun()

# --- PAGE AGENT (INTERFACE MODIFIÉE) ---
elif choix_page == "Agent (Distribution)":
    
    if not st.session_state.config_du_jour:
        st.warning("⚠️ En attente de configuration par le Maître.")
    else:
        # 1. ENTRÉES
        col_dossier, col_famille = st.columns([2, 1])
        with col_dossier:
            # On lie la valeur à session_state pour pouvoir la vider manuellement
            dossier = st.text_input("Numéro de dossier", value=st.session_state.dossier_input, key="input_dossier_widget")
        with col_famille:
            nb_famille = st.number_input("Membres Famille", min_value=1, value=1)

        type_famille = "small" if nb_famille <= 6 else "large"
        
        st.markdown("---")
        st.subheader("📦 Sélection des items")
        
        # 2. GRILLE DE BOUTONS (Items)
        # On utilise des colonnes pour faire joli sur tablette
        cols = st.columns(2) 
        
        index_col = 0
        items_a_afficher = list(st.session_state.config_du_jour.items())

        for item, quants in items_a_afficher:
            quantite = quants[type_famille]
            
            if quantite > 0:
                # Vérifier si l'item est déjà sélectionné dans notre mémoire
                est_selectionne = item in st.session_state.panier_courant
                
                # Définir le texte et le style du bouton
                if est_selectionne:
                    label = f"✅ {item} ({quantite})"
                    type_btn = "primary" # Bouton coloré (souvent rouge ou bleu selon le thème)
                else:
                    label = f"⬜ {item} ({quantite})"
                    type_btn = "secondary" # Bouton gris/neutre

                # Affichage du bouton dans la colonne adéquate
                if cols[index_col % 2].button(label, key=f"btn_{item}", use_container_width=True, type=type_btn):
                    # LOGIQUE AU CLIC : On inverse l'état
                    if est_selectionne:
                        st.session_state.panier_courant.remove(item)
                    else:
                        st.session_state.panier_courant.add(item)
                    st.rerun() # On recharge la page pour mettre à jour le visuel
                
                index_col += 1

        st.markdown("---")
        
        # 3. BOUTON FINAL
        if st.button("💾 TERMINER ET SAUVEGARDER", type="primary", use_container_width=True):
            if not dossier:
                st.error("Erreur : Numéro de dossier manquant.")
            elif not st.session_state.panier_courant:
                st.warning("Erreur : Aucun item sélectionné.")
            else:
                # Préparation de la liste finale pour le CSV
                liste_finale = []
                for item in st.session_state.panier_courant:
                    qty = st.session_state.config_du_jour[item][type_famille]
                    liste_finale.append(f"{item} ({qty})")
                
                sauvegarder_transaction(dossier, nb_famille, liste_finale)
                
                # Message de succès
                st.success(f"✅ Dossier {dossier} sauvegardé !")
                
                # RÉINITIALISATION POUR LE PROCHAIN
                st.session_state.panier_courant = set() # Vider le panier
                # Astuce pour vider le champ texte dossier sans recharger tout le script
                st.session_state.dossier_input = "" 
                # On force la mise à jour de la variable widget pour le prochain rerun
                del st.session_state["input_dossier_widget"]
                
                import time
                time.sleep(1) # Petite pause pour laisser l'agent voir le message vert
                st.rerun()