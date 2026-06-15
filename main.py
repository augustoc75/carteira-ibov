import logging
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks
from playwright_scraper import trigger_snapshot
import os

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    
    # Shutdown
    logger.info("Encerrando aplicação")


app = FastAPI(
    title="Carteira Ibovespa API",
    description="API para capturar e processar dados da carteira do Ibovespa",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/health", tags=["Health"])
async def health_check():
    """
    Verificar saúde da aplicação
    """
    return {
        "status": "healthy",
        "service": "Carteira Ibovespa API",
    }


@app.post("/trigger-snapshot", tags=["Snapshot"])
async def trigger_snapshot_endpoint(
    background_tasks: BackgroundTasks
):
    """
    Dispara o processo de extração da carteira Ibovespa e upload para GCS.
    """
    try:
        # Executar em background
        background_tasks.add_task(_run_snapshot_task)

        return {
            "status": "accepted",
            "message": "Snapshot agendado para execução em background",
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


async def _run_snapshot_task():
    """
    Tarefa em background para executar o snapshot.
    """
    try:
        await trigger_snapshot()
        logger.info("Snapshot concluído com sucesso")
    except Exception as e:
        logger.error(f"Erro na execução do snapshot: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    # Cloud Run dynamic port or default to 8000
    port = int(os.environ.get("PORT", 8000))

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=False,
    )
