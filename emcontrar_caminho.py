import os
import sys
import fdb
import re
import subprocess
from dotenv import load_dotenv

# Carrega as variáveis de ambiente (usuário e senha do banco)
load_dotenv()
from log import configurar_logger

log = configurar_logger()

# Credenciais de acesso ao Firebird extraídas do .env
FB_USER = os.getenv("FB_USER")
FB_PASS = os.getenv("FB_PASS")

# =================================================================
# LOCALIZAÇÃO DE DIRETÓRIOS E INSTÂNCIAS
# =================================================================

def caminho_base():
    """ 
    Determina a pasta raiz da aplicação.
    Lida com a diferença entre rodar como script (.py) ou executável (.exe).
    Se o executável estiver dentro de uma subpasta 'ferramentas', sobe um nível.
    """
    if getattr(sys, 'frozen', False):
        exe_dir = os.path.dirname(sys.executable)
    else:
        exe_dir = os.path.dirname(os.path.abspath(__file__))

    # Se estiver rodando de dentro da pasta 'ferramentas', ajusta para a raiz
    if os.path.basename(exe_dir).lower() == "ferramentas":
        return os.path.dirname(exe_dir)

    return exe_dir

def capturar_portas_firebird():
    """ 
    Varre o sistema via comando netstat para encontrar quais portas (3050, 3051...)
    possuem instâncias do Firebird ativas e escutando conexões.
    """
    # Executa comando de rede para filtrar portas 305x (padrão Firebird)
    cmd = 'netstat -ano | findstr LISTENING | findstr 305'
    result = subprocess.run(cmd, capture_output=True, text=True, shell=True)

    portas = set()
    for linha in result.stdout.splitlines():
        match = re.search(r':(\d+)', linha)
        if match:
            portas.add(int(match.group(1)))

    return sorted(portas)

def encontrar_banco_base(base_path):
    """ 
    Realiza uma busca recursiva no diretório para encontrar o banco de dados principal.
    Prioridade: 1º EMPRESA.GDB (Sistemas antigos) | 2º GESTAO.FDB (Sistemas novos).
    """
    # Busca prioritária por EMPRESA.GDB
    for root, dirs, files in os.walk(base_path):
        for file in files:
            if file.lower() == "empresa.gdb":
                return os.path.join(root, file)

    # Busca secundária por GESTAO.FDB
    for root, dirs, files in os.walk(base_path):
        for file in files:
            if file.lower() == "gestao.fdb":
                return os.path.join(root, file)

    return None

# =================================================================
# CONEXÃO E DESCOBERTA DE BASES DE DADOS
# =================================================================

def conectar_firebird(host, porta, banco, user, senha):
    """ Atalho para criar uma string DSN e conectar ao banco de dados. """
    banco = os.path.abspath(banco)
    dsn = f"{host}/{porta}:{banco}"
    return fdb.connect(dsn=dsn, user=user, password=senha)

def obter_bases(empresa_db, portas_firebird):
    """
    Tenta conexão no banco mestre (EMPRESA.GDB) testando todas as portas encontradas.
    Uma vez conectado, lê a tabela 'EMPRESA' para listar todos os outros bancos ativos
    que precisam sofrer backup.
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
            log.info("Conexão bem-sucedida EMPRESA.GDB. Buscando bases de dados ativas...")
            # Busca o caminho de todas as bases de dados cadastradas e ativas no sistema
            cur.execute("SELECT e.caminho FROM EMPRESA e WHERE e.ATIVO = 1")
            bases = [row[0] for row in cur.fetchall()]

            conn.close()
            log.info(f"Conectado com sucesso na porta {porta}")
            return bases

        except Exception as e:
            ultimo_erro = e
            log.error(f"Falha na porta {porta}: {e}")

    # Se exaurir todas as portas e não conectar, propaga o erro
    if ultimo_erro:
        raise ultimo_erro
    return []

# =================================================================
# TESTE ISOLADO
# =================================================================
if __name__ == "__main__":
    """ Bloco de teste manual para verificar a detecção de bancos no ambiente local. """
    try:
        load_dotenv() 
        base_teste = caminho_base()
        db_teste = encontrar_banco_base(base_teste)

        if not db_teste:
            print("Nenhum banco base encontrado.")
        else:
            portas = capturar_portas_firebird()
            # Se for banco mestre, busca a lista. Se for banco único, usa apenas ele.
            if db_teste.lower().endswith("empresa.gdb"):
                lista_bases = obter_bases(db_teste, portas)
            else:
                lista_bases = [db_teste]
            print(f"Bases encontradas para processamento: {lista_bases}")
    except Exception as e:
        print(f"Erro no teste de infraestrutura: {e}")