import logging
import re
from packaging.specifiers import SpecifierSet, InvalidSpecifier

logging.basicConfig(level=logging.INFO, format='%(message)s')

class InputValidator:

    def __init__(self, db_client):
        """
        Inicializa o validador com uma instancia do cliente de banco de dados
        para verificar a existencia dos pacotes.
        """

        self.db_client = db_client

    def validate(self, input_data):
        """
        Valida o JSON de entrada.
        
        Args:
            input_data (dict): O dicionário contendo 'python', 'fixed' e 'wants'.

        Returns:
            tuple: (is_valid (bool), error_message (str ou None))
        """
        
        # Validação Estrutural Básica
        if not isinstance(input_data, dict):
            return False, 'O input deve ser um objeto JSON (dicionário).'


        # Chaves permitidas
        allowed_keys = {'python', 'fixed', 'wants', 'max_versions'}
        unknown_keys = set(input_data.keys()) - allowed_keys
        if unknown_keys:
            return False, f'Chaves desconhecidas encontradas no input: {unknown_keys}.'


        # Validação da Versão do Python
        if 'python' in input_data:

            python_version = input_data['python']

            if not isinstance(python_version, str):
                return False, 'O campo "python" deve ser uma string (ex: "3.10").'
            
            # Validação simples de formato X.Y ou X.Y.Z
            if not re.match(r'^\d+\.\d+(\.\d+)?$', python_version):
                return False, f'Formato de versão Python inválido: "{python_version}". Use X.Y ou X.Y.Z.'


        # Validação de Pacotes Fixos ('fixed')
        if 'fixed' in input_data:

            fixed_deps = input_data['fixed']

            if not isinstance(fixed_deps, dict):
                return False, 'O campo "fixed" deve ser um dicionário {"pacote": "versão"}.'

            for package, version_spec in fixed_deps.items():

                # Valida nome do pacote
                if not self._is_valid_package_name(package):
                    return False, f'Nome de pacote inválido em "fixed": "{package}".'

                # Valida sintaxe do especificador (ex: ">=1.0,<=2.0") antes de chamar o banco
                if not self._is_valid_specifier(version_spec):
                    return False, f'Especificador de versão inválido para "{package}": "{version_spec}".'

                # Valida existência no DB passando o nome e a versão/restrição
                if not self.db_client.package_and_version_exists(package, version_spec):
                    return False, f'O pacote "{package}" com a versão/restrição "{version_spec}" não foi encontrado ou não é válido no banco de dados.'


        # Validação de Pacotes Desejados ('wants')
        if 'wants' in input_data:

            wants_deps = input_data['wants']

            if not isinstance(wants_deps, list):
                return False, 'O campo "wants" deve ser uma lista de strings.'
            
            logging.info(f'Validating wants: {wants_deps}')

            for item in wants_deps:

                if not isinstance(item, str):
                    return False, 'Os itens em "wants" devem ser nomes de pacotes (strings).'

                package_name = item
                
                if not self._is_valid_package_name(package_name):
                    return False, f'Nome de pacote inválido em "wants": "{package_name}".'

                if not self.db_client.package_and_version_exists(package_name, None):
                    return False, f'O pacote "{package_name}" listado em "wants" não foi encontrado no banco de dados.'


        # Verifica se um pacote está em 'fixed' E em 'wants' ao mesmo tempo (o que seria redundante ou conflitante)
        if 'fixed' in input_data and 'wants' in input_data:

            fixed_keys = set(input_data['fixed'].keys())
            wants_set = set(input_data['wants'])

            intersection = fixed_keys.intersection(wants_set)

            if intersection:
                return False, f'Pacotes não podem estar em "fixed" e "wants" simultaneamente: {intersection}.'

        return True, None

    def _is_valid_package_name(self, name):
        """
        Verifica se o nome do pacote segue regras básicas (alfanumérico, -, _, .).
        """
        return re.match(r'^[A-Za-z0-9_\-\.]+$', name) is not None

    def _is_valid_specifier(self, spec_str):
        """
        Verifica se a string de versão é válida.
        Aceita: "==1.0", ">=1.2, <2.0", "*", etc.
        """
        if spec_str == '*' or spec_str == '':
            return True
        
        try:
            SpecifierSet(spec_str)
            return True
        
        except InvalidSpecifier:
            return False