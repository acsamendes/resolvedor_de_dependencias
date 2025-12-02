# Resolvedor de Dependências para Bibliotecas Python

## Descrição
Este projeto implementa um resolvedor de dependências para bibliotecas Python, utilizando dados oficiais do repositório PyPI.

O resolvedor analisa:
* Versões fixas (ex.: numpy==2.2.7, numpy<=2.2)
* Intervalos de versões (ex.: >=1.0, <=2.1)
* Pacotes sem versão especificada

Com essas informações, o sistema determina automaticamente um conjunto de versões compatíveis, garantindo que não haja conflito entre dependências.

Quando não há solução, fornece um diagnóstico completo do conflito, incluindo sugestões.

Trabalho Final da Disciplina de AED2 com aplicação de Grafos. 

## Instalação



