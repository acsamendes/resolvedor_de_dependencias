# Resolvedor de Dependências para Bibliotecas Python

## Descrição
Este projeto tem como objetivo desenvolver um resolvedor de dependências para bibliotecas Python, sugerindo os pacotes corretos para que o usuário consiga montar um ambiente virtual com versões compatíveis, sem conflitos e com informações claras sobre pacotes problemáticos.

O resolvedor analisa:
* Pacotes com versão fixa
* Intervalos e restrições de versão
* Pacotes sem versões especificadas

O sistema utiliza dados reais do PyPI e resolve dependências usando as técnicas Backtracking + Poda + Heurísticas.

## Requisitos
* Python 3.10 ou superior
* SQLite3
* Dataset PyPI (fornecido no repositório)
* Docker e Docker Compose (para execução containerizada)

---

## 🚀 Passo a Passo de Execução

Para executar o projeto, você pode escolher entre utilizar uma base de dados pré-processada (execução rápida) ou construir a base do zero. Siga as instruções abaixo:

### 1. Configuração da Base de Dados

**Opção A: Execução Rápida (Recomendado)**
Se deseja iniciar a aplicação rapidamente, baixe a base de dados pré-processada:
1. Faça o download do arquivo `.zip` através deste link: [LINK DO DRIVE](https://drive.google.com/file/d/1T1WzNvzJyqBZuJnS4jZLl7A-I7siFdjE/view?usp=sharing)
2. Extraia o arquivo `.sqlite` contido no zip.
3. Mova o arquivo extraído para a pasta `data` dentro do diretório do projeto.
   > **Atenção:** Mantenha exatamente o mesmo nome do arquivo `.sqlite` extraído.

**Opção B: Configuração Completa (Via Script)**
Caso opte por não baixar o arquivo `.zip`, a aplicação executará automaticamente um script de setup.
* O sistema fará a busca e limpeza dos dados diretamente da fonte.
* **Aviso:** Este processo leva em média **22 minutos** para ser concluído.

### 2. Executando a Aplicação

Certifique-se de que o **Docker Desktop** esteja instalado e em execução na sua máquina.

1. No seu terminal (ambiente), execute o comando para construir e subir os containers:
   ```bash
   docker-compose up --build

**Exemplo:**

## Links úteis
* [Dataset PyPI](https://github.com/pypi-data/pypi-json-data/tree/main?tab=readme-ov-file)
* [Documentação PyPI](https://pypi.org/)
* [Tutorial sobre ambientes virtuais Python](https://docs.python.org/3/tutorial/venv.html)








