from packaging.specifiers import SpecifierSet
from packaging.utils import canonicalize_name




class ConflictError(Exception):
    """
    Exceção personalizada para sinalizar falhas na resolução (Backtracking).
    """

    def __init__(self, message, package=None, constraint=None, parent_error=None):

        super().__init__(message)
        self.package = package
        self.constraint = constraint
        self.parent_error = parent_error




class Resolver:

    def __init__(self, graph_builder):

        self.gb = graph_builder
        # Estatísticas para debug e análise de performance
        self.stats = {"steps": 0, "backtracks": 0}



    def resolve(self, requirements_map):
        """
        Ponto de entrada do algoritmo.
        
        Args:
            requirements_map (dict): { 'pacote': SpecifierSet('>=1.0') }
                                     Pacotes iniciais solicitados (fixed + wants).
        
        Returns:
            dict: Estrutura de sucesso ou erro.
        """

        self.stats = {"steps": 0, "backtracks": 0}
        
        # Normaliza nomes de pacotes (boa prática em Python: 'Flask' == 'flask')
        normalized_reqs = {canonicalize_name(k): v for k, v in requirements_map.items()}
        
        # Estado Inicial
        assignments = {}
        
        # Restrições ativas acumuladas { 'flask': SpecifierSet('>=2.0') }
        constraints = normalized_reqs.copy()
        
        # Pacotes com restrição mas ainda sem versão definida
        todo_list = list(constraints.keys())

        try:

            solution = self._backtracking(assignments, constraints, todo_list)

            return {
                "status": "ok",
                "install_plan": self._format_solution(solution),
                "stats": self.stats
            }
        
        except ConflictError as e:

            return {
                "status": "conflict",
                "message": str(e),
                "debug_info": {
                    "package_causing_conflict": e.package,
                    "constraint_violated": str(e.constraint) if e.constraint else None
                },
                "stats": self.stats
            }



    def _backtracking(self, assignments, constraints, todo_list):
        """
        Núcleo recursivo do resolvedor.
        """

        self.stats["steps"] += 1
        
        # Se não há mais pacotes na lista 'todo', uma solução válida foi encontrada
        if not todo_list:
            return assignments


        # Escolha de qual pacote resolver agora
        package_to_solve = self._select_mrv_package(todo_list, constraints)
        
        # Remove o pacote escolhido da lista de pendências para a próxima iteração
        new_todo_list = [package for package in todo_list if package != package_to_solve]

        # Busca Candidatos
        required_spec = constraints[package_to_solve]
        candidates = self.gb.get_candidate_versions(package_to_solve, required_spec)
        
        # As restrições atuais eliminaram todas as versões possíveis do pacote atual
        if not candidates:

            self.stats["backtracks"] += 1

            raise ConflictError(
                f"Sem versões compatíveis para '{package_to_solve}' com a restrição '{required_spec}'",
                package=package_to_solve,
                constraint=required_spec
            )

        last_error = None
        
        for candidate in candidates:

            version_str = candidate['version_str']
            
            try:
                # Busca de dependências do candidato
                dependencies = self.gb.get_dependencies(package_to_solve, version_str)

                # Verificação de Compatibilidade com decisões anteriores já tomadas
                new_constraints = constraints.copy()
                new_todo_additions = []
                
                for dependency_name, dependency_specifier in dependencies:
                    dependency_name = canonicalize_name(dependency_name)
                    new_spec = SpecifierSet(dependency_specifier)
                    
                    # Checagem se o pacote dependente já foi instalado com versão incompatível
                    if dependency_name in assignments:

                        assigned_ver = assignments[dependency_name]['version_obj']

                        if not new_spec.contains(assigned_ver, prereleases=False):

                            raise ConflictError(
                                f"Conflito: {package_to_solve} {version_str} requer {dependency_name}{new_spec}, mas {dependency_name} já foi fixado em {assigned_ver}."
                            )
                    
                    # Merge de restrições
                    # Se 'A' pedia numpy>=1.0 e agora 'B' pede numpy<1.15, a nova restrição global para numpy será ">=1.0,<1.15".
                    if dependency_name in new_constraints:

                        current_spec = new_constraints[dependency_name]

                        combined_spec_str = f"{current_spec},{new_spec}"

                        new_constraints[dependency_name] = SpecifierSet(combined_spec_str)

                    else:
                        new_constraints[dependency_name] = new_spec

                        # Se é uma nova dependência ainda não resolvida, adiciona à lista de 'todo'
                        if dependency_name not in assignments:
                            new_todo_additions.append(dependency_name)


                # Recursão
                new_assignments = assignments.copy()
                new_assignments[package_to_solve] = candidate
                
                # Atualiza a lista de tarefas com as novas dependências descobertas
                next_todo = new_todo_list + [package for package in new_todo_additions if package not in new_todo_list]
                
                return self._backtracking(new_assignments, new_constraints, next_todo)

            except ConflictError as e:
                # Essa versão do candidato não serviu, tenta a próxima
                last_error = e
                continue
        
        # Se saiu do loop, nenhuma versão serviu e deve ser feito um Backtrack no nível superior
        self.stats["backtracks"] += 1

        raise ConflictError(
            f"Falha ao resolver '{package_to_solve}'. Todas as {len(candidates)} versões falharam. Último erro: {last_error}",
            parent_error=last_error
        )



    def _select_mrv_package(self, todo_list, constraints):
        """
        Aplica a heurística MRV.
        Para cada pacote na lista, pergunta ao GraphBuilder quantos candidatos existem.
        Retorna o pacote com menor número de candidatos.
        """

        best_pkg = None
        min_candidates = float('inf')
        
        for package in todo_list:

            spec = constraints.get(package, SpecifierSet(""))

            candidates = self.gb.get_candidate_versions(package, spec)
            count = len(candidates)
            
            # Se count é 0, já escolhe para falhar imediatamente (Fail-Fast)
            if count == 0:
                return package
            
            # Se count é 1, é uma escolha forçada, prioridade máxima.
            if count < min_candidates:
                min_candidates = count
                best_pkg = package
                
        return best_pkg



    def _topological_sort(self, assignments):
        """
        Ordena os pacotes tal que dependências venham antes dos dependentes.
        Usado para gerar a ordem de instalação correta.
        """

        # Constroi grafo de dependência local baseado na solução encontrada
        graph = {package: set() for package in assignments}
        
        for package, data in assignments.items():

            version_str = data['version_str']

            # Re-consulta as dependências da versão ESCOLHIDA
            deps = self.gb.get_dependencies(package, version_str)
            
            for dependency_name, _ in deps:

                dependency_name = canonicalize_name(dependency_name)

                # A dependência só entra no grafo se ela faz parte da solução 
                if dependency_name in graph:

                    # Para instalação: dependency_name deve vir antes de package
                    graph[package].add(dependency_name)

        visited = set()
        temp_visited = set()
        order = []

        def visit(node):

            if node in visited:
                return
            
            if node in temp_visited:
                # Ciclo detectado
                return
            
            temp_visited.add(node)
            
            # Visita dependências primeiro
            for dependency in graph[node]:
                visit(dependency)
            
            temp_visited.remove(node)
            visited.add(node)
            order.append(node)

        # Itera sobre todos os nós
        for package in assignments:
            visit(package)
            
        return order

    def _format_solution(self, assignments):
        """
        Formata a solução aplicando a ordenação topológica.
        """

        # Obtém a ordem correta de instalação
        install_order = self._topological_sort(assignments)
        
        plan = []

        for package_name in install_order:

            data = assignments[package_name]

            plan.append({
                "package": package_name,
                "version": data['version_str'],
                "yanked": data['is_yanked'],
                "vulnerabilities": data['vulnerabilities']
            })

        return plan