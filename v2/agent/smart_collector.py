from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

import pandas as pd

FEATURES = [
    "serial",
    "model",
    "capacity_bytes",
    "smart_5_raw",
    "smart_9_raw",
    "smart_187_raw",
    "smart_188_raw",
    "smart_194_raw",
    "smart_197_raw",
    "smart_198_raw",
    "smart_199_raw",
]

SMART_ID_TO_COL = {
    5:   "smart_5_raw",
    9:   "smart_9_raw",
    187: "smart_187_raw",
    188: "smart_188_raw",
    194: "smart_194_raw",
    197: "smart_197_raw",
    198: "smart_198_raw",
    199: "smart_199_raw",
}

# agent/ 기준으로 상위 폴더의 tools/smartctl/smartctl.exe 탐색
_AGENT_DIR = Path(__file__).resolve().parent
_TOOLS_SMARTCTL = _AGENT_DIR.parent / "tools" / "smartctl" / "smartctl.exe"


def get_smartctl_path() -> str | None:
    if _TOOLS_SMARTCTL.exists():
        return str(_TOOLS_SMARTCTL)
    return shutil.which("smartctl")


def _run(cmd: list[str]) -> tuple[int, str, str]:
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="ignore")
    return r.returncode, r.stdout, r.stderr


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value) if value is not None else default
    except Exception:
        return default


def _parse_temperature(raw: dict) -> int:
    s = str(raw.get("string", "")).strip()
    m = re.search(r"-?\d+", s)
    if m:
        return _safe_int(m.group(0))
    v = _safe_int(raw.get("value", 0))
    if 0 <= v <= 120:
        return v
    low = v & 0xFF
    return low if 0 <= low <= 120 else 0


def _get_nested(data: dict, path: list[str], default=None):
    cur = data
    for key in path:
        if not isinstance(cur, dict) or key not in cur:
            return default
        cur = cur[key]
    return cur


def scan_devices() -> list[list[str]]:
    """연결된 디스크 목록 반환"""
    exe = get_smartctl_path()
    if not exe:
        raise RuntimeError("smartctl을 찾을 수 없습니다.")
    _, out, err = _run([exe, "--scan"])
    if not out.strip():
        raise RuntimeError(err or "smartctl --scan 출력이 비어 있습니다.")
    result = []
    for line in out.splitlines():
        pure = line.split("#", 1)[0].strip()
        if pure:
            result.append(pure.split())
    return result


def extract_features(device_args: list[str]) -> pd.DataFrame:
    """디스크 SMART 수치 10개 읽어서 DataFrame 반환"""
    exe = get_smartctl_path()
    if not exe:
        raise RuntimeError("smartctl을 찾을 수 없습니다.")

    _, out, err = _run([exe, "-a", "-j", *device_args])
    if not out.strip():
        raise RuntimeError(err or "smartctl 출력이 비어 있습니다.")

    data = json.loads(out)

    row = {
        "serial":         data.get("serial_number") or data.get("serial", "UNKNOWN"),
        "model":          data.get("model_name") or data.get("model_number") or "Unknown",
        "capacity_bytes": _safe_int(_get_nested(data, ["user_capacity", "bytes"], 0)),
        "smart_5_raw":    0,
        "smart_9_raw":    0,
        "smart_187_raw":  0,
        "smart_188_raw":  0,
        "smart_194_raw":  0,
        "smart_197_raw":  0,
        "smart_198_raw":  0,
        "smart_199_raw":  0,
    }

    if "ata_smart_attributes" in data:
        for attr in _get_nested(data, ["ata_smart_attributes", "table"], []):
            attr_id = attr.get("id")
            col = SMART_ID_TO_COL.get(attr_id)
            if not col:
                continue
            raw = attr.get("raw", {})
            row[col] = _parse_temperature(raw) if attr_id == 194 else _safe_int(raw.get("value", 0))
    else:
        temp = _get_nested(data, ["temperature", "current"]) or \
               _get_nested(data, ["nvme_smart_health_information_log", "temperature"])
        row["smart_194_raw"] = _safe_int(temp)

        hours = _get_nested(data, ["power_on_time", "hours"]) or \
                _get_nested(data, ["nvme_smart_health_information_log", "power_on_hours"])
        row["smart_9_raw"] = _safe_int(hours)

    return pd.DataFrame([row], columns=FEATURES)
