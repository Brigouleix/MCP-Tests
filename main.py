from mcp.server.fastmcp import FastMCP
import psutil
import platform
from datetime import datetime

# Création du serveur avec FastMCP (la méthode la plus simple du SDK)
mcp = FastMCP("Mon Serveur Natif")

@mcp.tool()
def get_system_info():
    """Récupère le CPU, la RAM et l'OS du PC."""
    cpu = psutil.cpu_percent(interval=1)
    ram = psutil.virtual_memory().percent
    os_name = platform.system()
    return f"Système: {os_name} | CPU: {cpu}% | RAM: {ram}%"

@mcp.tool()
def get_time():
    """Donne l'heure exacte."""
    return f"Il est {datetime.now().strftime('%H:%M:%S')}"

if __name__ == "__main__":
    # On lance le serveur en mode 'stdio' (standard input/output)
    mcp.run()