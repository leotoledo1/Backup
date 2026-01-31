import os
import requests
from datetime import datetime
from dotenv import load_dotenv
load_dotenv()

API_KEY_DISCORD = os.getenv("API_KEY_DISCORD")
WEBHOOK_URL = API_KEY_DISCORD

def enviar_log_discord(status, codigo_empresa, mensagem, detalhes=""):
    """
    Envia um card colorido para o Discord.
    status: 'sucesso' ou 'erro'
    """
    cor = 65280 if status == 'sucesso' else 16711680  # Verde ou Vermelho
    
    payload = {
        "embeds": [{
            "title": f"Relatório de Backup - Cliente {codigo_empresa}",
            "color": cor,
            "fields": [
                {"name": "Status", "value": status.upper(), "inline": True},
                {"name": "Data/Hora", "value": datetime.now().strftime("%d/%m/%Y %H:%M:%S"), "inline": True},
                {"name": "Mensagem", "value": mensagem},
                {"name": "Detalhes Técnicos", "value": detalhes[:1000]} # Limite do Discord
            ],
            "footer": {"text": "Sistema de Backup Automatizado"}
        }]
    }

    try:
        requests.post(WEBHOOK_URL, json=payload, timeout=10)
    except Exception as e:
        print(f"Falha ao enviar log online: {e}")