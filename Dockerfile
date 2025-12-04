# Use uma versão compatível com o projeto (documento cita Python 3.10 no exemplo) [cite: 41]
FROM python:3.10-slim

WORKDIR /app

# Instala dependências do sistema se necessário
RUN apt-get update && rm -rf /var/lib/apt/lists/*

# Copia os requirements e instala
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia o código fonte do projeto
COPY . .
