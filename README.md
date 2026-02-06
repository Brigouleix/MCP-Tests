🤖 Assistant Gmail Intelligent (MCP + Llama 3.2)
Ce projet est un assistant personnel capable de lister, résumer et répondre à vos emails Gmail en utilisant l'intelligence locale de Llama 3.2 via Ollama et le protocole MCP.

📋 Prérequis
Python 3.10+ installé.

Ollama installé (ollama.com).

Un fichier credentials.json valide (récupéré sur la Google Cloud Console avec l'API Gmail activée).

🚀 Installation Rapide
1. Cloner le projet et créer l'environnement
Bash
git clone <URL_DU_REPO>
cd mon-serveur-mcp

# Création de l'environnement virtuel
python -m venv venv
# Activation (Windows)
.\venv\Scripts\activate
# Activation (Mac/Linux)
# source venv/bin/activate

# Installation des dépendances
pip install streamlit google-api-python-client google-auth-oauthlib mcp ollama
2. Configuration Google Cloud
Placez votre fichier credentials.json à la racine du dossier.

Assurez-vous que l'URI de redirection http://localhost:0 (ou le port spécifique utilisé) est bien configuré dans votre console Google.

3. Préparation de l'IA
Lancez Ollama et téléchargez le modèle :

Bash
ollama pull llama3.2
🛠️ Utilisation
Pour faire fonctionner l'assistant, vous devez lancer deux terminaux :

Étape A : Lancer le serveur (Backend)
Bash
python server_mcp.py
Note : Au premier lancement, une fenêtre de navigateur s'ouvrira pour autoriser l'accès à votre compte Gmail. Cela générera un fichier token.json local.

Étape B : Lancer l'interface (Frontend)
Ouvrez un second terminal et lancez :

Bash
streamlit run app_ui.py


📂 Structure du projet
server_mcp.py : Le serveur MCP gérant l'authentification Google et la logique IA (Ollama).

app_ui.py : L'interface utilisateur Streamlit.

credentials.json : Vos clés secrètes Google API (ne pas partager !).

token.json : Vos jetons d'accès personnels (générés automatiquement).

💡 Astuce de dépannage
Si vous obtenez une erreur de type Invalid Grant ou Token Expired, supprimez simplement le fichier token.json et relancez server_mcp.py pour renouveler l'authentification.
