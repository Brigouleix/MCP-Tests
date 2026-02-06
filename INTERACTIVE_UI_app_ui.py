import streamlit as st
import re
# Note : On n'importe plus ollama ici, c'est le serveur qui s'en charge !
from INTERACTIVE_server_mcp import list_emails, smart_analyze_email, send_reply 

# --- CONFIGURATION ---
st.set_page_config(page_title="IA Gmail Assistant", page_icon="🤖", layout="wide")

st.title("🤖 Mon Assistant Gmail Intelligent")
st.caption("Piloté par nos Pious Pious IA, pour une gestion de mails sans stress !")

# Initialisation des variables de session
if "emails" not in st.session_state: st.session_state.emails = []
if "selected_email" not in st.session_state: st.session_state.selected_email = None
if "summary" not in st.session_state: st.session_state.summary = ""
if "draft" not in st.session_state: st.session_state.draft = ""

# --- BARRE LATÉRALE ---
with st.sidebar:
    st.header("⚙️ Contrôles")
    num_mails = st.slider("Nombre de mails à scanner", 1, 10, 5)
    
    if st.button("🔄 Scanner ma boîte Gmail", use_container_width=True):
        with st.spinner("Récupération en cours..."):
            raw_data = list_emails(max_results=num_mails)
            parsed = []
            for line in raw_data.split('\n'):
                match = re.search(r"ID:\s*(\w+)\s*\|\s*FROM:\s*(.*?)\s*\|\s*SUBJECT:\s*(.*)", line)
                if match:
                    parsed.append({
                        "id": match.group(1),
                        "from": match.group(2),
                        "subject": match.group(3)
                    })
            st.session_state.emails = parsed
            st.success(f"{len(parsed)} mails trouvés.")

    st.markdown("---")
    st.subheader("✍️ Actions")
    gmail_compose_url = "https://mail.google.com/mail/?view=cm&fs=1"
    st.link_button("➕ Nouveau mail (Gmail)", gmail_compose_url, use_container_width=True)

# --- AFFICHAGE PRINCIPAL ---
if st.session_state.emails:
    col_list, col_analyser = st.columns([1, 1])

    with col_list:
        st.subheader("📬 Derniers Messages")
        for mail in st.session_state.emails:
            with st.expander(f"**{mail['subject']}**"):
                st.write(f"De : {mail['from']}")
                if st.button("🧠 Analyser ce mail", key=f"btn_{mail['id']}"):
                    with st.spinner("Llama analyse et prépare la réponse..."):
                        # ON APPELLE LA NOUVELLE FONCTION DU SERVEUR
                        analysis = smart_analyze_email(mail['id'])
                        
                        st.session_state.summary = analysis["summary"]
                        st.session_state.draft = analysis["draft"]
                        st.session_state.selected_email = mail
                    st.rerun()

    with col_analyser:
        if st.session_state.selected_email:
            st.subheader("✨ Analyse de l'IA")
            
            st.markdown("#### 📝 Résumé du message")
            st.info(st.session_state.summary)
            
            st.markdown("#### ✍️ Réponse suggérée")
            final_reply = st.text_area("Brouillon (modifiable) :", 
                                       value=st.session_state.draft, height=300)
            
            c1, c2 = st.columns(2)
            if c1.button("🚀 Envoyer maintenant", use_container_width=True):
                with st.spinner("Envoi..."):
                    res = send_reply(
                        st.session_state.selected_email['from'],
                        st.session_state.selected_email['subject'],
                        final_reply
                    )
                st.success("C'est envoyé !")
                st.balloons()
                st.session_state.selected_email = None
                
            if c2.button("🗑️ Ignorer", use_container_width=True):
                st.session_state.selected_email = None
                st.rerun()
        else:
            st.info("Sélectionnez un email à gauche pour lancer l'analyse intelligente.")
else:
    st.write("Cliquez sur 'Scanner' pour charger vos messages.")