import os
import uuid
from datetime import datetime

from sqlalchemy import (
    Column,
    DateTime,
    Float,
    ForeignKey,
    String,
    create_engine,
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker


DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://zolis:zolis@db:5432/zolis")

Base = declarative_base()


class Runner(Base):
    __tablename__ = "runners"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    email = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    sessions = relationship("Session", back_populates="runner")


class Session(Base):
    __tablename__ = "sessions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    runner_id = Column(String, ForeignKey("runners.id"), nullable=False)
    started_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    total_distance_m = Column(Float, default=0.0, nullable=False)

    runner = relationship("Runner", back_populates="sessions")
    measures = relationship("Measure", back_populates="session")


class Measure(Base):
    __tablename__ = "measures"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String, ForeignKey("sessions.id"), nullable=False)
    ts = Column(DateTime, default=datetime.utcnow, nullable=False)
    lat = Column(Float, nullable=False)
    lon = Column(Float, nullable=False)
    temperature = Column(Float, nullable=False)
    humidite = Column(Float, nullable=False)
    pression = Column(Float, nullable=False)
    batterie = Column(Float, nullable=False)
    distance_m = Column(Float, default=0.0, nullable=False)

    session = relationship("Session", back_populates="measures")


engine = create_engine(DATABASE_URL, future=True)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
