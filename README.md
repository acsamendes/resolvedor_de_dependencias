# Resolvedor de Dependências para Bibliotecas Python

## Descrição
Este projeto tem como objetivo desenvolver um resolvedor de dependências para bibliotecas Python, garantindo que o usuário consiga montar um ambiente virtual com versões compatíveis, sem conflitos e com informações claras sobre pacotes problemáticos.

O resolvedor analisa:
* Pacotes com versão fixa
* Intervalos e restrições de versão
* Pacotes sem versões especificadas

O sistema utiliza dados reais do PyPI (através de um dataset disponibilizado em Links Úteis) e resolve dependências usando técnicas avançadas de Backtracking + Poda + Heurísticas.


## Requisitos
Para executar este projeto, você precisará ter instalado em sua máquina:

- **[Docker](https://www.docker.com/get-started)**
- **[Docker Compose](https://docs.docker.com/compose/install/)**
- Um cliente HTTP para testes ou navegador.

## Instalação
1. **Clone o repositório:**
   ```bash
   git clone https://github.com/seu-usuario/resolvedor_de_dependencias.git
   cd resolvedor_de_dependencias
2. **Configuração do Banco de Dados:** O projeto utiliza um banco de dados SQLite
 [Dataset PyPI](https://github.com/pypi-data/pypi-json-data/tree/main?tab=readme-ov-file)

3. **Subindo o Servidor:** Execute o comando para construir a imagem e iniciar o container:
   ```bash
   docker-compose up --build
  O servidor estará rodando em: http://localhost:8000

## Uso
A API expõe um endpoint principal para resolução. Devido à estrutura do projeto, os dados devem ser enviados como Form-Data.

**Endpoint:** POST /resolve

**Parâmetros do Formulário:**
* **python:** Versão do Python alvo (ex: 3.10).
* **wants:** Lista de pacotes desejados (ex: 0-core-client).
* **fixed (Opcional):** JSON string com versões travadas.
* **max_versions:** Limite de versões por pacote.

**Exemplo:**
## Links úteis
* [Dataset PyPI](https://github.com/pypi-data/pypi-json-data/tree/main?tab=readme-ov-file)
* [Documentação PyPI](https://pypi.org/)
* [Tutorial sobre ambientes virtuais Python](https://docs.python.org/3/tutorial/venv.html)







