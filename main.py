import logging
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from database import engine, get_db, Base
from models import SnapshotExecution
from playwright_scraper import trigger_snapshot
import uuid
import os

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: criar tabelas
    logger.info("Criando tabelas do banco de dados...")
    Base.metadata.create_all(bind=engine)
    logger.info("Tabelas criadas com sucesso")
    
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
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """
    Dispara o processo de extração da carteira Ibovespa e upload para GCS.
    
    O processo:
    1. Acessa a página da B3 via Playwright (headless)
    2. Faz download do CSV da carteira
    3. Upload para o Google Cloud Storage (pasta comp-ibov)
    
    Retorna ID de rastreamento da execução.
    """
    try:
        # Criar registro de execução
        execution_id = uuid.uuid4()
        execution = SnapshotExecution(id=str(execution_id), status="started")
        db.add(execution)
        db.commit()
        db.refresh(execution)

        # Executar em background
        background_tasks.add_task(
            _run_snapshot_task,
            execution_id=execution_id,
        )

        logger.info(f"Snapshot {execution_id} agendado para execução")

        return {
            "execution_id": str(execution_id),
            "status": "accepted",
            "message": "Snapshot agendado para execução em background",
        }

    except Exception as e:
        logger.error(f"Erro ao agendar snapshot: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


async def _run_snapshot_task(execution_id: uuid.UUID):
    """
    Tarefa em background para executar o snapshot.
    """
    from database import SessionLocal
    
    db = SessionLocal()
    try:
        # Executar snapshot
        result = await trigger_snapshot(db)

        # Atualizar execução
        execution = db.query(SnapshotExecution).filter(
            SnapshotExecution.id == str(execution_id)
        ).first()

        if execution:
            execution.status = "completed"
            db.commit()

        logger.info(f"Snapshot {execution_id} concluído com sucesso")

    except Exception as e:
        logger.error(f"Erro na execução do snapshot {execution_id}: {str(e)}")

        # Atualizar execução com erro
        execution = db.query(SnapshotExecution).filter(
            SnapshotExecution.id == str(execution_id)
        ).first()

        if execution:
            execution.status = "failed"
            execution.error_message = str(e)[:500]
            db.commit()

    finally:
        db.close()


@app.get("/snapshot-status/{execution_id}", tags=["Snapshot"])
async def get_snapshot_status(
    execution_id: str,
    db: Session = Depends(get_db),
):
    """
    Obter status de uma execução de snapshot.
    """
    try:
        execution = db.query(SnapshotExecution).filter(
            SnapshotExecution.id == execution_id
        ).first()

        if not execution:
            raise HTTPException(status_code=404, detail="Execução não encontrada")

        return {
            "execution_id": str(execution.id),
            "status": execution.status,
            "error_message": execution.error_message,
            "created_at": execution.created_at.isoformat(),
            "updated_at": execution.updated_at.isoformat(),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao obter status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/carteira", tags=["Data"])
async def get_carteira(
    db: Session = Depends(get_db),
    data_pregao: str = None,
):
    """
    Obter dados da carteira Ibovespa.
    
    Parâmetros:
    - data_pregao: data no formato YYYY-MM-DD (opcional)
    """
    try:
        from datetime import datetime
        from models import CarteiraIbovespa

        query = db.query(CarteiraIbovespa)

        if data_pregao:
            data = datetime.strptime(data_pregao, "%Y-%m-%d").date()
            query = query.filter(CarteiraIbovespa.data_pregao == data)
        else:
            # Retornar dados mais recentes
            query = query.order_by(CarteiraIbovespa.data_pregao.desc())

        registros = query.limit(1000).all()

        return {
            "total": len(registros),
            "data": [
                {
                    "codigo": r.codigo,
                    "acao": r.acao,
                    "tipo": r.tipo,
                    "quantidade": r.quantidade,
                    "participacao": r.participacao,
                    "data_pregao": r.data_pregao.isoformat(),
                }
                for r in registros
            ],
        }

    except Exception as e:
        logger.error(f"Erro ao obter carteira: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


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
