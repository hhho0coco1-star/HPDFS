import os
from contextlib import asynccontextmanager

import joblib
from sqlalchemy import inspect, text
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import Base, engine
from router_diagnose import router as diagnose_router
from router_disks import router as disks_router



def ensure_runtime_columns():
    """Add lightweight runtime columns used to separate the latest scan batch."""
    inspector = inspect(engine)
    with engine.begin() as conn:
        diagnosis_cols = {col["name"] for col in inspector.get_columns("diagnosis_log")}
        if "scan_id" not in diagnosis_cols:
            conn.execute(text("ALTER TABLE diagnosis_log ADD COLUMN scan_id VARCHAR"))

        disk_cols = {col["name"] for col in inspector.get_columns("disks")}
        if "last_scan_id" not in disk_cols:
            conn.execute(text("ALTER TABLE disks ADD COLUMN last_scan_id VARCHAR"))

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        app.state.ml_models = {
            "storage": joblib.load("models/storage_best_model.pkl"),
        }
    except FileNotFoundError:
        print("[경고] 모델 파일을 찾을 수 없습니다. ML 예측 기능이 비활성화됩니다.")
        app.state.ml_models = {}
    Base.metadata.create_all(bind=engine)
    ensure_runtime_columns()
    yield
    app.state.ml_models.clear()


app = FastAPI(
    title="PDFS API",
    description="Predictive Drive Failure System — 고장 예측 API (port 8010)",
    version="2.0.0",
    lifespan=lifespan,
)

_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 등록
app.include_router(diagnose_router, prefix="/api", tags=["진단"])
app.include_router(disks_router,   prefix="/api", tags=["디스크"])


@app.get("/")
def health_check():
    """서버 상태 확인"""
    return {"status": "ok", "service": "PDFS API v2.0.0"}

