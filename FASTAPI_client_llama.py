import ollama
import requests

# Llama voit ce menu, mais il ne sait pas COMMENT les fonctions marchent
tools = [
    {'type': 'function', 'function': {'name': 'get_system_stats', 'description': 'Stats PC'}},
    {'type': 'function', 'function': {'name': 'get_os_info', 'description': 'Infos OS'}},
    {'type': 'function', 'function': {'name': 'get_time', 'description': 'Heure'}}
]

def run_agent():
    prompt = "Utilise tes outils pour me donner l'heure EXACTE et ensuite utilise ton outil OS pour me dire sur quel système je tourne."
    # 1. L'IA analyse la demande
    response = ollama.chat(model='llama3.2:latest', messages=[{'role': 'user', 'content': prompt}], tools=tools)
    
    messages = [{'role': 'user', 'content': prompt}, response['message']]

    if response.get('message', {}).get('tool_calls'):
        for tool in response['message']['tool_calls']:
            tool_name = tool['function']['name']
            print(f"[Client] Je demande au SERVEUR d'exécuter : {tool_name}")
            
            # 2. LE CLIENT APPELLE LE SERVEUR (Le lien !)
            res = requests.get(f"http://127.0.0.1:8000/execute/{tool_name}")
            
            # 3. On donne la réponse du serveur à l'IA
            messages.append({'role': 'tool', 'content': res.text, 'name': tool_name})

        # 4. L'IA fait sa phrase finale
        final = ollama.chat(model='llama3.2:latest', messages=messages)
        print(f"\nLlama dit : {final['message']['content']}")

if __name__ == "__main__":
    run_agent()