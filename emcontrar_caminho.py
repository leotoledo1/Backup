import os
import sys
import fdb
import re
import subprocess
from dotenv import load_dotenv
load_dotenv()
from log import configurar_logger

log = configurar_logger()

FB_USER = os.getenv("FB_USER")
FB_PASS = os.getenv("FB_PASS")

def caminho_base():
    if getattr(sys, 'frozen', False):
        exe_dir = os.path.dirname(sys.executable)
    else:
        exe_dir = os.path.dirname(os.path.abspath(__file__))

    if os.path.basename(exe_dir).lower() == "ferramentas":
        return os.path.dirname(exe_dir)

    return exe_dir

def capturar_portas_firebird():
    cmd = 'netstat -ano | findstr LISTENING | findstr 305'
    result = subprocess.run(cmd, capture_output=True, text=True, shell=True)

    portas = set()
    for linha in result.stdout.splitlines():
        match = re.search(r':(\d+)', linha)
        if match:
            portas.add(int(match.group(1)))

    return sorted(portas)

def encontrar_banco_base(base_path):
    # Primeiro tenta achar EMPRESA.GDB
    for root, dirs, files in os.walk(base_path):
        for file in files:
            if file.lower() == "empresa.gdb":
                return os.path.join(root, file)

    # Se não achar EMPRESA.GDB, tenta achar GESTAO.FDB
    for root, dirs, files in os.walk(base_path):
        for file in files:
            if file.lower() == "gestao.fdb":
                return os.path.join(root, file)

    return None

def conectar_firebird(host, porta, banco, user, senha):
    banco = os.path.abspath(banco)
    dsn = f"{host}/{porta}:{banco}"
    return fdb.connect(dsn=dsn, user=user, password=senha)

def obter_bases(empresa_db, portas_firebird):
    """
    Tenta conectar nas portas Firebird e obter as bases do EMPRESA.GDB.
    Retorna lista de caminhos de bases.
    """
    ultimo_erro = None

    for porta in portas_firebird:
        try:
            log.info(f"Tentando conectar na porta {porta}...")
            conn = conectar_firebird(
                host="localhost",
                porta=porta,
                banco=empresa_db,
                user=FB_USER,
                senha=FB_PASS
            )

            cur = conn.cursor()
            cur.execute("SELECT e.caminho FROM EMPRESA e WHERE e.ATIVO = 1")
            bases = [row[0] for row in cur.fetchall()]

            conn.close()

            log.info(f"Conectado com sucesso na porta {porta}")
            return bases

        except Exception as e:
            ultimo_erro = e
            log.error(f"Falha na porta {porta}: {e}")

    if ultimo_erro:
        raise ultimo_erro
    return []

if __name__ == "__main__":
    # Este bloco serve apenas para você testar este arquivo isoladamente
    try:
        load_dotenv() # Garante que as variáveis carreguem no teste
        base_teste = caminho_base()
        db_teste = encontrar_banco_base(base_teste)

        if not db_teste:
            print("Nenhum banco base encontrado.")
        else:
            portas = capturar_portas_firebird()
            if db_teste.lower().endswith("empresa.gdb"):
                lista_bases = obter_bases(db_teste, portas)
            else:
                lista_bases = [db_teste]
            print(f"Bases encontradas: {lista_bases}")
    except Exception as e:
        print(f"Erro no teste: {e}")