import sqlite3
import os
import sys
import time
import requests
import logging
import gzip
import shutil
from db_client import DBClient

# --- CONFIGURAÇÃO DE LOGS ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# --- CONFIGURAÇÕES ---
DB_URL = "https://github.com/pypi-data/pypi-json-data/releases/download/latest/pypi-data.sqlite.gz"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "..", "dados", "pypi-data.sqlite")

# Colunas para remover
DROP_COLUMNS = [
    'id', 'description', 'summary', 'author', 'author_email', 
    'maintainer', 'maintainer_email', 'package_url', 'license', 
    'home_page', 'project_url', 'plataform'
]

def download_and_stream_extract(url, dest_path):
    """
    Técnica de Streaming:
    Conecta o stream de download (requests) diretamente no descompactador (gzip)
    e escreve no disco apenas o arquivo final.
    """
    logger.info("Arquivo não encontrado. Iniciando Download + Descompactação em Stream...")
    logger.info(f"Origem: {url}")
    
    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
    
    # Arquivo temporário para garantir que se falhar no meio, não fique um sqlite corrompido
    temp_path = dest_path + ".tmp"
    
    start_time = time.time()
    
    try:
        with requests.get(url, stream=True) as r:
            r.raise_for_status()
            
            # Aqui está a mágica: Passamos o socket bruto (raw) para o GzipFile.
            # O Python vai baixando, descompactando na RAM e escrevendo no disco em chunks.
            with gzip.GzipFile(fileobj=r.raw) as f_in:
                with open(temp_path, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
        
        # Se chegou aqui, deu tudo certo. Renomeia para o oficial.
        os.rename(temp_path, dest_path)
        
        duration = time.time() - start_time
        final_size = os.path.getsize(dest_path) / (1024*1024)
        logger.info(f"Download e Extração concluídos em {duration:.2f}s! Tamanho final: {final_size:.2f} MB")
        return True

    except Exception as e:
        logger.error(f"Erro no streaming: {e}")
        if os.path.exists(temp_path):
            os.remove(temp_path)
        sys.exit(1)

def get_connection():
    client = DBClient(DB_PATH)
    conn = client.get_connection()
    # Otimizações de performance do SQLite para operações em lote
    conn.execute("PRAGMA journal_mode = OFF") # Arriscado em prod, mas ótimo para setup inicial
    conn.execute("PRAGMA synchronous = 0")    # Escreve sem esperar confirmação do disco (muito mais rápido)
    conn.execute("PRAGMA cache_size = 100000") # Usa mais RAM para cache
    return conn

def get_table_columns(cursor, table_name):
    try:
        cursor.execute(f"PRAGMA table_info({table_name})")
        return [row[1] for row in cursor.fetchall()]
    except sqlite3.OperationalError:
        return []

def clean_database():
    logger.info(f"Iniciando limpeza e otimização do banco...")
    
    conn = get_connection()
    conn.isolation_level = None # Autocommit para comandos como VACUUM
    cursor = conn.cursor()

    try:
        # Remoção rápida de tabela
        cursor.execute(f"DROP TABLE IF EXISTS urls")

        # Remoção de Colunas
        table = 'projects'
        current_columns = get_table_columns(cursor, table)
        
        if not current_columns:
            logger.error("Tabela projects não encontrada.")
            return

        # Dica: Em SQLite, DROP COLUMN pode ser lento pois ele recria a tabela internamente.
        # Mas vamos manter o padrão por enquanto.
        cols_to_drop = [c for c in DROP_COLUMNS if c in current_columns]
        
        if cols_to_drop:
            logger.info(f"Removendo {len(cols_to_drop)} colunas...")
            for col in cols_to_drop:
                cursor.execute(f"ALTER TABLE {table} DROP COLUMN {col}")

        # Sanitização e Coluna Lower
        # Vamos fazer tudo em uma transação única para ser atômico e rápido
        cursor.execute("BEGIN TRANSACTION")
        
        # Adiciona coluna se não existir
        current_columns = get_table_columns(cursor, table)
        if 'name_lower' not in current_columns:
            logger.info("Criando coluna auxiliar 'name_lower'...")
            cursor.execute(f"ALTER TABLE {table} ADD COLUMN name_lower TEXT")
            # Update massivo otimizado
            logger.info("Populando 'name_lower'...")
            cursor.execute(f"UPDATE {table} SET name_lower = LOWER(name)")
        
        cursor.execute("COMMIT")
        
        # VACUUM é pesado, mas necessário para reduzir o tamanho do arquivo
        logger.info("Executando VACUUM final...")
        cursor.execute("VACUUM")
        
        logger.info("Limpeza finalizada.")

    except Exception as e:
        logger.critical(f"Erro na limpeza: {e}")
        try:
            cursor.execute("ROLLBACK")
        except:
            pass
        # Não damos exit aqui para não travar o boot se for erro SQL menor

def main():
    # Validação rápida de integridade
    if os.path.exists(DB_PATH):
        try:
            conn = sqlite3.connect(DB_PATH)
            conn.execute("SELECT 1 FROM projects LIMIT 1")
            conn.close()
            logger.info(f"✅ Banco válido encontrado: {DB_PATH}")
            return
        except Exception:
            logger.warning("Arquivo corrompido detectado. Recomeçando...")
            os.remove(DB_PATH)

    # Processo de setup
    if download_and_stream_extract(DB_URL, DB_PATH):
        clean_database()

if __name__ == "__main__":
    main()