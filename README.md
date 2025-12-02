# Resolvedor de Dependências para Bibliotecas Python

## Descrição
Este projeto tem como objetivo desenvolver um resolvedor de dependências para bibliotecas Python, garantindo que o usuário consiga montar um ambiente virtual com versões compatíveis, sem conflitos e com informações claras sobre pacotes problemáticos.

O resolvedor analisa:
* Pacotes com versão fixa
* Intervalos e restrições de versão
* Pacotes sem versões especificadas

O sistema utiliza dados reais do PyPI (através de um dataset disponibilizado em Links Úteis) e resolve dependências usando técnicas avançadas de Backtracking + Poda + Heurísticas.


## Requisitos
* Python 3.10 ou superior
* SQLite3
* Dataset PyPI (fornecido no repositório)
* Bibliotecas Python

## Links úteis
* [Dataset PyPI](https://github.com/pypi-data/pypi-json-data/tree/main?tab=readme-ov-file)
* [Documentação PyPI](https://pypi.org/)
* [Tutorial sobre ambientes virtuais Python](https://docs.python.org/3/tutorial/venv.html)






