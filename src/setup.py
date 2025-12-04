import sqlite3
import os
import sys
import time
import requests
import logging

from db_client import DBClient

# --- CONFIGURAÇÃO DE LOGS ---
# Configura para exibir no terminal (stdout) com horário e nível de severidade
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# --- CONFIGURAÇÕES ---
DB_URL = "https://github.com/pypi-data/pypi-json-data/releases/download/latest/pypi-data.sqlite.gz" 
DB_PATH = os.path.join("..", "dados", "pypi-data.sqlite")

# Colunas para remover
DROP_COLUMNS = [
    'id', 
    'description', 
    'summary', 
    'author', 
    'author_email', 
    'maintainer', 
    'maintainer_email', 
    'package_url', 
    'license', 
    'home_page',
    'project_url',
    'plataform'
]

def download_database(url, dest_path):
    """
    Baixa o arquivo da URL especificada para o caminho de destino.
    Usa stream para não sobrecarregar a memória com arquivos grandes.
    """
    logger.info("Arquivo do banco não encontrado localmente.")
    logger.info(f"Iniciando download de: {url}")
    
    # Garante que o diretório de destino existe
    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
    
    try:
        with requests.get(url, stream=True) as r:
            r.raise_for_status() # Lança erro se a URL estiver quebrada (404, 500)
            
            # Baixa para um arquivo temporário primeiro
            temp_path = dest_path + ".tmp"
            total_size = 0
            chunk_size = 8192
            log_interval = 10 * 1024 * 1024 # Log a cada 10MB
            last_log_size = 0
            
            with open(temp_path, 'wb') as f:
                for chunk in r.iter_content(chunk_size=chunk_size):
                    if chunk:
                        f.write(chunk)
                        total_size += len(chunk)
                        
                        # Log de progresso para não parecer que travou
                        if total_size - last_log_size > log_interval:
                            logger.info(f"Baixando... {total_size / (1024*1024):.2f} MB recebidos")
                            last_log_size = total_size
                        
            # Renomeia o temporário para o nome final
            os.rename(temp_path, dest_path)
            
        logger.info(f"Download concluído com sucesso! Tamanho final: {total_size / (1024*1024):.2f} MB")
        return True 
        
    except Exception as e:
        logger.error(f"Falha ao baixar o banco de dados: {e}")
        # Remove arquivo temporário se existir
        if os.path.exists(dest_path + ".tmp"):
            os.remove(dest_path + ".tmp")
        sys.exit(1)

def get_connection():
    client = DBClient(DB_PATH)
    return client.get_connection()

def get_table_columns(cursor, table_name):
    """Retorna uma lista com os nomes das colunas de uma tabela."""
    try:
        cursor.execute(f"PRAGMA table_info({table_name})")
        return [row[1] for row in cursor.fetchall()]
    except sqlite3.OperationalError:
        return []

def clean_database():
    logger.info(f"Iniciando limpeza do banco: {DB_PATH}")
    
    if os.path.exists(DB_PATH):
        logger.info(f"Tamanho inicial: {os.path.getsize(DB_PATH) / (1024*1024):.2f} MB")
    
    conn = get_connection()
    conn.isolation_level = None  # Autocommit ligado (necessário para VACUUM)
    cursor = conn.cursor()

    try:
        # 1. REMOÇÃO DE TABELA INUTILIZADA
        cursor.execute(f"DROP TABLE IF EXISTS urls")
        logger.info("Tabela 'urls' removida (se existia).")

        # 2. REMOÇÃO DE COLUNAS (DROP COLUMN)
        logger.info("--- Verificando remoção de colunas ---")
        
        table = 'projects'
        current_columns = get_table_columns(cursor, table) 
        
        if not current_columns:
            logger.error(f"Tabela '{table}' não encontrada! Verifique o banco de dados.")
            return

        cols_removed_count = 0
        for col in DROP_COLUMNS:
            if col in current_columns:
                logger.info(f"Removendo coluna '{col}' da tabela '{table}'...")
                try:
                    cursor.execute(f"ALTER TABLE {table} DROP COLUMN {col}")
                    cols_removed_count += 1
                except sqlite3.OperationalError as e:
                    logger.error(f"Erro ao remover '{col}': {e}")
        
        if cols_removed_count == 0:
            logger.info("Nenhuma coluna precisou ser removida (já estavam limpas ou não existiam).")

        # 3. SANITIZAÇÃO DE DADOS
        logger.info("--- Sanitizando dados ('' ou 'null' -> NULL) ---")
        
        cursor.execute("BEGIN TRANSACTION") 
        
        updates_total = 0
        tbl = 'projects' 
        
        cursor.execute(f"PRAGMA table_info({tbl})")
        columns_info = cursor.fetchall()
        
        for col_info in columns_info:
            col_name = col_info[1]  
            is_not_null = col_info[3]
            is_pk = col_info[5]

            # Pula colunas que não aceitam NULL ou são Chave Primária
            if is_pk or is_not_null:
                continue

            query = f"""
                UPDATE "{tbl}"
                SET "{col_name}" = NULL
                WHERE "{col_name}" = '' 
                   OR "{col_name}" IS 'null' 
            """
            cursor.execute(query)
            if cursor.rowcount > 0:
                logger.info(f" -> Tabela '{tbl}' | Coluna '{col_name}': {cursor.rowcount} registros corrigidos.")
                updates_total += cursor.rowcount
                
        # Adicionar name_lower
        # Verifica se a coluna já existe antes de tentar criar
        current_columns_updated = get_table_columns(cursor, table)
        if 'name_lower' not in current_columns_updated:
            logger.info(f"Criando coluna 'name_lower' na tabela '{table}'...")
            cursor.execute(f"ALTER TABLE {table} ADD COLUMN name_lower TEXT")
            
            logger.info("Populando 'name_lower' com valores minúsculos...")
            cursor.execute(f"UPDATE {table} SET name_lower = LOWER(name)")
        else:
            logger.info("Coluna 'name_lower' já existe.")
        
        cursor.execute("COMMIT") 
        logger.info(f"Sanitização concluída. Total de células alteradas: {updates_total}")

        # 4. VACUUM
        logger.info("--- Executando VACUUM (Otimizando espaço em disco, aguarde...) ---")
        start_time = time.time()
        cursor.execute("VACUUM")
        end_time = time.time()
        
        logger.info(f"VACUUM concluído em {end_time - start_time:.2f} segundos.")
        
        if os.path.exists(DB_PATH):
            logger.info(f"Tamanho final: {os.path.getsize(DB_PATH) / (1024*1024):.2f} MB")

    except Exception as e:
        logger.critical(f"Erro crítico durante a limpeza: {e}", exc_info=True)
        try:
            cursor.execute("ROLLBACK")
            logger.info("Rollback executado devido ao erro.")
        except:
            pass
        
def main():
    logger.info("Iniciando script de setup...")
    
    # 1. Verifica se o banco já existe
    if os.path.exists(DB_PATH):
        # Opcional: Verificar se o banco não está corrompido ou vazio (tamanho > 0)
        if os.path.getsize(DB_PATH) > 0:
            logger.info(f"✅ Banco de dados já existe em: {DB_PATH}")
            logger.info("⏩ Pulando etapa de download e limpeza.")
            return 

    # 2. Se não existe, baixa e limpa
    download_success = download_database(DB_URL, DB_PATH)
    
    if download_success:
        clean_database()
    
    logger.info("Script finalizado.")

if __name__ == "__main__":
    main()