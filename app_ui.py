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
                # Nettoyage et parsing des lignes
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
    elif any(word in ui_lower for word in ["analyse", "analyze", "summarize","que dis", "résume","résumer","détail-moi", "about", "details"]):
        if not st.session_state.email_cache:
            return "Please list your emails first (e.g., 'show my last emails')."
        
        # Préparation du contexte pour qu'Ollama trouve l'ID
        context_str = "\n".join([f"INDEX:{i} | FROM:{e['from']} | SUBJECT:{e['subject']} | ID:{e['id']}" 
                               for i, e in enumerate(st.session_state.email_cache)])

        search_prompt = f"""
        Analyze the user's request based on this list of emails:
        {context_str}

        User Request: "{user_input}"
        
        Identify the correct Email ID. Return ONLY the ID. If not found, return NONE.
        """
        
        with st.spinner("Finding email..."):
            res = ollama.chat(model='llama3.2', messages=[{"role": "user", "content": search_prompt}])
            target_id = res['message']['content'].strip()
            
            # Extraction propre de l'ID (au cas où l'IA bavarde)
            match = re.search(r'([a-fA-F0-9]{10,})', target_id)
            if match:
                target_id = match.group(1)
                try:
                    analysis = mcp_tools.smart_analyze_email(target_id)
                    email_info = next((e for e in st.session_state.email_cache if e['id'] == target_id), None)

                    
                    # On stocke tout dans la session pour pouvoir éditer
                    st.session_state.current_analysis = {
                        "summary": analysis['summary'],
                        "draft": analysis['draft'], # Ce texte sera modifiable
                        "original_sender": email_info['from'],
                        "original_subject": email_info['subject']
                    }

                    # Affichage avec zone d'édition
                    st.markdown("### 📝 Summary")
                    st.info(st.session_state.current_analysis['summary'])

                    st.markdown("### ✍️ Proposed Reply (You can edit below)")
                    
                    # La zone de texte éditable
                    # Chaque modification de l'utilisateur met à jour st.session_state.current_analysis['draft']
                    edited_draft = st.text_area(
                        "Edit the draft:", 
                        value=st.session_state.current_analysis['draft'], 
                        height=250,
                        key="editable_draft_area"
                    )
                    
                    # Mise à jour du brouillon avec la version éditée
                    st.session_state.current_analysis['draft'] = edited_draft

                    st.warning("Type 'send' or 'yes' to send this exact version.")
                    return "You can now edit the draft above. When ready, type 'send' to send the email."
                except Exception as e:
                    return f"Error analyzing email: {str(e)}"

    # --- 3. LOGIQUE : ENVOYER ---
    elif any(x in ui_lower for x in ["send", "envoie", "confirm", "yes", "oui"]):
        if st.session_state.current_analysis:
            # On récupère la dernière version (potentiellement éditée)
            final_text = st.session_state.current_analysis['draft']
            
            with st.spinner("Sending your corrected email..."):
                res = mcp_tools.send_reply(
                    st.session_state.current_analysis['original_sender'], 
                    st.session_state.current_analysis['original_subject'], 
                    final_text # Envoi du texte corrigé
                )
                st.session_state.current_analysis = None
                return f"✅ Sent successfully!"

    # --- 4. RÉPONSE PAR DÉFAUT ---
    else:
            # On définit un rôle strict pour éviter qu'elle ne dise "Je ne peux pas"
            system_instruction = (
                "You are a helpful Gmail Assistant. "
                "I have provided you with access to the user's emails via specialized tools. "
                "Never ever imagine a response if yuou don't find the answer, don't dare to make fictionnal resume."
                "If the user asks about their emails and you see a list above, use that information. "
                "Never say you don't have access to emails, because I (the system) provide them to you."
            )
            
            res = ollama.chat(model='llama3.2', messages=[
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": user_input}
            ])
            return res['message']['content']

# --- INTERFACE DE CHAT STREAMLIT ---
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if prompt := st.chat_input("Ex: Show my last 3 emails"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        answer = handle_ai_query(prompt)
        st.markdown(answer)
        st.session_state.messages.append({"role": "assistant", "content": answer})