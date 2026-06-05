from sqlalchemy import Column, Integer, String, Float, Date, DateTime, Index
import uuid
from datetime import datetime
from database import Base


class SnapshotExecution(Base):
    __tablename__ = "snapshot_executions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    status = Column(String(50), default="started")
    error_message = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class CarteiraIbovespa(Base):
    __tablename__ = "carteira_ibovespa"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    data_pregao = Column(Date, nullable=False, index=True)
    codigo = Column(String(10), nullable=False)
    acao = Column(String(100), nullable=False)
    tipo = Column(String(10), nullable=True)
    quantidade = Column(Integer, nullable=False)
    participacao = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index('ix_carteira_ibovespa_data_pregao_codigo', 'data_pregao', 'codigo', unique=True),
    )
