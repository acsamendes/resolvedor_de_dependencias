# Resolvedor de Dependências para Bibliotecas Python

## Descrição
Este projeto tem como objetivo desenvolver um resolvedor de dependências para bibliotecas Python, sugerindo os pacotes corretos para que o usuário consiga montar um ambiente virtual com versões compatíveis, sem conflitos e com informações claras sobre pacotes problemáticos.

O resolvedor analisa:
* Pacotes com versão fixa
* Intervalos e restrições de versão
* Pacotes sem versões especificadas

O sistema utiliza dados reais do PyPI e resolve dependências usando as técnicas Backtracking + Poda + Heurísticas.

---

## Arquitetura e Fluxo

Abaixo, o diagrama ilustra como o sistema processa uma requisição, desde a entrada do usuário até a resolução final das versões.

![Fluxo de Execução](arquivos_relacionados/fluxo.png)

1.  **Entrada e Validação:**
    O `main.py` recebe a requisição (`POST /resolve`) e aciona o `InputValidator`. Ele normaliza os nomes (ex: "Pandas" vira "pandas") e verifica imediatamente no banco se os pacotes existem. Se não existirem, o processo para aqui (*Fail Fast*).

2.  **Resolução:**
    O `Resolver` utiliza um algoritmo de **Backtracking**. Ele gerencia uma lista de tarefas e escolhe qual pacote resolver primeiro, tentando encontrar uma combinação válida.

3.  **Exploração:**
    O `GraphBuilder` atua como intermediário entre o Resolver e os dados. Ele consulta o banco (`db_client`), filtra versões incompatíveis (como aquelas que não suportam a versão do Python solicitada ou estão marcadas como *yanked*) e entrega apenas candidatos válidos ao Resolver.

4.  **Expansão e Decisão:**
    Ao escolher uma versão de um pacote, o Resolver pede as dependências dele. Se houver conflito entre requisitos, o sistema realiza o *backtrack* (desfaz a escolha atual e tenta a próxima versão disponível). Se a lista de tarefas for concluída sem erros, a solução é devolvida.

---

## Requisitos
* Python 3.10 ou superior
* SQLite3
* Dataset PyPI (fornecido no repositório)
* Docker e Docker Compose (para execução containerizada)

---

## Passo a Passo de Execução

Para executar o projeto, siga a ordem das etapas abaixo. O uso de um ambiente virtual é recomendado para evitar conflitos de bibliotecas no seu sistema operacional.

### 1\. Preparação do Ambiente Virtual

Antes de iniciar, crie e ative um ambiente virtual isolado para o projeto acessando o seu terminal local.

**No Windows:**

```powershell
# 1. Cria o ambiente virtual
python -m venv venv

# 2. Ativa o ambiente
.\venv\Scripts\activate

# 3. (Opcional) Se for rodar scripts locais, instale as dependências
pip install -r requirements.txt
```

**No Linux / macOS:**

```bash
# 1. Cria o ambiente virtual
python3 -m venv venv

# 2. Ativa o ambiente
source venv/bin/activate

# 3. (Opcional) Se for rodar scripts locais, instale as dependências
pip install -r requirements.txt
```

-----

### 2\. Configuração da Base de Dados

Você tem duas opções para preparar o banco de dados utilizado pelo resolvedor:

**Opção A: Execução Rápida (Recomendado)**
Se deseja iniciar a aplicação rapidamente, baixe o dataset pré-processado:

1.  Faça o download do arquivo `.zip` através deste link: [LINK DO DRIVE](https://drive.google.com/drive/folders/1ZqvOu022HgDVcafCKbKbks3cJkBscttT?usp=sharing)
2.  Extraia o arquivo `.sqlite` contido no zip.
3.  Mova o arquivo extraído para a pasta `dados` dentro do diretório do projeto.
    > **Atenção:** Mantenha exatamente o mesmo nome do arquivo (`pypi-data.sqlite`).

**Opção B: Configuração Automática (Via Script)**
Caso opte por não baixar o arquivo manualmente, a aplicação executará automaticamente um script de setup ao iniciar.

  * O sistema fará o download, descompactação e limpeza dos dados diretamente da fonte oficial.
  * **Aviso:** Este processo pode levar alguns minutos dependendo da sua velocidade de internet, pois envolve o download e processamento de um arquivo grande.

-----

### 3\. Executando a Aplicação

Certifique-se de que o **Docker Desktop** (ou Engine) esteja instalado e em execução na sua máquina.

1.  No seu terminal (com o `venv` ativado ou não, pois o Docker isola a execução), rode o comando para construir e subir os containers:
    ```bash
    docker-compose up --build
    ```
2.  A aplicação estará disponível em `http://localhost:8000`.

-----

## Links úteis

  * [Dataset PyPI](https://github.com/pypi-data/pypi-json-data/tree/main?tab=readme-ov-file)
  * [Documentação PyPI](https://pypi.org/)
  * [Tutorial sobre ambientes virtuais Python](https://docs.python.org/3/tutorial/venv.html)

<!-- end list -->


