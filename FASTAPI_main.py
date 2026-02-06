from fastapi import FastAPI, Request
from mcp.server import Server
from mcp.server.sse import SseServerTransport
import psutil
import platform
from datetime import datetime

app = FastAPI(title="Mon Serveur MCP")
mcp_server = Server("mon-serveur")
sse = SseServerTransport("/messages")

# LA CUISINE : C'est ici qu'on fait le vrai travail
@mcp_server.call_tool()
async def handle_call_tool(name: str, arguments: dict):
    if name == "get_system_stats":
        return [{"type": "text", "text": f"CPU: {psutil.cpu_percent(interval=1)}% | RAM: {psutil.virtual_memory().percent}%"}]
    elif name == "get_os_info" or name == "get_os_infos":
        return [{"type": "text", "text": f"OS: {platform.platform()}"}]
    elif name == "get_time":
        return [{"type": "text", "text": f"Heure: {datetime.now().strftime('%H:%M:%S')}"}]
    raise ValueError("Outil inconnu")

# LA PORTE D'ENTRÉE : Pour que le client puisse demander l'exécution
@app.get("/execute/{tool_name}")
async def execute_tool(tool_name: str):
    # Le serveur appelle sa propre cuisine interne
    result = await handle_call_tool(tool_name, {})
    return result[0]["text"]

# LE TUNNEL MCP (indispensable pour être un vrai serveur MCP)
@app.get("/sse")
async def handle_sse(request: Request):
    async with sse.connect_sse(request.scope, request.receive, request._send) as (read_stream, write_stream):
        await mcp_server.run(read_stream, write_stream, mcp_server.create_initialization_options())