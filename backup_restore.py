import subprocess
import os
from datetime import datetime
import sys
from dotenv import load_dotenv

def resource_path(relative_path):
    """ Retorna o caminho correto para arquivos embutidos no EXE """
    if hasattr(sys, '_MEIPASS'):
        # Caminho da pasta temporária do PyInstaller
        return os.path.join(sys._MEIPASS, relative_path)
    # Caminho em modo de desenvolvimento (script .py)
    return os.path.join(os.path.abspath("."), relative_path)

# Localiza e carrega o .env embutido
caminho_env = resource_path(".env")

if os.path.exists(caminho_env):
    load_dotenv(caminho_env)
else:
    # Caso o arquivo não exista nem no pacote
    raise Exception("Erro crítico: Arquivo .env não foi embutido no executável.")

# Agora sim, pegamos as variáveis
FTP_HOST = os.getenv("FTP_HOST")
FTP_USER = os.getenv("FTP_USER")
FTP_PASS_PREFIX = os.getenv("FTP_PASS_PREFIX")
FB_USER = os.getenv("FB_USER")
FB_PASS = os.getenv("FB_PASS")

# Verifica se os valores foram preenchidos
if not all([FB_USER, FB_PASS, FTP_HOST, FTP_USER, FTP_PASS_PREFIX]):
    print(f"DEBUG: FTP_HOST={FTP_HOST}, FB_USER={FB_USER}") # Isso te ajuda a ver qual está vindo vazio
    raise Exception("Variáveis de ambiente encontradas, mas estão vazias no .env")

from encontrar_gbak import gbak_path
from emcontrar_caminho import caminho_base, encontrar_banco_base, capturar_portas_firebird, obter_bases
import os
import fdb
import re 
import shutil
import ftplib
from interface import mostrar_loading
from log import configurar_logger

log = configurar_logger()

log.info("INICIANDO PROCESSO DE BACKUP FIREBIRD")


# Define o caminho base
base = caminho_base()

# Procura banco EMPRESA.GDB ou GESTAO.FDB
empresa_db = encontrar_banco_base(base)

if not empresa_db:
    raise Exception("Nenhum banco base encontrado (EMPRESA.GDB ou GESTAO.FDB)")

# Captura portas Firebird disponíveis
portas_firebird = capturar_portas_firebird()

# Agora chama obter_bases corretamente
if empresa_db.lower().endswith("empresa.gdb"):
    bases = obter_bases(empresa_db, portas_firebird)


else:
    # Se for GESTAO.FDB, só coloca na lista
    bases = [empresa_db]

log.info(f"Bases encontradas: {bases}")


PASTA_RAIZ = "backup_mercosistem"
PASTA_BACKUP = os.path.join(PASTA_RAIZ, "backup")
PASTA_RESTORE = os.path.join(PASTA_RAIZ, "restore")

os.makedirs(PASTA_BACKUP, exist_ok=True)
os.makedirs(PASTA_RESTORE, exist_ok=True)

def matar_atualizador():
    try:
        log.info("Tentando finalizar processo atualizador.exe")
        si = subprocess.STARTUPINFO()
        si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        si.wShowWindow = subprocess.SW_HIDE
        
        subprocess.run(
            ["taskkill", "/F", "/IM", "atualizador.exe"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
            startupinfo=si # Oculta o CMD do taskkill
        )
    except Exception as e:
        log.warning("Não foi possível finalizar atualizador.exe", exc_info=True)

def buscar_cod_empresa(dsn):
    conn = fdb.connect(
    dsn=dsn,
    user=FB_USER,
    password=FB_PASS
    )

    cur = conn.cursor()
    cur.execute("SELECT FIRST 1 NUMSERIE FROM EMPRESA")
    row = cur.fetchone()
    conn.close()

    if row and row[0]:
        codigo = re.sub(r"[^0-9\-]", "", str(row[0]))
        return codigo
    return None

def compactar_fdb(fdb_file):
    zip_name = fdb_file.replace(".FDB", ".zip")

    shutil.make_archive(
        zip_name.replace(".zip", ""),
        "zip",
        root_dir=os.path.dirname(fdb_file),
        base_dir=os.path.basename(fdb_file)
    )

    return zip_name

def enviar_ftp(zip_name, codigo_empresa):
    try:
        log.info(f"Iniciando envio FTP para empresa {codigo_empresa}")
        senha = FTP_PASS_PREFIX + datetime.now().strftime("%d%m%y")

        ftp = ftplib.FTP(FTP_HOST)
        ftp.login(FTP_USER, senha)

        pasta = f"/ENTRADAS/{codigo_empresa}"
        try:
            ftp.mkd(pasta)
        except:
            pass  

        ftp.cwd(pasta)

        with open(zip_name, "rb") as arq:
            ftp.storbinary(f"STOR {os.path.basename(zip_name)}", arq)

        ftp.quit()
        log.info("Envio FTP concluído com sucesso")


    except Exception as e:
        log.error(
            f"Erro ao enviar FTP (empresa {codigo_empresa})",
            exc_info=True
        )

def rodar_backup():
    

    log.info(f"GBak localizado em: {gbak_path}")
    log.info(f"Total de bases encontradas: {len(bases)}") 
    if not gbak_path:
        log.critical("GBAK NÃO ENCONTRADO - PROCESSO ABORTADO")
        raise Exception("gbak.exe não encontrado")
    for dsn in bases:
        try:
            nome_base = os.path.basename(dsn.split(":")[-1]).replace(".FDB", "")
            data = datetime.now().strftime("%Y%m%d_%H%M%S")

            cod_empresa = buscar_cod_empresa(dsn) or "SEM_CODIGO"

            nome_arquivo = f"{nome_base}_{cod_empresa}_{data}"

            fbk = os.path.join(PASTA_BACKUP, f"{nome_arquivo}.fbk")
            fdb_restore = os.path.join(PASTA_RESTORE, f"{nome_arquivo}.FDB")

            log.info(f"Iniciando processamento da base: {dsn}")
            cod_empresa = buscar_cod_empresa(dsn)
            log.info(f"Código da empresa identificado: {cod_empresa}")
            if not cod_empresa:
                log.warning("Código da empresa NÃO encontrado")

            log.info("Iniciando BACKUP")
            si = subprocess.STARTUPINFO()
            si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            si.wShowWindow = subprocess.SW_HIDE
            subprocess.run([
                gbak_path, "-b", "-g", "-ig", "-l",
                "-user", FB_USER,
                "-password", FB_PASS,
                dsn, fbk
            ], check=True, startupinfo=si)
            log.info(f"Backup criado com sucesso: {fbk}")
            


            log.info("Iniciando RESTORE")
            subprocess.run([
                gbak_path, "-r", "-p", "4096",
                "-user", FB_USER,
                "-password", FB_PASS,
                fbk, fdb_restore
            ], check=True, startupinfo=si)
            log.info(f"Restore concluído: {fdb_restore}")

            log.info("Iniciando compactação do FDB")
            zip_fdb = compactar_fdb(fdb_restore)
            os.remove(fdb_restore)
            enviar_ftp(zip_fdb, cod_empresa)
            log.info(f"OK: {nome_arquivo}")
            log.info(f"Arquivo ZIP gerado: {zip_fdb}")

        except Exception as e:
            log.error(f" Erro em {dsn}: {e}")
        except subprocess.CalledProcessError as e:
            log.error("Erro no BACKUP", exc_info=True)
            raise
        


            

if __name__ == "__main__":
    matar_atualizador()
    mostrar_loading(rodar_backup)
    log.info("PROCESSO DE BACKUP FINALIZADO")
