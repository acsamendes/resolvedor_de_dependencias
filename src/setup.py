import sqlite3
import os
import sys
import time
import requests

from resolvedor_de_dependencias.src.db_client import DBClient

# --- CONFIGURAÇÕES ---
DB_URL = "https://github.com/pypi-data/pypi-json-data/releases/download/latest/pypi-data.sqlite.gz" 
DB_PATH = os.path.join("data", "pypi-data.sqlite")

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
    print(f"Arquivo do banco não encontrado.")
    print(f"Iniciando download de: {url}")
    
    try:
        with requests.get(url, stream=True) as r:
            r.raise_for_status() # Lança erro se a URL estiver quebrada (404, 500)
            
            # Baixa para um arquivo temporário primeiro para evitar corromper o oficial
            temp_path = dest_path + ".tmp"
            total_size = 0
            
            with open(temp_path, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        total_size += len(chunk)
                        
            # Renomeia o temporário para o nome final apenas se deu tudo certo
            os.rename(temp_path, dest_path)
            
        print(f"Download concluído com sucesso! Tamanho: {total_size / (1024*1024):.2f} MB")
        
    except Exception as e:
        print(f"\n[ERRO] Falha ao baixar o banco de dados: {e}")
        # Remove arquivo temporário se existir
        if os.path.exists(dest_path + ".tmp"):
            os.remove(dest_path + ".tmp")
        sys.exit(1) # Encerra o programa pois não dá para continuar sem banco

def get_connection():
    """
    Verifica se o banco existe. Se não, baixa. Retorna a conexão.
    """
    if not os.path.exists(DB_PATH):
        # Chama a função de download definida acima
        download_database(DB_URL, DB_PATH)
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
    print(f"Iniciando limpeza do banco: {DB_PATH}")
    if os.path.exists(DB_PATH):
        print(f"Tamanho inicial: {os.path.getsize(DB_PATH) / (1024*1024):.2f} MB")
    
    conn = get_connection()
    conn.isolation_level = None  # Autocommit ligado (necessário para VACUUM)
    cursor = conn.cursor()

    try:
        # 1. REMOÇÃO DE TABELA INUTILIZADA
        cursor.execute(f"DROP TABLE IF EXISTS urls")
        print(f"Tabela 'urls' removida.")

        # 2. REMOÇÃO DE COLUNAS (DROP COLUMN)
        print("\n--- Verificando remoção de colunas ---")
        
        table = 'projects'
        # Função auxiliar que você já tem
        current_columns = get_table_columns(cursor, table) 
        
        for col in DROP_COLUMNS:
            if col in current_columns:
                print(f"Removendo coluna '{col}' da tabela '{table}'...")
                try:
                    cursor.execute(f"ALTER TABLE {table} DROP COLUMN {col}")
                except sqlite3.OperationalError as e:
                    print(f"  Erro ao remover '{col}': {e}")

        # 3. SANITIZAÇÃO DE DADOS (Transformar '' e 'null' em NULL real)
        print("\n--- Sanitizando dados ('' ou 'null' -> NULL) ---")
        
        # Iniciamos uma transação manual para performance, pois o autocommit está ligado
        cursor.execute("BEGIN TRANSACTION") 
        
        updates_total = 0

        tbl = 'projects'  # Foco apenas na tabela 'projects' para sanitização
        print(f"Sanitizando tabela '{tbl}'...")
        # Pega info atualizada das colunas (PRAGMA retorna: cid, name, type, notnull, dflt, pk)
        cursor.execute(f"PRAGMA table_info({tbl})")
        columns_info = cursor.fetchall()
        
        for col_info in columns_info:
            # Se estiver usando row_factory, adapte os índices abaixo ou use chaves
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
                print(f"  -> Tabela '{tbl}' | Coluna '{col_name}': {cursor.rowcount} corrigidos.")
                updates_total += cursor.rowcount
        
        cursor.execute("COMMIT") # Salva todas as alterações de dados
        print(f"Sanitização concluída. Total de células alteradas: {updates_total}")


        # 4. VACUUM (Reescreve o banco do zero)
        print("\n--- Executando VACUUM (Isso pode demorar alguns minutos) ---")
        start_time = time.time()
        cursor.execute("VACUUM")
        end_time = time.time()
        
        print(f"VACUUM concluído em {end_time - start_time:.2f} segundos.")
        
        if os.path.exists(DB_PATH):
            print(f"Tamanho final: {os.path.getsize(DB_PATH) / (1024*1024):.2f} MB")

    except Exception as e:
        print(f"Erro crítico durante a limpeza: {e}")
        # Tenta desfazer alterações de dados se der erro antes do commit
        try:
            cursor.execute("ROLLBACK")
        except:
            pass

if __name__ == "__main__":
    clean_database()