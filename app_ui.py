import streamlit as st
import ollama
import re
import server_mcp as mcp_tools 

# --- CONFIGURATION ---
st.set_page_config(page_title="IA Gmail Assistant", page_icon="🤖")
st.title("🤖 Mon Assistant Gmail par Prompt")

# Initialisation de la session
if "messages" not in st.session_state:
    st.session_state.messages = []
if "email_cache" not in st.session_state:
    st.session_state.email_cache = []
if "current_analysis" not in st.session_state:
    st.session_state.current_analysis = None

def handle_ai_query(user_input):
    ui_lower = user_input.lower()
    
    # --- 1. LOGIQUE : LISTER ---
    if any(x in ui_lower for x in ["list", "liste", "show", "voir", "donne-moi", "affiche", "montre", "quels sont"]):
        numbers = re.findall(r'\d+', ui_lower)
        n = int(numbers[0]) if numbers else 5
        
        with st.spinner(f"Fetching {n} emails..."):
            try:
                raw_data = mcp_tools.list_emails(max_results=n)
                parsed = []
                clean_data = raw_data.replace("DATA_START", "").replace("DATA_END", "").strip()
                lines = clean_data.split('\n')
                
                for line in lines:
                    m = re.search(r"ID:\s*(\w+)\s*\|\s*FROM:\s*(.*?)\s*\|\s*SUBJECT:\s*(.*)", line)
                    if m:
                        parsed.append({"id": m.group(1), "from": m.group(2), "subject": m.group(3)})
                
                st.session_state.email_cache = parsed
                
                if not parsed:
                    return "No emails found in your Inbox."
                
                response_text = f"I found {len(parsed)} emails in your Inbox:\n\n"
                for i, e in enumerate(parsed, 1):
                    response_text += f"{i}. **From:** {e['from']}  \n**Objet:** {e['subject']}\n\n"
                return response_text
            except Exception as e:
                return f"Error accessing Gmail: {str(e)}"

# --- 2. LOGIQUE : ANALYSER / RÉSUMER ---
    elif any(word in ui_lower for word in ["analyse", "analyze", "summarize", "que dis", "résume", "détail", "about", "details"]):
        if not st.session_state.email_cache:
            return "Désolé, ma liste est vide. Dis-moi 'montre mes mails' d'abord."
        
        # On prépare un contexte très clair pour Llama
        context_str = ""
        for i, e in enumerate(st.session_state.email_cache, 1):
            context_str += f"CHOIX {i}: ID={e['id']} | FROM={e['from']} | SUBJECT={e['subject']}\n"

        search_prompt = f"""
        Voici la liste des emails récents :
        {context_str}

        L'utilisateur demande : "{user_input}"
        Trouve l'ID correspondant à sa demande (il peut citer un numéro de choix, un nom ou un sujet).
        Renvoie UNIQUEMENT l'ID technique (ex: 18db...) ou le mot NONE.
        """
        
        with st.spinner("Identification de l'email..."):
            res = ollama.chat(model='llama3.2', messages=[{"role": "user", "content": search_prompt}])
            target_id = res['message']['content'].strip()
            
            # Nettoyage de la réponse de l'IA (parfois elle bavarde)
            match = re.search(r'([a-fA-F0-9]{10,})', target_id)
            
            if match:
                target_id = match.group(1)
                try:
                    # On vérifie que l'ID existe bien dans notre cache
                    email_info = next((e for e in st.session_state.email_cache if e['id'] == target_id), None)
                    
                    if not email_info:
                        return f"L'IA a trouvé l'ID {target_id} mais il ne correspond pas à la liste actuelle."

                    analysis = mcp_tools.smart_analyze_email(target_id)
                    
                    # CRUCIAL : On stocke l'adresse email exacte extraite de 'from'
                    # Souvent 'from' est "Nom <email@test.com>", on nettoie pour n'avoir que l'email
                    raw_from = email_info['from']
                    clean_email = re.search(r'[\w\.-]+@[\w\.-]+', raw_from)
                    recipient = clean_email.group(0) if clean_email else raw_from

                    st.session_state.current_analysis = {
                        "summary": analysis['summary'],
                        "draft": analysis['draft'],
                        "original_sender": recipient, # On utilise l'email propre ici
                        "original_subject": email_info['subject'],
                        "original_id": target_id
                    }
                    return "ANALYSIS_COMPLETE"
                except Exception as e:
                    return f"Erreur lors de l'analyse : {str(e)}"
            else:
                return "Je n'ai pas compris de quel email tu parles. Peux-tu préciser (ex: 'le mail de Jean' ou 'le mail numéro 2') ?"

    # --- 3. LOGIQUE : ENVOYER ---
    elif any(x in ui_lower for x in ["send", "envoie", "confirm", "yes", "oui"]):
        if st.session_state.current_analysis:
            final_text = st.session_state.current_analysis['draft']
            with st.spinner("Sending..."):
                res = mcp_tools.send_reply(
                    st.session_state.current_analysis['original_sender'], 
                    st.session_state.current_analysis['original_subject'], 
                    final_text
                )
                st.session_state.current_analysis = None # On vide après envoi
                return f"✅ Envoyeeyyy ! Status: {res}"
        else:
            return "No draft to send. Analyze an email first."

    # --- 4. RÉPONSE PAR DÉFAUT ---
    else:
        system_instruction = "You are a helpful Gmail Assistant. Use provided info."
        res = ollama.chat(model='llama3.2', messages=[
            {"role": "system", "content": system_instruction},
            {"role": "user", "content": user_input}
        ])
        return res['message']['content']

# --- AFFICHAGE DU CHAT ---
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# --- INTERFACE D'ÉDITION (Toujours visible si une analyse est en cours) ---
if st.session_state.current_analysis:
    with st.expander("✨ Edition du brouillon en cours", expanded=True):
        st.info(f"**Résumé :** {st.session_state.current_analysis['summary']}")
        
        # Le TEXT_AREA met à jour la session en direct
        edited_text = st.text_area(
            "Modifiez votre réponse :", 
            value=st.session_state.current_analysis['draft'], 
            height=200
        )
        st.session_state.current_analysis['draft'] = edited_text
        st.caption("Une fois prêt, tape 'envoie' ou 'send' dans le chat ci-dessous.")

# --- ENTRÉE DU CHAT ---
if prompt := st.chat_input("Ex: Montre moi mes 3 derniers "):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        answer = handle_ai_query(prompt)
        if answer != "ANALYSIS_COMPLETE":
            st.markdown(answer)
            st.session_state.messages.append({"role": "assistant", "content": answer})
        else:
            st.rerun() # On relance pour afficher l'expander d'édition