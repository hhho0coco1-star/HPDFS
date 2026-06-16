from datetime import datetime
from typing import Any

import pandas as pd
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from models import DiagnosisLog, Disk
from predictor import FEATURES, predict

router = APIRouter()


def build_disk_key(agent_id: str, serial: str, device: str, model: str) -> str:
    """DB 내부에서 Agent별 디스크를 구분하기 위한 저장 키를 만든다."""
    safe_agent = agent_id or "UNKNOWN"
    safe_serial = (serial or "UNKNOWN").strip()
    if safe_agent == "UNKNOWN":
        return safe_serial or "UNKNOWN"
    if safe_serial.upper() not in {"", "UNKNOWN", "NONE", "NULL"}:
        return f"{safe_agent}::{safe_serial}"
    return f"{safe_agent}::UNKNOWN::{device or 'device'}::{model or 'model'}"


class SmartData(BaseModel):
    """에이전트가 보내는 SMART 수치"""
    agent_id:       str | None = None   # 데이터를 보낸 Agent/PC 식별자
    scan_id:        str | None = None   # 한 번의 Agent 수집 묶음을 구분하는 ID
    serial:         str   = "UNKNOWN"   # 디스크 고유 시리얼 넘버
    device:         str   = ""          # 연결 경로 참고용 (/dev/sda 등)
    model:          str
    capacity_bytes: int   = 0
    smart_5_raw:    int   = 0
    smart_9_raw:    int   = 0
    smart_187_raw:  int   = 0
    smart_188_raw:  int   = 0
    smart_194_raw:  int   = 0
    smart_197_raw:  int   = 0
    smart_198_raw:  int   = 0
    smart_199_raw:  int   = 0


@router.post("/diagnose")
def diagnose(request: Request, data: SmartData, db: Session = Depends(get_db)) -> dict[str, Any]:
    ml_models = request.app.state.ml_models

    # ① SMART 수치 → DataFrame
    df = pd.DataFrame([{
        "model":          data.model,
        "capacity_bytes": data.capacity_bytes,
        "smart_5_raw":    data.smart_5_raw,
        "smart_9_raw":    data.smart_9_raw,
        "smart_187_raw":  data.smart_187_raw,
        "smart_188_raw":  data.smart_188_raw,
        "smart_194_raw":  data.smart_194_raw,
        "smart_197_raw":  data.smart_197_raw,
        "smart_198_raw":  data.smart_198_raw,
        "smart_199_raw":  data.smart_199_raw,
    }], columns=FEATURES)

    # ② ML 예측
    if "storage" not in ml_models:
        from fastapi import HTTPException
        raise HTTPException(status_code=503, detail="ML 모델이 로드되지 않았습니다. 서버 로그를 확인하세요.")
    result = predict(df, ml_models["storage"])

    is_manual = data.serial == "MANUAL"
    agent_id = data.agent_id or "UNKNOWN"
    scan_id = data.scan_id or f"{agent_id}-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    disk_key = build_disk_key(agent_id, data.serial, data.device, data.model)

    # ③ diagnosis_log 저장 (수동진단 제외)
    if not is_manual:
        log = DiagnosisLog(
            scan_id        = scan_id,
            agent_id       = agent_id,
            timestamp      = datetime.now(),
            serial         = disk_key,
            device         = data.device,
            model          = data.model,
            capacity_bytes = data.capacity_bytes,
            smart_5_raw    = data.smart_5_raw,
            smart_9_raw    = data.smart_9_raw,
            smart_187_raw  = data.smart_187_raw,
            smart_188_raw  = data.smart_188_raw,
            smart_194_raw  = data.smart_194_raw,
            smart_197_raw  = data.smart_197_raw,
            smart_198_raw  = data.smart_198_raw,
            smart_199_raw  = data.smart_199_raw,
            ml_probability = result["prob"],
            ml_level       = result["ml_level"],
            rule_level     = result["rule_level"],
            final_level    = result["final"],
        )
        db.add(log)

        # ④ disks 테이블 최신 상태 업데이트 (serial 기준)
        disk = db.query(Disk).filter(Disk.serial == disk_key).first()
        if disk:
            disk.agent_id      = agent_id
            disk.device        = data.device
            disk.model         = data.model
            disk.capacity_bytes= data.capacity_bytes
            disk.final_level   = result["final"]
            disk.risk          = round(result["prob"] * 100, 2)
            disk.last_scan_id  = scan_id
            disk.last_updated  = datetime.now()
        else:
            db.add(Disk(
                serial         = disk_key,
                agent_id       = agent_id,
                device         = data.device,
                model          = data.model,
                capacity_bytes = data.capacity_bytes,
                final_level    = result["final"],
                risk           = round(result["prob"] * 100, 2),
                last_scan_id   = scan_id,
                action_status  = "미확인",
                last_updated   = datetime.now(),
            ))

        db.commit()

    # ⑤ 예측 결과 응답
    return {
        "agent_id":    agent_id,
        "serial":      data.serial,
        "device":      data.device,
        "model":       data.model,
        "ml_level":    result["ml_level"],
        "rule_level":  result["rule_level"],
        "final_level": result["final"],
        "risk":        round(result["prob"] * 100, 2),
        "reasons":     result["reasons"],
        "actions":     result["actions"],
    }
