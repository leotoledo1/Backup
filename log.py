import logging
import os
import sys
from datetime import datetime

# =================================================================
# GESTÃO DE LOGS E AUDITORIA
# =================================================================

def base_dir():
    """ 
    Identifica o diretório base para salvar os logs.
    Se o programa for um executável (.exe), usa a pasta do executável.
    Se for um script (.py), usa a pasta onde o script está salvo.
    """
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

def configurar_logger(nome="Backup_Mercosistem"):
    """
    Configura o sistema de log da aplicação. 
    Cria automaticamente uma pasta 'LOGS_BACKUP_MERCOSISTEM' e gera arquivos 
    diários para facilitar a manutenção e auditoria dos backups.
    """
    base = base_dir()
    pasta_logs = os.path.join(base, "LOGS_BACKUP_MERCOSISTEM")
    
    # Garante que a pasta de logs exista antes de tentar criar o arquivo
    os.makedirs(pasta_logs, exist_ok=True)

    # Define o nome do arquivo com a data atual (ex: Backup_Mercosistem_20260124.log)
    log_file = os.path.join(
        pasta_logs,
        f"{nome}_{datetime.now().strftime('%Y%m%d')}.log"
    )

    # Configuração do formato do log:
    # %(asctime)s    -> Horário exato do evento
    # %(levelname)s  -> Tipo (INFO, WARNING, ERROR, CRITICAL)
    # %(message)s    -> A descrição do que aconteceu
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
        handlers=[
            # FileHandler com encoding utf-8 para suportar acentos nas mensagens
            logging.FileHandler(log_file, encoding="utf-8"),
        ]
    )

    return logging.getLogger(nome)