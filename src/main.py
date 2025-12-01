import os
import uvicorn
from typing import Dict, List, Optional
from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from packaging.specifiers import SpecifierSet

from db_client import DBClient
from input_validator import InputValidator
from graph_builder import GraphBuilder
from resolver import Resolver

DB_PATH = os.path.join("data", "pypi_data.sqlite")

# Modelo Pydantic da requisição
class ResolveRequest(BaseModel):
    python: Optional[str] = None
    fixed: Optional[Dict[str, str]] = None
    wants: Optional[List[str]] = []
    max_versions: Optional[int] = 10 

# Inicialização da Aplicação
app = FastAPI(
    title="Python Dependency Resolver",
    description="API para resolução de dependências de pacotes Python usando Backtracking e Heurísticas.",
    version="1.0.0"
)

# Singleton do Banco de Dados 
_db_client: Optional[DBClient] = None

@app.on_event("startup")
def startup_event():
    """
    Inicializa a instância do DBClient e verifica se o arquivo existe.
    """
    global _db_client

    if not os.path.exists(DB_PATH):
        print(f'AVISO CRÍTICO: Banco de dados "{DB_PATH}" não encontrado. As requisições irão falhar.')
    else:
        print(f'Banco de dados encontrado em: {DB_PATH}')
    
    _db_client = DBClient(DB_PATH)
    print('Serviço de banco de dados configurado.')

@app.on_event("shutdown")
def shutdown_event():
    """
    Fecha a conexão ao parar o servidor.
    """
    
    print('Encerrando aplicação...')

def get_db() -> DBClient:
    """
    Função de Dependência (Dependency Injection).
    Retorna a instância ativa do banco de dados para os endpoints que precisarem.
    """

    if _db_client is None:
        raise HTTPException(status_code=500, detail="Serviço de banco de dados não inicializado.")
    
    return _db_client

def prepare_requirements(input_data: dict) -> Dict[str, SpecifierSet]:
    """
    Converte o input 'fixed' e 'wants' para o formato interno do Resolver.
    """
    requirements = {}
    
    if 'fixed' in input_data and input_data['fixed']:
        
        for pkg, spec_str in input_data['fixed'].items():
            requirements[pkg] = SpecifierSet(spec_str)
            

    if 'wants' in input_data and input_data['wants']:

        for pkg in input_data['wants']:

            if pkg not in requirements:
                requirements[pkg] = SpecifierSet("")
                
    return requirements



# ENDPOINTS

@app.get("/")
def read_root():
    return {"message": "Dependency Resolver API is running. Use POST /resolve to solve dependencies."}


@app.post("/resolve")
def resolve_dependencies(request: ResolveRequest, db_client: DBClient = Depends(get_db)):
    """
    Endpoint principal.
    A injeção 'db_client: DBClient = Depends(get_db)' garante a instância correta do banco de dados será recebida automaticamente.
    """

    # Converte Pydantic para dict
    input_data = request.model_dump(exclude_none=True)
    
    # Validação Lógica
    validator = InputValidator(db_client)
    is_valid, error_msg = validator.validate(input_data)
    
    if not is_valid:
        raise HTTPException(status_code=400, detail=error_msg)


    # Configuração
    python_version = input_data.get("python")
    max_versions = input_data.get("max_versions", None)
    
    gb = GraphBuilder(
        db_client=db_client,
        python_version=python_version,
        max_versions_per_package=max_versions
    )
    
    resolver = Resolver(graph_builder=gb)

    # Execução
    try:
        reqs_map = prepare_requirements(input_data)
        
        print(f'Resolvendo para Python: {python_version}, Alvos: {list(reqs_map.keys())}')
        
        result = resolver.resolve(reqs_map)

        return result

    except Exception as e:

        import traceback

        traceback.print_exc()

        raise HTTPException(status_code=500, detail=f"Erro interno do servidor: {str(e)}")




if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)