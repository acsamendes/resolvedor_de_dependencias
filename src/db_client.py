import json
import sqlite3
import logging
from packaging.specifiers import SpecifierSet
from packaging.version import Version, InvalidVersion

logging.basicConfig(level=logging.INFO, format='%(message)s')




class DBClient:
    def __init__(self, db_path):
        """
        Inicializa o cliente do banco de dados.
        :param db_path: Caminho para o arquivo .db
        """
        self.db_path = db_path
        self.table_name = "projects"



    def get_connection(self):
        """
        Cria uma conexão com row_factory e registra a função de versão.
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        
        # REGISTRO DA FUNÇÃO: Permite usar version_match(ver, spec) no SQL
        conn.create_function("version_match", 2, self._sql_version_match)
        
        return conn



    @staticmethod
    def _sql_version_match(version, specifier):
        """
        Função auxiliar executada pelo SQLite.
        Retorna 1 se a versão atende ao specifier, 0 caso contrário.
        """
        if not specifier or specifier == "":
            return 1 # Sem restrição = compatível
        if not version:
            return 0 
            
        try:
            v = Version(str(version))
            spec = SpecifierSet(str(specifier))
            return 1 if spec.contains(v, prereleases=True) else 0
        except (InvalidVersion, ValueError):
            return 0



    def get_available_versions(self, package):
        """
        Retorna todas as versões disponíveis para um pacote.
        """
        if not package: return []

        query = f"SELECT version FROM {self.table_name} WHERE LOWER(name) = ?"
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (package.lower(),))
            rows = cursor.fetchall()
            return [row['version'] for row in rows]



    def get_dependencies(self, package, version):
        """
        Retorna a lista de dependências (requires_dist) de um pacote específico.
        """
        query = f"SELECT requires_dist FROM {self.table_name} WHERE LOWER(name) = ? AND version = ?"
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (package.lower(), version))
            row = cursor.fetchone()
            
            if row and row['requires_dist']:
                try:
                    return json.loads(row['requires_dist'])
                except json.JSONDecodeError:
                    return [row['requires_dist']]
            return []



    def version_satisfies(self, version, specifier):
        """
        Verifica se uma versão atende a um especificador.
        Mantida como utilitário para uso fora de queries.
        """
        try:
            v = Version(version)
            spec = SpecifierSet(specifier)
            return v in spec
        except InvalidVersion:
            logging.warning(f"AVISO: Versão inválida encontrada: {version}")
            return False



    def package_and_version_exists(self, package, version):
        """
        Verifica se existe pelo menos uma versão no banco que atenda ao especificador passado.
        
        Args:
            package: Nome do pacote.
            version: Agora atua como SPECIFIER (ex: "==1.0", ">=2.0").
        """
        # A query verifica:
        # 1. Se o nome do pacote bate
        # 2. Se a versão salva no banco (coluna version) satisfaz o specifier passado 
        query = f"""
            SELECT 1 
            FROM {self.table_name} 
            WHERE LOWER(name) = ? 
            AND version_match(version, ?) 
            LIMIT 1
        """
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (package.lower(), version))
            return cursor.fetchone() is not None



    def python_version_satisfies_package(self, package, version, python_version):
        """
        Verifica se uma versão específica do Python é compatível
        com o 'requires_python' definido no pacote, usando lógica SQL.
        """
        # A query agora calcula a compatibilidade diretamente no banco.
        # CASE WHEN verifica: Se for nulo/vazio -> 1 (True), senão usa a função customizada.
        query = f"""
            SELECT 
                CASE 
                    WHEN requires_python IS NULL THEN 1 
                    ELSE version_match(?, requires_python) 
                END as is_compatible
            FROM {self.table_name} 
            WHERE LOWER(name) = ?  AND version = ?
        """
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            # Note a ordem dos parâmetros: python_version primeiro (para o version_match), depois name e version
            cursor.execute(query, (python_version, package.lower(), version))
            row = cursor.fetchone()
            
            # Mantendo a lógica original: 
            # Se o pacote não existe (row is None), retorna True
            if row is None:
                return True
            
            # Retorna o resultado booleano calculado pelo SQLite (0 ou 1)
            return bool(row['is_compatible'])
        

    def is_yanked(self, package, version):
        """
        Verifica se uma versão específica de um pacote foi marcada como 'yanked' (descontinuada/removida).
        
        Args:
            package: Nome do pacote.
            version: Versão exata do pacote.
            
        Returns:
            bool: True se o pacote estiver marcado como yanked, False caso contrário.
        """
        # A query seleciona a coluna 'yanked' baseada no nome e versão exata
        query = f"SELECT yanked FROM {self.table_name} WHERE LOWER(name) = ?  AND version = ?"
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (package.lower(), version))
            row = cursor.fetchone()
            
            # Se o registro existe e a coluna yanked é verdadeira (1, True, ou string não vazia)
            if row and row['yanked']:
                return True
                
            return False