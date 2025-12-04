import logging
from packaging.specifiers import SpecifierSet
from packaging.requirements import Requirement
from packaging.version import Version, InvalidVersion

logging.basicConfig(level=logging.INFO, format='%(message)s')




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
        logging.info(f'Versões brutas encontradas para o pacote "{package_name}": {raw_versions}')
        candidates = []

        if specifier_set is None:
            specifier_set = SpecifierSet("")

        for version in raw_versions:

            try:
                version_obj = Version(version)

            except InvalidVersion:
                logging.info(f"Versão inválida ignorada no banco: {version} do pacote {package_name}.")
                continue

            # Filtro: Specifier
            if not specifier_set.contains(version_obj, prereleases=True):
                logging.info(f"Rejeitado: {version_obj} | É Prerelease? {version_obj.is_prerelease} | Spec: {specifier_set}")
                continue

            # Filtro: Compatibilidade com Python
            # Se python_version for None, aceita qualquer versão do pacote
            if self.python_version:
                if not self.db.python_version_satisfies_package(package_name, version, self.python_version):
                    logging.info(f'Versão Python do pacote "{package_name}" na versão "{version}" não é compatível com Python {self.python_version}.')
                    continue

            # Metadados
            is_yanked = self.db.is_yanked(package_name, version)

            candidate = {
                'package': package_name.lower(),
                'version_obj': version_obj,
                'version': version,
                'is_yanked': bool(is_yanked),
            }
            candidates.append(candidate)

        # Ordenação
        candidates.sort(key=lambda x: x['version_obj'], reverse=True)
        candidates.sort(key=lambda x: x['is_yanked'])

        # Poda pela quantidade máxima de versões definida
        if self.max_versions and len(candidates) > self.max_versions:
            candidates = candidates[:self.max_versions]

        return candidates



    def get_dependencies(self, package_name, version):
        """
        Retorna as dependências de um pacote.
        Filtra apenas por versão do Python se ela estiver definida.
        """

        raw_deps_list = self.db.get_dependencies(package_name, version)
        logging.info(f'Obtidas dependências brutas para "{package_name}" na versão "{version}": {raw_deps_list}')
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

                        # O marcador com a versão do Python fornecida é avaliado
                        if not req.marker.evaluate(env_markers):
                            logging.info(f'Dependência rejeitada: "{raw_dep}". Motivo: Marcador "{req.marker}" falhou para o ambiente "{env_markers}".')
                            continue # Marcador falhou (ex: versão python incompatível), descarta
                    
                    # CASO 2: Python indefinido (Modo Universal)
                    else:
                        # Se não há a versão do Python definida, não é possível julgar marcadores de versão
                        logging.info(f'Versão do Python não definida. Aceitando dependência "{raw_dep}" do pacote "{package_name}" na versão "{version}".')
                        pass

                cleaned_deps.append((req.name.lower(), req.specifier))

            except Exception as e:
                # Se falhar o parse, ignora a dependência por segurança
                logging.error(f"ERRO DE PARSE: Não foi possível processar a dependência '{raw_dep}' do pacote '{package_name}'. Erro: '{e}'.")
                continue

        return cleaned_deps