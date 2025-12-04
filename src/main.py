import json
import logging
import os
import uvicorn
from typing import Dict, List, Optional
from fastapi import FastAPI, HTTPException, Depends, Form
from packaging.specifiers import SpecifierSet

from db_client import DBClient
from input_validator import InputValidator
from graph_builder import GraphBuilder
from resolver import Resolver




DB_PATH = os.path.join("data", "pypi-data.sqlite")

# Singleton do Banco de Dados 
_db_client: Optional[DBClient] = None

logging.basicConfig(level=logging.INFO, format='%(message)s')




# Inicialização da Aplicação
app = FastAPI(
    title="Python Dependency Resolver",
    description="API para resolução de dependências de pacotes Python usando Backtracking e Heurísticas.",
    version="1.0.0"
)




@app.on_event("startup")
def startup_event():
    """
    Inicializa a instância do DBClient e verifica se o arquivo existe.
    """
    global _db_client

    if not os.path.exists(DB_PATH):
        logging.info(f'AVISO CRÍTICO: Banco de dados "{DB_PATH}" não encontrado.')
        raise RuntimeError(f'Banco de dados "{DB_PATH}" não encontrado.')
    
    else:
        logging.info(f'Banco de dados encontrado em: {DB_PATH}')
    
    _db_client = DBClient(DB_PATH)
    logging.info('Serviço de banco de dados configurado.')




@app.on_event("shutdown")
def shutdown_event():
    """
    Fecha a conexão ao parar o servidor.
    """
    
    logging.info('Encerrando aplicação...')




def get_db() -> DBClient:
    """
    Função de Dependência (Dependency Injection).
    Retorna a instância ativa do banco de dados para os endpoints que precisarem.
    """

    if _db_client is None:
        logging.error("Serviço de banco de dados não inicializado.")
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
                
    logging.info(f'Prepared requirements: {requirements}')
                
    return requirements




# ENDPOINTS

@app.get("/")
def read_root():
    return {"message": "Dependency Resolver API is running. Use POST /resolve to solve dependencies."}




@app.post("/resolve")
def resolve_dependencies(
        # Parâmetros definidos como Form aparecem como caixas de texto no Swagger
        python: Optional[str] = Form('"3.10"', description="Versão do Python."),
        wants: Optional[List[str]] = Form('["mcp"]', description='Lista de pacotes desejados. Ex: "mcp"'),
        fixed: Optional[str] = Form('{"numpy": ">=1.0"}', description='JSON contendo os pacotes e versões fixas. Ex: {"numpy": ">=1.0"}'),
        max_versions: int = Form(10, description="Limite de versões por pacote durante as buscas."),
        db_client: DBClient = Depends(get_db)):
    """
    Endpoint principal para resolver dependências.
    """

    # Processamento do campo 'fixed' 
    fixed_dict = {}
    if fixed:
        try:
            # Tenta converter a string de entrada em um dicionário
            fixed_dict = json.loads(fixed)

            if not isinstance(fixed_dict, dict):
                raise ValueError
            
        except (json.JSONDecodeError, ValueError):
            logging.error("Erro ao processar o campo 'fixed'.")
            raise HTTPException(status_code=400, detail='O campo "fixed" deve ser um JSON válido (ex: {"pkg": "==1.0"}).')
    

    # Processamento do campo 'wants' 
    final_wants = []
    
    if wants:
        for item in wants:
            # Se o item contiver vírgula, quebra ele. Se não, mantém.
            if "," in item:
                parts = [x.strip() for x in item.split(",") if x.strip()]
                final_wants.extend(parts)
            elif item.strip():
                final_wants.append(item.strip())
    
    # Montagem do JSON 
    input_data = {
        "python": python,
        "fixed": fixed_dict,
        "wants": final_wants if final_wants else [],
        "max_versions": max_versions
    }

    logging.info(f'Requisição recebida: {input_data}')

    validator = InputValidator(db_client)
    is_valid, error_msg = validator.validate(input_data)
    
    if not is_valid:
        raise HTTPException(status_code=400, detail=error_msg)
    
    gb = GraphBuilder(
        db_client=db_client,
        python_version=python,
        max_versions_per_package=max_versions
    )
    
    resolver = Resolver(graph_builder=gb)

    # Execução
    try:
        reqs_map = prepare_requirements(input_data)
        logging.info(f'Resolvendo para Python: {python}, Alvos: {list(reqs_map.keys())}')
        result = resolver.resolve(reqs_map)

        return result

    except Exception as e:
        logging.error(f"Erro interno do servidor: {str(e)}")
        import traceback
        logging.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Erro interno do servidor.")




if __name__ == "__main__":
    uvicorn.run("main:app", host="localhost", port=8000, reload=True)