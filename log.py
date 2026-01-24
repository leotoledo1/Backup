import logging
import os
import sys
from datetime import datetime

def base_dir():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

def configurar_logger(nome="Backup_Mercosistem"):
    base = base_dir()
    pasta_logs = os.path.join(base, "LOGS_BACKUP_MERCOSISTEM")
    os.makedirs(pasta_logs, exist_ok=True)

    log_file = os.path.join(
        pasta_logs,
        f"{nome}_{datetime.now().strftime('%Y%m%d')}.log"
    )

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
        ]
    )

    return logging.getLogger(nome)
