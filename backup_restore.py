import subprocess
import os
from datetime import datetime
import sys
from dotenv import load_dotenv

# --- GERENCIAMENTO DE RECURSOS ---
def resource_path(relative_path):
    """ 
    Ajusta o caminho dos arquivos (como o .env) para que funcionem 
    tanto rodando o script .py quanto rodando o executável (.exe) gerado pelo PyInstaller.
    """
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

# Carrega as variáveis de ambiente sensíveis (senhas e hosts)
caminho_env = resource_path(".env")
if os.path.exists(caminho_env):
    load_dotenv(caminho_env)
else:
    raise Exception("Erro crítico: Arquivo .env não encontrado.")

# Captura das credenciais via variáveis de ambiente
FTP_HOST = os.getenv("FTP_HOST")
FTP_USER = os.getenv("FTP_USER")
FTP_PASS_PREFIX = os.getenv("FTP_PASS_PREFIX")
FB_USER = os.getenv("FB_USER")
FB_PASS = os.getenv("FB_PASS")

# Importações de módulos locais do projeto
from encontrar_gbak import gbak_path
from emcontrar_caminho import caminho_base, encontrar_banco_base, capturar_portas_firebird, obter_bases
import fdb
import re 
import shutil
import ftplib
from interface import mostrar_loading
from log import configurar_logger

log = configurar_logger()

# --- PREPARAÇÃO DO AMBIENTE ---
# Define bases e pastas onde os arquivos temporários de backup serão gerados
base = caminho_base()
empresa_db = encontrar_banco_base(base)

if not empresa_db:
    raise Exception("Nenhum banco base encontrado (EMPRESA.GDB ou GESTAO.FDB)")

portas_firebird = capturar_portas_firebird()

bases = obter_bases(empresa_db, portas_firebird) if empresa_db.lower().endswith("empresa.gdb") else [empresa_db]

PASTA_RAIZ = "backup_mercosistem"
PASTA_BACKUP = os.path.join(PASTA_RAIZ, "backup")
PASTA_RESTORE = os.path.join(PASTA_RAIZ, "restore")

os.makedirs(PASTA_BACKUP, exist_ok=True)
os.makedirs(PASTA_RESTORE, exist_ok=True)
log.info(f"Pasta de backup: {PASTA_BACKUP}")
log.info(f"Pasta de restore: {PASTA_RESTORE}")

# --- FUNÇÕES AUXILIARES ---
def matar_atualizador():
    """ Encerra processos que podem travar o acesso exclusivo ao banco de dados. """
    try:
        si = subprocess.STARTUPINFO()
        si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        si.wShowWindow = subprocess.SW_HIDE # Roda o taskkill sem abrir janela de CMD
        subprocess.run(["taskkill", "/F", "/IM", "atualizador.exe"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False, startupinfo=si)
    except Exception as e:
        log.warning("Não foi possível finalizar atualizador.exe")

def buscar_cod_empresa(dsn):
    """ Conecta ao banco Firebird para buscar o número de série da empresa (usado no nome do arquivo). """
    conn = fdb.connect(dsn=dsn, user=FB_USER, password=FB_PASS)
    cur = conn.cursor()
    cur.execute("SELECT FIRST 1 NUMSERIE FROM EMPRESA")
    row = cur.fetchone()
    conn.close()
    log.info(f"Código da empresa encontrado: {row[0] if row and row[0] else 'N/A'}")
    return re.sub(r"[^0-9\-]", "", str(row[0])) if row and row[0] else None

def compactar_fdb(fdb_file):
    """ Compacta o banco restaurado em formato ZIP para economizar banda no upload FTP. """
    zip_name = fdb_file.replace(".FDB", ".zip")
    shutil.make_archive(zip_name.replace(".zip", ""), "zip", root_dir=os.path.dirname(fdb_file), base_dir=os.path.basename(fdb_file))
    return zip_name

def enviar_ftp(zip_name, codigo_empresa):
    """ Realiza o upload do arquivo compactado para o servidor FTP da empresa. """
    try:
        senha = FTP_PASS_PREFIX + datetime.now().strftime("%d%m%y")
        ftp = ftplib.FTP(FTP_HOST)
        ftp.login(FTP_USER, senha)
        pasta = f"/ENTRADAS/{codigo_empresa}"
        try: ftp.mkd(pasta) 
        except: pass  
        ftp.cwd(pasta)
        with open(zip_name, "rb") as arq:
            ftp.storbinary(f"STOR {os.path.basename(zip_name)}", arq)
        ftp.quit()
    except Exception as e:
        log.error(f"Erro ao enviar FTP (empresa {codigo_empresa})", exc_info=True)

# --- FLUXO PRINCIPAL ---
def rodar_backup():
    """ 
    Executa o ciclo completo: 
    1. Backup (.fbk) -> 2. Restore (.fdb) -> 3. Compactação (.zip) -> 4. Upload FTP 
    """
    for dsn in bases:
        try:
            log.info(f"Iniciando processamento da base: {dsn}")
            # Configuração de nomes de arquivos com timestamp
            nome_base = os.path.basename(dsn.split(":")[-1]).replace(".FDB", "")
            data = datetime.now().strftime("%Y%m%d_%H%M%S")
            cod_empresa = buscar_cod_empresa(dsn) or "SEM_CODIGO"
            nome_arquivo = f"{nome_base}_{cod_empresa}_{data}"
            fbk = os.path.join(PASTA_BACKUP, f"{nome_arquivo}.fbk")
            fdb_restore = os.path.join(PASTA_RESTORE, f"{nome_arquivo}.FDB")

            si = subprocess.STARTUPINFO()
            si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            si.wShowWindow = subprocess.SW_HIDE

            
            # Execução do GBAK para Backup
            log.info(f"Executando GBAK Backup para: {fbk}")
            subprocess.run([gbak_path, "-b", "-g", "-ig", "-l", "-user", FB_USER, "-password", FB_PASS, dsn, fbk], check=True, startupinfo=si)
            log.info("Backup físico (.fbk) gerado com sucesso.")
            # Execução do GBAK para Restore (Validação da integridade do backup)
            log.info(f"Iniciando Restore de validação em: {fdb_restore}")
            subprocess.run([gbak_path, "-r", "-p", "4096", "-user", FB_USER, "-password", FB_PASS, fbk, fdb_restore], check=True, startupinfo=si)
            log.info("Restore de validação concluído. Banco íntegro.")


            # Preparação e envio do arquivo 
            log.info("Compactando banco restaurado para formato ZIP...")
            zip_fdb = compactar_fdb(fdb_restore)
            os.remove(fdb_restore) # Remove o FDB temporário para poupar espaço
            log.info(f"Compactação finalizada: {zip_fdb}")
            log.info(f"Enviando arquivo para o FTP da empresa {cod_empresa}...")
            enviar_ftp(zip_fdb, cod_empresa)
            log.info("Upload concluído!")
        except Exception as e:
            log.error(f" Erro no processamento da base {dsn}: {e}")

if __name__ == "__main__":
    log.info("Finalizando o Atualizador.exe antes de iniciar o backup...")
    matar_atualizador()
    log.info("Atualizador finalizado.")
    log.info("INICIANDO PROCESSO DE BACKUP")
    mostrar_loading(rodar_backup) # Chama a interface visual enquanto processa
    log.info("PROCESSO DE BACKUP FINALIZADO")