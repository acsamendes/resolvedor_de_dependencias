import sqlite3
import json
from packaging.specifiers import SpecifierSet
from packaging.version import Version, InvalidVersion

class DBClient:
    def __init__(self, db_path):
        """
        Inicializa o cliente do banco de dados.
        :param db_path: Caminho para o arquivo .db
        """
        self.db_path = db_path
        self.table_name = "projects"

    def get_connection(self):
        """Cria uma conexão com row_factory para facilitar o acesso."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def get_available_versions(self, package):
        """
        Retorna todas as versões disponíveis para um pacote.
        """
        query = f"SELECT version FROM {self.table_name} WHERE name = ?"
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (package,))
            rows = cursor.fetchall()
            
            # Retorna uma lista simples de strings
            return [row['version'] for row in rows]

    def get_dependencies(self, package, version):
        """
        Retorna a lista de dependências (requires_dist) de um pacote específico.
        Assume que a coluna 'requires_dist' armazena 
        JSON ou string.
        """
        query = f"SELECT requires_dist FROM {self.table_name} WHERE name = ? AND version = ?"
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (package, version))
            row = cursor.fetchone()
            
            if row and row['requires_dist']:
                try:
                    # Tenta carregar como JSON (comum em dumps do PyPI)
                    return json.loads(row['requires_dist'])
                except json.JSONDecodeError:
                    # Se não for JSON, retorna o texto cru ou trata como lista unitária
                    return [row['requires_dist']]
            return []

    def version_satisfies(self, version, specifier):
        """
        Verifica se uma versão atende a um especificador (ex: '>=1.0,~=1.5').
        Não acessa o banco, é uma função lógica utilitária.
        """
        try:
            v = Version(version)
            spec = SpecifierSet(specifier)
            return v in spec
        except InvalidVersion:
            print(f"Aviso: Versão inválida encontrada: {version}")
            return False

    def package_and_version_exists(self, package, version):
        """
        Verifica se o par pacote e versão existe no banco.
        """
        # lança o valor 1 para todas as linhas que correspondem aos valores buscados
        query = f"SELECT 1 FROM {self.table_name} WHERE name = ? AND version = ? LIMIT 1"
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (package, version))
            # Se fetchone retornar algo, ou seja, existe pelo menos uma linha em que o par existe
            return cursor.fetchone() is not None

    def python_version_satisfies_package(self, package, version, python_version):
        """
        Verifica se uma versão específica do Python é compatível
        com o 'requires_python' definido no pacote.
        """
        query = f"SELECT requires_python FROM {self.table_name} WHERE name = ? AND version = ?"
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (package, version))
            row = cursor.fetchone()
            
            # Se o pacote não especifica python, assume-se que roda em qualquer um
            if not row or not row['requires_python']:
                return True
            
            requires_python = row['requires_python']
            
            # Reutiliza a lógica de specifiers
            return self.version_satisfies(python_version, requires_python)