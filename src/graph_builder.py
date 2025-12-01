from packaging.specifiers import SpecifierSet
from packaging.version import Version, InvalidVersion
from packaging.requirements import Requirement




class GraphBuilder:

    def __init__(self, db_client, python_version, max_versions_per_package=None):
        """
        Responsável por expandir os nós do grafo sob demanda (Lazy Loading).
        Gerencia a obtenção de candidatos e a leitura de dependências.
        
        Args:
            db_client: Instância do DBClient.
            python_version (str): Versão do Python alvo (ex: "3.10"). Se None, modo universal.
            max_versions_per_package (int, optional): Limite de candidatos para podar busca.
        """

        self.db = db_client
        self.python_version = python_version
        self.max_versions = max_versions_per_package

        # Cria um objeto Version para comparações com marcadores de ambiente
        self.python_version_obj = Version(python_version) if python_version else None



    def get_candidate_versions(self, package_name, specifier_set=None):
        """
        Busca versões disponíveis, aplica filtros (Python, Specifier) e ordenação heurística.
        """

        # Busca versões
        raw_versions = self.db.get_available_versions(package_name)
        candidates = []

        if specifier_set is None:
            specifier_set = SpecifierSet("")

        for version_str in raw_versions:

            try:
                version_obj = Version(version_str)

            except InvalidVersion:
                continue

            # Filtro: Specifier
            if not specifier_set.contains(version_obj, prereleases=False):
                continue

            # Filtro: Compatibilidade com Python
            # Se python_version for None, aceita qualquer versão do pacote
            if self.python_version:
                if not self.db.python_version_satisfies_package(package_name, version_str, self.python_version):
                    continue

            # Metadados
            metadata = self.db.get_metadata(package_name, version_str)
            is_yanked = metadata.get('yanked', False)
            vulnerabilities = metadata.get('vulnerabilities', [])

            candidate = {
                'package': package_name,
                'version_obj': version_obj,
                'version_str': version_str,
                'is_yanked': bool(is_yanked),
                'vulnerabilities': len(vulnerabilities),
                'raw_metadata': metadata
            }
            candidates.append(candidate)

        # Ordenação
        candidates.sort(key=lambda x: x['version_obj'], reverse=True)
        candidates.sort(key=lambda x: (x['is_yanked'], x['vulnerabilities'] > 0))

        # Poda pela quantidade máxima de versões definida
        if self.max_versions and len(candidates) > self.max_versions:
            candidates = candidates[:self.max_versions]

        return candidates



    def get_dependencies(self, package_name, version_str):
        """
        Retorna as dependências de um pacote.
        Filtra apenas por versão do Python se ela estiver definida.
        """

        raw_deps_list = self.db.get_dependencies(package_name, version_str)
        cleaned_deps = []

        # Configura marcador para versão do Python
        env_markers = {}
        if self.python_version:
            env_markers["python_version"] = self.python_version
            env_markers["python_full_version"] = self.python_version 

        for raw_dep in raw_deps_list:

            try:
                req = Requirement(raw_dep)
                
                # Se houver marcadores (ex: "python_version < '3.8'")
                if req.marker:

                    # CASO 1: A versão do Python está definida 
                    if self.python_version:

                        # Avaliamos o marcador com a versão do Python fornecida
                        if not req.marker.evaluate(env_markers):
                            continue # Marcador falhou (ex: versão python incompatível), descarta
                    
                    # CASO 2: Python indefinido (Modo Universal)
                    else:
                        # Se não há a versão do Python definida, não é possível julgar marcadores de versão
                        pass

                cleaned_deps.append((req.name, req.specifier))

            except Exception:
                # Se falhar o parse, ignora a dependência por segurança
                continue

        return cleaned_deps