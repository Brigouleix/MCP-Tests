import os
import base64
import re
import logging
from typing import Any
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from mcp.server.fastmcp import FastMCP
from email.message import EmailMessage
import ollama
# Configuration des Logs
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger("GmailEngine")

SCOPES = ['https://www.googleapis.com/auth/gmail.readonly', 'https://www.googleapis.com/auth/gmail.send']
mcp = FastMCP("Gmail_Engine")

def get_gmail_service():
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    return build('gmail', 'v1', credentials=creds)

@mcp.tool()
def list_emails(max_results: Any = 5):
    """List recent emails. Returns technical IDs, Senders, and Subjects."""
    try:
        limit = int(max_results) if not isinstance(max_results, dict) else max_results.get('value', 5)
    except: limit = 5

    service = get_gmail_service()
    try:
        results = service.users().messages().list(
        userId='me', 
        maxResults=limit, 
        q='label:INBOX -from:me' 
    ).execute()
        
        messages = results.get('messages', [])
        output = "DATA_START\n"
        for msg in messages:
            m = service.users().messages().get(userId='me', id=msg['id']).execute()
            headers = m['payload']['headers']
            sender = next((h['value'] for h in headers if h['name'] == 'From'), "Unknown")
            subject = next((h['value'] for h in headers if h['name'] == 'Subject'), "No Subject")
            output += f"ID: {msg['id']} | FROM: {sender} | SUBJECT: {subject}\n"
        return output + "DATA_END"
    except Exception as e:
        return f"Error: {str(e)}"

@mcp.tool()
def get_email_content(message_id: str):
    """Retrieve full body of an email using its technical ID."""
    clean_id = re.sub(r'[^a-zA-Z0-9]', '', str(message_id))
    service = get_gmail_service()
    try:
        msg = service.users().messages().get(userId='me', id=clean_id, format='full').execute()
        def get_text(payload):
            if payload.get('mimeType') == 'text/plain':
                data = payload.get('body', {}).get('data')
                return base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore') if data else ""
            if 'parts' in payload:
                for part in payload['parts']:
                    res = get_text(part)
                    if res: return res
            return ""
        content = get_text(msg.get('payload', {})) or msg.get('snippet', "No content.")
        return f"BODY_START\n{content[:3000]}\nBODY_END"
    except Exception as e:
        return f"Error: {str(e)}"

@mcp.tool()
def send_reply(recipient: str, subject: str, body: str):
    """Send an email. Final step after user validation."""
    match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', recipient)
    target = match.group(0) if match else recipient.strip()
    service = get_gmail_service()
    message = EmailMessage()
    message.set_content(body)
    message['To'] = target
    message['From'] = 'me'
    message['Subject'] = subject if subject.lower().startswith("re:") else f"Re: {subject}"
    try:
        raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
        service.users().messages().send(userId="me", body={'raw': raw}).execute()
        return "SUCCESS_SENT"
    except Exception as e:
        return f"FAILURE: {str(e)}"
    

def _ask_llama(content, prompt_type="summary"):
    """Fonction interne pour interroger Llama 3.2"""
    # Nettoyage automatique des balises avant envoi à l'IA
    clean = content.replace("BODY_START", "").replace("BODY_END", "").replace("---", "").strip()
    
    if prompt_type == "summary":
        p = f"Résume cet email de manière très concise (3 points max) :\n\n{clean}"
    else:
        p = f"Rédige une réponse pro et chaleureuse à cet email. Ne mets aucun commentaire, écris juste le message :\n\n{clean}"
    
    try:
        response = ollama.chat(model='llama3.2', messages=[
            {'role': 'system', 'content': 'Tu es un assistant Gmail efficace.'},
            {'role': 'user', 'content': p}
        ])
        return response['message']['content']
    except:
        return "Erreur d'analyse IA."

@mcp.tool()
def smart_analyze_email(message_id: str):
    """Outil combiné : récupère, nettoie et analyse l'email."""
    # 1. Utilise ta fonction get_email_content existante
    raw_content = get_email_content(message_id)
    
    # 2. Génère les deux versions
    summary = _ask_llama(raw_content, "summary")
    draft = _ask_llama(raw_content, "reply")
    
    return {
        "summary": summary,
        "draft": draft
    }

if __name__ == "__main__":
    mcp.run()
    