from __future__ import annotations

import json
import re
import shlex
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
import streamlit as st


BASE_DIR = Path(__file__).resolve().parent
MODEL_DIR = BASE_DIR / "models"
SCORE_DIR = BASE_DIR / "scores"
LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)

MODEL_PATH = MODEL_DIR / "storage_best_model.pkl"
THRESHOLD_PATH = MODEL_DIR / "storage_threshold.json"
LOG_PATH = LOG_DIR / "storage_diagnosis_log.csv"

FEATURES = [
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
    5: "smart_5_raw",
    9: "smart_9_raw",
    187: "smart_187_raw",
    188: "smart_188_raw",
    194: "smart_194_raw",
    197: "smart_197_raw",
    198: "smart_198_raw",
    199: "smart_199_raw",
}

COL_KO = {
    "model": "모델",
    "capacity_bytes": "용량",
    "smart_5_raw": "재할당섹터(5)",
    "smart_9_raw": "가동시간(9)",
    "smart_187_raw": "에러(187)",
    "smart_188_raw": "명령타임아웃(188)",
    "smart_194_raw": "온도(194)",
    "smart_197_raw": "대기섹터(197)",
    "smart_198_raw": "정정불가(198)",
    "smart_199_raw": "CRC오류(199)",
}


st.set_page_config(
    page_title="PDFS — Predictive Drive Failure System",
    page_icon="💾",
    layout="wide",
    initial_sidebar_state="collapsed",
)


# =========================================================
# CSS: 사용자가 올린 mockup과 비슷한 GitHub dark dashboard 스타일
# =========================================================
CSS = """
<style>
:root {
  --bg: #0d1117;
  --bg-card: #161b22;
  --bg-card2: #1c2128;
  --border: #30363d;
  --text: #e6edf3;
  --text-dim: #8b949e;
  --accent: #58a6ff;
  --ok: #3fb950;
  --warn: #d29922;
  --danger: #f85149;
}
.stApp { background: var(--bg); color: var(--text); }
[data-testid="stHeader"] { background: transparent; }
[data-testid="stSidebar"] { background: #010409; border-right: 1px solid var(--border); }
.block-container { padding-top: 0.8rem; max-width: 1240px; }
h1,h2,h3,h4,p,span,div { color: var(--text); }
button[kind="primary"] {
  background: var(--accent) !important;
  color: #0d1117 !important;
  border: none !important;
  font-weight: 800 !important;
}
div[data-testid="stMetric"] {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 14px 16px;
}
div[data-testid="stMetricLabel"] p { color: var(--text-dim) !important; }
div[data-testid="stMetricValue"] { color: var(--text) !important; }
.pdfs-header {
  display:flex; align-items:center; justify-content:space-between;
  padding: 16px 22px; border:1px solid var(--border); border-radius: 12px;
  background:#010409; margin-bottom:22px; position: sticky; top:0; z-index:5;
}
.logo { display:flex; align-items:center; gap:10px; }
.logo .mark {
  width:30px; height:30px; border-radius:7px;
  background:linear-gradient(135deg,var(--accent),#1f6feb);
  display:grid; place-items:center; font-weight:900; color:#fff; font-size:15px;
}
.logo b { font-size:18px; letter-spacing:.2px; }
.logo span { color:var(--text-dim); font-size:12px; margin-left:4px; }
.live { display:flex; align-items:center; gap:8px; color:var(--text-dim); font-size:13px; }
.dot { width:9px; height:9px; border-radius:50%; background:var(--ok); box-shadow:0 0 0 0 rgba(63,185,80,.6); animation:pulse 1.6s infinite; }
@keyframes pulse { 0%{box-shadow:0 0 0 0 rgba(63,185,80,.5)} 70%{box-shadow:0 0 0 8px rgba(63,185,80,0)} 100%{box-shadow:0 0 0 0 rgba(63,185,80,0)} }
.section-title {
  font-size:13px; color:var(--text-dim); text-transform:uppercase;
  letter-spacing:.6px; margin:26px 0 12px; font-weight:700;
}
.summary { display:grid; grid-template-columns: repeat(4,1fr); gap:14px; }
.stat {
  background:var(--bg-card); border:1px solid var(--border); border-radius:10px; padding:18px 20px;
}
.stat .label { color:var(--text-dim); font-size:13px; }
.stat .num { font-size:32px; font-weight:900; margin-top:8px; }
.stat .sub { font-size:12px; color:var(--text-dim); margin-top:2px; }
.stat.total { border-left:3px solid var(--accent); }
.stat.ok { border-left:3px solid var(--ok); }
.stat.warn { border-left:3px solid var(--warn); }
.stat.danger { border-left:3px solid var(--danger); }
.num.ok { color:var(--ok); } .num.warn { color:var(--warn); } .num.danger { color:var(--danger); }
.charts { display:grid; grid-template-columns: 320px 1fr; gap:14px; }
.chart-card { background:var(--bg-card); border:1px solid var(--border); border-radius:10px; padding:18px 20px; }
.chart-card h4 { font-size:13px; color:var(--text); margin-bottom:16px; }
.donut-wrap { display:flex; align-items:center; gap:22px; }
.donut { width:130px; height:130px; border-radius:50%; position:relative; flex-shrink:0; }
.donut::before { content:''; position:absolute; inset:20px; border-radius:50%; background:var(--bg-card); }
.donut .center { position:absolute; inset:0; display:grid; place-items:center; text-align:center; }
.donut .big { font-size:26px; font-weight:900; }
.donut .lbl { font-size:11px; color:var(--text-dim); }
.legend { display:flex; flex-direction:column; gap:10px; width:120px; }
.legend .item { display:flex; align-items:center; gap:8px; font-size:13px; color:var(--text); }
.legend .sw { width:11px; height:11px; border-radius:3px; }
.legend .cnt { margin-left:auto; font-weight:800; color:var(--text-dim); }
.bars { display:flex; align-items:flex-end; gap:10px; height:130px; padding-top:8px; }
.bar-col { flex:1; display:flex; flex-direction:column; align-items:center; gap:7px; height:100%; justify-content:flex-end; }
.bar-col .bv, .bar-col .bk { font-size:11px; color:var(--text-dim); }
.bar2 { width:70%; max-width:34px; border-radius:5px 5px 0 0; background:linear-gradient(180deg,var(--warn),rgba(210,153,34,.3)); }
.bar-col.peak .bar2 { background:linear-gradient(180deg,var(--danger),rgba(248,81,73,.3)); }
.demo-panel {
  background:linear-gradient(135deg, rgba(88,166,255,.08), rgba(31,111,235,.04));
  border:1px dashed rgba(88,166,255,.4); border-radius:10px; padding:16px 20px;
  display:flex; align-items:center; justify-content:space-between; gap:16px;
}
.demo-panel b { font-size:14px; }
.demo-panel p { color:var(--text-dim); font-size:12px; margin-top:3px; margin-bottom:0; }
.risk-grid { display:grid; grid-template-columns:repeat(2,1fr); gap:14px; }
.risk-card {
  background:var(--bg-card); border:1px solid var(--border); border-radius:10px; padding:16px 18px;
  position:relative; overflow:hidden;
}
.risk-card.danger { border-color:rgba(248,81,73,.45); }
.risk-card.warn { border-color:rgba(210,153,34,.45); }
.risk-card.ok { border-color:rgba(63,185,80,.35); }
.risk-card .bar { position:absolute; left:0; top:0; bottom:0; width:4px; }
.risk-card.danger .bar { background:var(--danger); }
.risk-card.warn .bar { background:var(--warn); }
.risk-card.ok .bar { background:var(--ok); }
.risk-head { display:flex; justify-content:space-between; align-items:flex-start; }
.disk-name { font-weight:800; font-size:15px; }
.disk-model { color:var(--text-dim); font-size:12px; margin-top:3px; }
.badge { font-size:11px; font-weight:800; padding:4px 9px; border-radius:20px; }
.badge.danger { background:rgba(248,81,73,.15); color:var(--danger); }
.badge.warn { background:rgba(210,153,34,.15); color:var(--warn); }
.badge.ok { background:rgba(63,185,80,.15); color:var(--ok); }
.risk-meter { margin-top:14px; }
.risk-meter .top { display:flex; justify-content:space-between; font-size:12px; color:var(--text-dim); margin-bottom:5px; }
.risk-meter .val { font-weight:800; color:var(--text); }
.track { height:8px; background:var(--bg-card2); border-radius:5px; overflow:hidden; }
.fill { height:100%; border-radius:5px; }
.fill.danger { background:var(--danger); } .fill.warn { background:var(--warn); } .fill.ok { background:var(--ok); }
.smart-row { display:flex; gap:16px; margin-top:14px; flex-wrap:wrap; }
.smart { font-size:12px; }
.smart .k { color:var(--text-dim); }
.smart .v { font-weight:800; margin-left:5px; }
.smart .v.bad { color:var(--danger); }
.smart .v.warn { color:var(--warn); }
.pdfs-table {
  width:100%; border-collapse:collapse; background:var(--bg-card); border:1px solid var(--border);
  border-radius:10px; overflow:hidden; display:table;
}
.pdfs-table th, .pdfs-table td { text-align:left; padding:12px 16px; font-size:13px; border-bottom:1px solid var(--border); }
.pdfs-table th { color:var(--text-dim); background:var(--bg-card2); font-weight:700; }
.pdfs-table tr:last-child td { border-bottom:none; }
.status { display:inline-flex; align-items:center; gap:7px; font-size:12px; font-weight:800; }
.status .d { width:8px; height:8px; border-radius:50%; }
.status.ok .d { background:var(--ok); } .status.warn .d { background:var(--warn); } .status.danger .d { background:var(--danger); }
.status.ok { color:var(--ok); } .status.warn { color:var(--warn); } .status.danger { color:var(--danger); }
.toast {
  background:var(--bg-card); border:1px solid rgba(248,81,73,.5); border-left:4px solid var(--danger);
  border-radius:10px; padding:14px 16px; margin-top:12px; box-shadow:0 10px 28px rgba(0,0,0,.25);
}
.toast .th { display:flex; align-items:center; gap:8px; font-weight:800; color:var(--danger); font-size:14px; }
.toast .tb { font-size:13px; margin-top:7px; color:var(--text); }
.disk-header { background:var(--bg-card); border:1px solid var(--border); border-left:3px solid var(--danger); border-radius:10px; padding:20px 24px; }
.disk-header .name { font-size:22px; font-weight:900; }
.disk-meta { display:flex; gap:26px; flex-wrap:wrap; margin-top:14px; }
.disk-meta .k { color:var(--text-dim); font-size:12px; display:block; }
.disk-meta .v { font-weight:800; font-size:13px; }
.two-col { display:grid; grid-template-columns:320px 1fr; gap:14px; }
.card { background:var(--bg-card); border:1px solid var(--border); border-radius:10px; padding:20px 24px; }
.gauge-wrap { display:flex; flex-direction:column; align-items:center; }
.gauge { width:170px; height:170px; border-radius:50%; position:relative; }
.gauge::before { content:''; position:absolute; inset:18px; border-radius:50%; background:var(--bg-card); }
.gauge .c { position:absolute; inset:0; display:grid; place-items:center; text-align:center; }
.gauge .pct { font-size:38px; font-weight:900; }
.gauge .lbl { font-size:12px; color:var(--text-dim); }
.gauge-status { margin-top:16px; font-weight:800; }
.predict .headline { font-size:18px; font-weight:900; display:flex; align-items:center; gap:8px; }
.predict .desc { color:var(--text-dim); font-size:13px; margin-top:8px; line-height:1.6; }
.reason-tags { display:flex; flex-wrap:wrap; gap:8px; margin-top:8px; }
.rtag { background:rgba(248,81,73,.1); border:1px solid rgba(248,81,73,.3); color:var(--danger); font-size:12px; padding:6px 11px; border-radius:7px; }
.action-box { margin-top:18px; background:var(--bg-card2); border-radius:8px; padding:12px 14px; font-size:13px; }
.smart-grid { display:grid; grid-template-columns:repeat(5,1fr); gap:12px; }
.sc { background:var(--bg-card); border:1px solid var(--border); border-radius:10px; padding:14px 16px; }
.sc .k { font-size:12px; color:var(--text-dim); } .sc .v { font-size:24px; font-weight:900; margin-top:6px; }
.sc.bad { border-color:rgba(248,81,73,.35); } .sc.bad .v { color:var(--danger); }
.sc.warn { border-color:rgba(210,153,34,.35); } .sc.warn .v { color:var(--warn); }
.mock-tag { position:fixed; bottom:14px; right:14px; background:var(--bg-card2); border:1px solid var(--border); color:var(--text-dim); font-size:11px; padding:6px 12px; border-radius:20px; z-index:99; }
@media (max-width: 820px) {
  .summary, .risk-grid, .charts, .two-col { grid-template-columns:1fr; }
  .smart-grid { grid-template-columns:repeat(2,1fr); }
}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)


# =========================================================
# Data / Model functions
# =========================================================
@st.cache_resource
def load_model():
    if MODEL_PATH.exists():
        return joblib.load(MODEL_PATH)
    return None


def threshold() -> float:
    if THRESHOLD_PATH.exists():
        try:
            data = json.loads(THRESHOLD_PATH.read_text(encoding="utf-8"))
            return float(data.get("recommended_threshold", 0.5))
        except Exception:
            return 0.5
    return 0.5


def smartctl_available() -> bool:
    return shutil.which("smartctl") is not None


def run_cmd(cmd: list[str]) -> tuple[int, str, str]:
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="ignore")
    return r.returncode, r.stdout, r.stderr


def parse_scan_line(line: str) -> list[str] | None:
    pure = line.split("#", 1)[0].strip()
    if not pure:
        return None
    return pure.split()


def scan_devices() -> list[list[str]]:
    code, out, err = run_cmd(["smartctl", "--scan"])
    if not out.strip():
        raise RuntimeError(err or "smartctl --scan 출력이 비어 있습니다.")
    return [x for line in out.splitlines() if (x := parse_scan_line(line))]


def get_nested(data: dict, path: list[str], default=None):
    cur = data
    for key in path:
        if not isinstance(cur, dict) or key not in cur:
            return default
        cur = cur[key]
    return cur


def safe_int(value, default=0) -> int:
    try:
        if value is None:
            return default
        return int(value)
    except Exception:
        return default


def parse_temperature_raw(raw: dict[str, Any]) -> int:
    s = str(raw.get("string", "")).strip()
    m = re.search(r"-?\d+", s)
    if m:
        return safe_int(m.group(0))
    v = safe_int(raw.get("value", 0))
    if 0 <= v <= 120:
        return v
    low = v & 0xFF
    return low if 0 <= low <= 120 else 0


def extract_features(device_args: list[str]) -> pd.DataFrame:
    code, out, err = run_cmd(["smartctl", "-a", "-j"] + device_args)
    if not out.strip():
        raise RuntimeError(err or "smartctl 출력이 비어 있습니다.")
    data = json.loads(out)

    messages = data.get("smartctl", {}).get("messages", [])
    text = "\n".join(str(m.get("string", "")) for m in messages if isinstance(m, dict))
    if "SMART Disabled" in text:
        raise RuntimeError("SMART가 비활성화되어 있습니다. SMART 활성화 후 다시 진단하세요.")

    row = {
        "model": data.get("model_name") or data.get("model_number") or get_nested(data, ["device", "model_name"], "Unknown"),
        "capacity_bytes": safe_int(get_nested(data, ["user_capacity", "bytes"], 0)),
        "smart_5_raw": 0,
        "smart_9_raw": 0,
        "smart_187_raw": 0,
        "smart_188_raw": 0,
        "smart_194_raw": 0,
        "smart_197_raw": 0,
        "smart_198_raw": 0,
        "smart_199_raw": 0,
    }

    if "ata_smart_attributes" in data:
        for attr in get_nested(data, ["ata_smart_attributes", "table"], []):
            attr_id = attr.get("id")
            col = SMART_ID_TO_COL.get(attr_id)
            if not col:
                continue
            raw = attr.get("raw", {})
            row[col] = parse_temperature_raw(raw) if attr_id == 194 else safe_int(raw.get("value", 0))
    else:
        temp = get_nested(data, ["temperature", "current"], None)
        if temp is None:
            temp = get_nested(data, ["nvme_smart_health_information_log", "temperature"], None)
        row["smart_194_raw"] = safe_int(temp, 0)

        hours = get_nested(data, ["power_on_time", "hours"], None)
        if hours is None:
            hours = get_nested(data, ["nvme_smart_health_information_log", "power_on_hours"], None)
        row["smart_9_raw"] = safe_int(hours, 0)

    return pd.DataFrame([row], columns=FEATURES)


def enable_smart(device_args: list[str]) -> tuple[bool, str]:
    code, out, err = run_cmd(["smartctl", "-s", "on"] + device_args)
    return code == 0, ((out or "") + "\n" + (err or "")).strip()


def prob_to_level(prob: float) -> str:
    if prob < 0.3:
        return "정상"
    if prob < 0.7:
        return "주의"
    return "위험"


def rule_level(row: pd.Series) -> str:
    if row["smart_198_raw"] > 0 or row["smart_197_raw"] > 0:
        return "위험"
    if row["smart_5_raw"] >= 100:
        return "위험"
    if row["smart_187_raw"] > 0:
        return "위험"
    if row["smart_5_raw"] > 0 or row["smart_199_raw"] > 0 or row["smart_188_raw"] > 0:
        return "주의"
    if row["smart_194_raw"] >= 50:
        return "주의"
    return "정상"


def combine_level(a: str, b: str) -> str:
    order = {"정상": 0, "주의": 1, "위험": 2}
    inv = {0: "정상", 1: "주의", 2: "위험"}
    return inv[max(order.get(a, 0), order.get(b, 0))]


def reasons_actions(row: pd.Series, prob: float) -> tuple[list[str], list[str]]:
    reasons, actions = [], []
    if row["smart_5_raw"] >= 100:
        reasons.append(f"재할당섹터(5) {row['smart_5_raw']} — 매우 높음")
        actions.append("중요 데이터 즉시 백업 후 디스크 교체를 강하게 권장합니다.")
    elif row["smart_5_raw"] > 0:
        reasons.append(f"재할당섹터(5) {row['smart_5_raw']} — 불량 섹터 대체 이력 있음")
        actions.append("중요 데이터 백업 후 디스크 교체 여부를 검토하세요.")
    if row["smart_197_raw"] > 0:
        reasons.append(f"대기섹터(197) {row['smart_197_raw']} — 불량 의심 섹터 존재")
        actions.append("디스크 검사를 수행하고 즉시 백업을 권장합니다.")
    if row["smart_198_raw"] > 0:
        reasons.append(f"정정불가섹터(198) {row['smart_198_raw']} — 복구 불가능 섹터 존재")
        actions.append("즉시 백업 후 디스크 교체를 권장합니다.")
    if row["smart_187_raw"] > 0:
        reasons.append(f"에러(187) {row['smart_187_raw']} — 수정 불가능 오류 보고")
        actions.append("디스크 오류 로그 확인 및 교체 준비가 필요합니다.")
    if row["smart_188_raw"] > 0:
        reasons.append(f"명령타임아웃(188) {row['smart_188_raw']} — 명령 처리 지연")
        actions.append("SATA/전원 케이블, 컨트롤러, 디스크 상태를 점검하세요.")
    if row["smart_199_raw"] > 0:
        reasons.append(f"CRC오류(199) {row['smart_199_raw']} — 전송 오류 발생")
        actions.append("데이터 케이블/포트 접촉 상태를 점검하세요.")
    if row["smart_194_raw"] >= 50:
        reasons.append(f"온도(194) {row['smart_194_raw']}℃ — 온도 높음")
        actions.append("케이스 내부 공기 흐름과 냉각 상태를 확인하세요.")
    if not reasons:
        reasons.append("주요 SMART 이상 지표가 크게 감지되지 않았습니다.")
        actions.append("정기 모니터링을 유지하세요.")
    return reasons, list(dict.fromkeys(actions))


def predict(df: pd.DataFrame, model) -> dict[str, Any]:
    prob = float(model.predict_proba(df)[0][1])
    t = threshold()
    pred = int(prob >= t)
    row = df.iloc[0]
    ml = prob_to_level(prob)
    rule = rule_level(row)
    final = combine_level(ml, rule)
    reasons, actions = reasons_actions(row, prob)
    return {"prob": prob, "threshold": t, "pred": pred, "ml_level": ml, "rule_level": rule, "final": final, "reasons": reasons, "actions": actions}


def save_log(df: pd.DataFrame, result: dict, device: str):
    row = df.iloc[0].to_dict()
    out = pd.DataFrame([{
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "device": device,
        **row,
        "ml_probability": result["prob"],
        "ml_level": result["ml_level"],
        "smart_rule_level": result["rule_level"],
        "final_level": result["final"],
    }])
    if LOG_PATH.exists():
        out = pd.concat([pd.read_csv(LOG_PATH), out], ignore_index=True)
    out.to_csv(LOG_PATH, index=False, encoding="utf-8-sig")


def demo_disks() -> list[dict[str, Any]]:
    return [
        {"status": "위험", "serial": "ZA12B9KL", "model": "Seagate ST4000DM000", "capacity": "4TB", "risk": 92, "hours": "38,210h", "s5": 120, "s197": 48, "s198": 32, "s187": 2, "s188": 0, "s199": 0, "temp": 36},
        {"status": "주의", "serial": "ZB34C7MN", "model": "WDC WD40EFRX", "capacity": "4TB", "risk": 61, "hours": "29,540h", "s5": 16, "s197": 4, "s198": 0, "s187": 9, "s188": 0, "s199": 0, "temp": 39},
        {"status": "주의", "serial": "ZC56D1PQ", "model": "HGST HMS5C4040", "capacity": "4TB", "risk": 44, "hours": "41,002h", "s5": 8, "s197": 2, "s198": 0, "s187": 3, "s188": 0, "s199": 0, "temp": 41},
        {"status": "주의", "serial": "ZD78E3RS", "model": "Seagate ST8000NM0055", "capacity": "8TB", "risk": 38, "hours": "22,880h", "s5": 5, "s197": 1, "s198": 0, "s187": 0, "s188": 4, "s199": 0, "temp": 35},
        {"status": "정상", "serial": "ZE90F5TU", "model": "ST12000NM0007", "capacity": "12TB", "risk": 8, "hours": "12,300h", "s5": 0, "s197": 0, "s198": 0, "s187": 0, "s188": 0, "s199": 0, "temp": 31},
        {"status": "정상", "serial": "ZF11G7VW", "model": "WD40EFRX", "capacity": "4TB", "risk": 5, "hours": "9,870h", "s5": 0, "s197": 0, "s198": 0, "s187": 0, "s188": 0, "s199": 0, "temp": 33},
        {"status": "정상", "serial": "ZG22H9XY", "model": "ST4000DM000", "capacity": "4TB", "risk": 3, "hours": "5,420h", "s5": 0, "s197": 0, "s198": 0, "s187": 0, "s188": 0, "s199": 0, "temp": 32},
    ]


def current_disk_to_card(df: pd.DataFrame, result: dict[str, Any]) -> dict[str, Any]:
    row = df.iloc[0]
    return {
        "status": result["final"],
        "serial": "LOCAL-DISK",
        "model": str(row["model"]),
        "capacity": f"{row['capacity_bytes'] / 1_000_000_000:.0f}GB" if row["capacity_bytes"] else "Unknown",
        "risk": round(float(result.get("prob", 0) or 0) * 100, 2),
        "hours": f"{int(row['smart_9_raw']):,}h",
        "s5": int(row["smart_5_raw"]),
        "s197": int(row["smart_197_raw"]),
        "s198": int(row["smart_198_raw"]),
        "s187": int(row["smart_187_raw"]),
        "s188": int(row["smart_188_raw"]),
        "s199": int(row["smart_199_raw"]),
        "temp": int(row["smart_194_raw"]),
        "ml_level": result["ml_level"],
        "rule_level": result["rule_level"],
        "reasons": result["reasons"],
        "actions": result["actions"],
    }


def level_class(level: str) -> str:
    return {"정상": "ok", "주의": "warn", "위험": "danger"}.get(level, "ok")


def render_header():
    st.markdown(
        """
        <div class="pdfs-header">
          <div class="logo">
            <div class="mark">P</div>
            <b>PDFS</b><span>Predictive Drive Failure System</span>
          </div>
          <div class="live"><span class="dot"></span> 실시간 연결됨 · 로컬 SMART 모니터링</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_summary(disks: list[dict]):
    total = len(disks)
    ok = sum(d["status"] == "정상" for d in disks)
    warn = sum(d["status"] == "주의" for d in disks)
    danger = sum(d["status"] == "위험" for d in disks)
    st.markdown(
        f"""
        <div class="section-title">전체 현황</div>
        <div class="summary">
          <div class="stat total"><div class="label">전체 디스크</div><div class="num">{total}</div><div class="sub">모니터링 중</div></div>
          <div class="stat ok"><div class="label">● 정상</div><div class="num ok">{ok}</div><div class="sub">위험도 30% 미만</div></div>
          <div class="stat warn"><div class="label">● 주의</div><div class="num warn">{warn}</div><div class="sub">위험도 30~70%</div></div>
          <div class="stat danger"><div class="label">● 위험</div><div class="num danger">{danger}</div><div class="sub">위험도 70% 이상 또는 SMART 치명 지표</div></div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_charts(disks: list[dict]):
    total = len(disks)
    ok = sum(d["status"] == "정상" for d in disks)
    warn = sum(d["status"] == "주의" for d in disks)
    danger = sum(d["status"] == "위험" for d in disks)
    ok_pct = ok / total * 100 if total else 0
    warn_pct = warn / total * 100 if total else 0
    danger_pct = danger / total * 100 if total else 0
    danger_start = ok_pct + warn_pct
    st.markdown(
        f"""
        <div class="section-title">시스템 분석</div>
        <div class="charts">
          <div class="chart-card">
            <h4>위험도 분포</h4>
            <div class="donut-wrap">
              <div class="donut" style="background:conic-gradient(var(--ok) 0 {ok_pct:.1f}%, var(--warn) {ok_pct:.1f}% {danger_start:.1f}%, var(--danger) {danger_start:.1f}% 100%);">
                <div class="center"><div><div class="big">{total}</div><div class="lbl">전체</div></div></div>
              </div>
              <div class="legend">
                <div class="item"><span class="sw" style="background:var(--ok)"></span>정상<span class="cnt">{ok}</span></div>
                <div class="item"><span class="sw" style="background:var(--warn)"></span>주의<span class="cnt">{warn}</span></div>
                <div class="item"><span class="sw" style="background:var(--danger)"></span>위험<span class="cnt">{danger}</span></div>
              </div>
            </div>
          </div>
          <div class="chart-card">
            <h4>최근 7일 위험·주의 디스크 추이</h4>
            <div class="bars">
              <div class="bar-col"><span class="bv">2</span><div class="bar2" style="height:35%"></div><span class="bk">월</span></div>
              <div class="bar-col"><span class="bv">2</span><div class="bar2" style="height:35%"></div><span class="bk">화</span></div>
              <div class="bar-col"><span class="bv">3</span><div class="bar2" style="height:55%"></div><span class="bk">수</span></div>
              <div class="bar-col"><span class="bv">3</span><div class="bar2" style="height:55%"></div><span class="bk">목</span></div>
              <div class="bar-col"><span class="bv">3</span><div class="bar2" style="height:55%"></div><span class="bk">금</span></div>
              <div class="bar-col peak"><span class="bv">{warn + danger}</span><div class="bar2" style="height:78%"></div><span class="bk">토</span></div>
              <div class="bar-col peak"><span class="bv">{warn + danger}</span><div class="bar2" style="height:78%"></div><span class="bk">오늘</span></div>
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_risk_cards(disks: list[dict]):
    st.markdown('<div class="section-title">⚠ 주의가 필요한 디스크</div>', unsafe_allow_html=True)

    risky = [d for d in disks if d["status"] != "정상"]
    risky = sorted(risky, key=lambda x: x["risk"], reverse=True)

    if not risky:
        st.markdown(
            """
            <div class="risk-card ok">
              <div class="bar"></div>
              <b>현재 주의/위험 디스크가 없습니다.</b>
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    # Streamlit이 큰 HTML 블록을 문자 그대로 보여주는 환경이 있어서,
    # 카드 전체를 한 번에 join하지 않고 columns + 개별 st.markdown으로 렌더링한다.
    for i in range(0, len(risky), 2):
        cols = st.columns(2)
        for col, d in zip(cols, risky[i:i + 2]):
            cls = level_class(d["status"])
            html = f"""
            <div class="risk-card {cls}">
              <div class="bar"></div>
              <div class="risk-head">
                <div>
                  <div class="disk-name">{d['serial']}</div>
                  <div class="disk-model">{d['model']} · {d['capacity']}</div>
                </div>
                <span class="badge {cls}">{d['status']}</span>
              </div>
              <div class="risk-meter">
                <div class="top">
                  <span>고장 위험도</span>
                  <span class="val">{d['risk']}%</span>
                </div>
                <div class="track">
                  <div class="fill {cls}" style="width:{min(100, d['risk'])}%"></div>
                </div>
              </div>
              <div class="smart-row">
                <div class="smart">
                  <span class="k">재할당섹터(5)</span>
                  <span class="v {'bad' if d['s5'] else ''}">{d['s5']}</span>
                </div>
                <div class="smart">
                  <span class="k">대기섹터(197)</span>
                  <span class="v {'bad' if d['s197'] else ''}">{d['s197']}</span>
                </div>
                <div class="smart">
                  <span class="k">정정불가(198)</span>
                  <span class="v {'bad' if d['s198'] else ''}">{d['s198']}</span>
                </div>
              </div>
            </div>
            """
            with col:
                st.markdown(html, unsafe_allow_html=True)


def render_table(disks: list[dict]):
    st.markdown('<div class="section-title">전체 디스크 목록</div>', unsafe_allow_html=True)

    if not disks:
        st.info("표시할 디스크가 없습니다.")
        return

    rows = []
    for d in disks:
        status_icon = {"정상": "🟢 정상", "주의": "🟡 주의", "위험": "🔴 위험"}.get(d["status"], d["status"])
        risk = d.get("risk", 0)
        try:
            risk_float = float(risk)
            risk_text = "-" if pd.isna(risk_float) else f"{risk_float:.2f}%"
        except Exception:
            risk_text = str(risk)

        rows.append({
            "상태": status_icon,
            "디스크": d.get("serial", "-"),
            "모델": d.get("model", "-"),
            "용량": d.get("capacity", "-"),
            "고장 위험도": risk_text,
            "가동시간": d.get("hours", "-"),
        })

    table_df = pd.DataFrame(rows)
    st.dataframe(table_df, use_container_width=True, hide_index=True)


def render_toast(disks: list[dict]):
    worst = max(disks, key=lambda x: x["risk"]) if disks else None
    if worst and worst["status"] == "위험":
        st.markdown(
            f"""
            <div class="toast">
              <div class="th">⚠ 고장 위험 감지</div>
              <div class="tb"><b>{worst['serial']}</b> · {worst['model']}<br>
              고장 위험도 <b style="color:var(--danger)">{worst['risk']}%</b> — 백업 및 점검 권장</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_detail(d: dict[str, Any]):
    cls = level_class(d["status"])
    gauge_color = {"danger": "var(--danger)", "warn": "var(--warn)", "ok": "var(--ok)"}[cls]
    st.markdown(
        f"""
        <div class="disk-header">
          <div>
            <div class="name">{d['serial']} <span class="badge {cls}">{d['status']}</span></div>
            <div class="disk-meta">
              <div><span class="k">모델</span><span class="v">{d['model']}</span></div>
              <div><span class="k">용량</span><span class="v">{d['capacity']}</span></div>
              <div><span class="k">가동시간</span><span class="v">{d['hours']}</span></div>
              <div><span class="k">마지막 수집</span><span class="v">방금 전</span></div>
            </div>
          </div>
        </div>

        <div class="section-title">예측 결과</div>
        <div class="two-col">
          <div class="card">
            <h4>고장 위험도</h4>
            <div class="gauge-wrap">
              <div class="gauge" style="background:conic-gradient({gauge_color} 0 {min(100, d['risk'])}%, var(--bg-card2) {min(100, d['risk'])}% 100%);">
                <div class="c"><div><div class="pct" style="color:{gauge_color}">{d['risk']}%</div><div class="lbl">위험도</div></div></div>
              </div>
              <div class="gauge-status" style="color:{gauge_color}">● {d['status']}</div>
            </div>
          </div>
          <div class="card predict">
            <h4>예측 분석</h4>
            <div class="headline" style="color:{gauge_color}">⚠ 저장장치 {d['status']} 상태</div>
            <div class="desc">머신러닝 모델의 고장 위험 확률과 SMART 규칙 기반 판단을 결합해 최종 등급을 산출했습니다.</div>
            <div class="reason-tags">
              <span class="rtag">재할당섹터(5) <b>{d['s5']}</b></span>
              <span class="rtag">대기섹터(197) <b>{d['s197']}</b></span>
              <span class="rtag">정정불가섹터(198) <b>{d['s198']}</b></span>
            </div>
            <div class="action-box">
              <div style="color:var(--text-dim);font-size:12px;margin-bottom:5px;">권장 조치</div>
              {'<br>'.join(d.get('actions', ['중요 데이터 백업 후 디스크 상태를 점검하세요.']))}
            </div>
          </div>
        </div>

        <div class="section-title">핵심 SMART 현재값</div>
        <div class="smart-grid">
          <div class="sc {'bad' if d['s5'] else ''}"><div class="k">재할당섹터 (5)</div><div class="v">{d['s5']}</div></div>
          <div class="sc {'bad' if d['s197'] else ''}"><div class="k">대기섹터 (197)</div><div class="v">{d['s197']}</div></div>
          <div class="sc {'bad' if d['s198'] else ''}"><div class="k">정정불가 (198)</div><div class="v">{d['s198']}</div></div>
          <div class="sc {'warn' if d['s187'] else ''}"><div class="k">에러 (187)</div><div class="v">{d['s187']}</div></div>
          <div class="sc {'warn' if d['s188'] else ''}"><div class="k">명령타임아웃 (188)</div><div class="v">{d['s188']}</div></div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def load_log_as_disks() -> list[dict[str, Any]]:
    if not LOG_PATH.exists():
        return []

    df = pd.read_csv(LOG_PATH)

    # 같은 device/model 중복 진단은 마지막 행만 사용
    if "timestamp" in df.columns:
        df = df.sort_values("timestamp")
    dedupe_cols = [c for c in ["device", "model"] if c in df.columns]
    if dedupe_cols:
        df = df.drop_duplicates(subset=dedupe_cols, keep="last")

    df = df.tail(5)

    disks = []
    for _, r in df.iterrows():
        prob = r.get("ml_probability", 0)
        try:
            prob = float(prob)
            if pd.isna(prob):
                prob = 0.0
        except Exception:
            prob = 0.0

        cap = r.get("capacity_bytes", 0)
        try:
            cap = float(cap)
            if pd.isna(cap) or cap <= 0:
                capacity_text = "Unknown"
            else:
                capacity_text = f"{cap / 1_000_000_000:.0f}GB"
        except Exception:
            capacity_text = "Unknown"

        disks.append({
            "status": str(r.get("final_level", "정상")),
            "serial": str(r.get("device", "LOCAL")),
            "model": str(r.get("model", "Unknown")),
            "capacity": capacity_text,
            "risk": round(prob * 100, 2),
            "hours": f"{int(float(r.get('smart_9_raw', 0) or 0)):,}h",
            "s5": int(float(r.get("smart_5_raw", 0) or 0)),
            "s197": int(float(r.get("smart_197_raw", 0) or 0)),
            "s198": int(float(r.get("smart_198_raw", 0) or 0)),
            "s187": int(float(r.get("smart_187_raw", 0) or 0)),
            "s188": int(float(r.get("smart_188_raw", 0) or 0)),
            "s199": int(float(r.get("smart_199_raw", 0) or 0)),
            "temp": int(float(r.get("smart_194_raw", 0) or 0)),
            "actions": ["최근 진단 로그 기반 결과입니다."],
        })
    return disks



# =========================================================
# Main UI
# =========================================================
render_header()
model = load_model()

with st.sidebar:
    st.title("PDFS")
    page = st.radio("화면", ["대시보드", "자동진단", "수동진단", "디스크 상세", "모델 성능", "컬럼 설명"])
    st.divider()
    use_demo = st.toggle("목업 더미 데이터 표시", value=True)
    st.caption("업로드된 mockup 스타일에 맞춘 Streamlit 버전")

if "demo_injected" not in st.session_state:
    st.session_state.demo_injected = use_demo

if "real_disks" not in st.session_state:
    st.session_state.real_disks = load_log_as_disks()

if use_demo:
    disks = demo_disks() + st.session_state.real_disks
else:
    disks = st.session_state.real_disks

if page == "대시보드":
    render_summary(disks)
    render_charts(disks)

    st.markdown('<div class="section-title">데모 제어</div>', unsafe_allow_html=True)
    st.markdown(
        """
        <div class="demo-panel">
          <div><b>발표용 데모 모드</b><p>Backblaze 고장 직전 디스크 예시를 대시보드에 표시합니다. 실제 진단은 자동진단 메뉴에서 수행합니다.</p></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    render_risk_cards(disks)
    render_table(disks)
    render_toast(disks)

elif page == "자동진단":
    st.markdown('<div class="section-title">저장장치 자동진단</div>', unsafe_allow_html=True)

    if model is None:
        st.error(f"모델 파일이 없습니다: {MODEL_PATH}")
    elif not smartctl_available():
        st.error("smartctl을 찾을 수 없습니다. smartmontools 설치 후 다시 실행하세요.")
        st.code("winget install smartmontools.smartmontools")
    else:
        col1, col2 = st.columns([1, 2])
        with col1:
            if st.button("디스크 목록 조회", type="primary"):
                try:
                    st.session_state.devices = scan_devices()
                    st.success(f"{len(st.session_state.devices)}개 감지")
                except Exception as e:
                    st.exception(e)

        devices = st.session_state.get("devices", [])
        options = [" ".join(d) for d in devices]
        selected = st.selectbox("진단할 디스크", options) if options else st.text_input("디스크 인자 직접 입력", value="/dev/sda -d ata")
        device_args = shlex.split(selected)

        c1, c2 = st.columns(2)
        with c1:
            if st.button("현재 상태 자동 진단", type="primary"):
                try:
                    df = extract_features(device_args)
                    result = predict(df, model)
                    save_log(df, result, " ".join(device_args))
                    card = current_disk_to_card(df, result)
                    st.session_state.real_disks = [card] + [d for d in st.session_state.real_disks if d["serial"] != card["serial"]]
                    st.success("진단 완료. 대시보드에도 반영했습니다.")
                    render_detail(card)
                except Exception as e:
                    st.exception(e)

        with c2:
            if st.button("SMART 활성화 시도"):
                try:
                    ok, msg = enable_smart(device_args)
                    st.success("SMART 활성화 명령 실행") if ok else st.error("SMART 활성화 실패. 관리자 권한이 필요할 수 있습니다.")
                    st.code(msg or "출력 없음")
                except Exception as e:
                    st.exception(e)

elif page == "수동진단":
    st.markdown('<div class="section-title">저장장치 수동진단</div>', unsafe_allow_html=True)
    if model is None:
        st.error(f"모델 파일이 없습니다: {MODEL_PATH}")
    else:
        c1, c2 = st.columns(2)
        with c1:
            model_name = st.text_input("모델명", value="ST4000DM000")
            capacity_tb = st.number_input("용량(TB)", min_value=0.1, value=4.0)
            smart_5 = st.number_input("재할당섹터(5)", min_value=0, value=0)
            smart_9 = st.number_input("가동시간(9)", min_value=0, value=10000)
            smart_187 = st.number_input("에러(187)", min_value=0, value=0)
        with c2:
            smart_188 = st.number_input("명령타임아웃(188)", min_value=0, value=0)
            smart_194 = st.number_input("온도(194)", min_value=0, value=35)
            smart_197 = st.number_input("대기섹터(197)", min_value=0, value=0)
            smart_198 = st.number_input("정정불가(198)", min_value=0, value=0)
            smart_199 = st.number_input("CRC오류(199)", min_value=0, value=0)
        if st.button("수동 진단", type="primary"):
            df = pd.DataFrame([{
                "model": model_name,
                "capacity_bytes": int(capacity_tb * 1_000_000_000_000),
                "smart_5_raw": smart_5,
                "smart_9_raw": smart_9,
                "smart_187_raw": smart_187,
                "smart_188_raw": smart_188,
                "smart_194_raw": smart_194,
                "smart_197_raw": smart_197,
                "smart_198_raw": smart_198,
                "smart_199_raw": smart_199,
            }], columns=FEATURES)
            result = predict(df, model)
            card = current_disk_to_card(df, result)
            card["serial"] = "MANUAL"
            render_detail(card)

elif page == "디스크 상세":
    st.markdown('<div class="section-title">디스크 상세</div>', unsafe_allow_html=True)
    if not disks:
        st.warning("표시할 디스크가 없습니다.")
    else:
        serials = [f"{d['serial']} · {d['model']} · {d['status']}" for d in disks]
        chosen = st.selectbox("디스크 선택", serials)
        idx = serials.index(chosen)
        render_detail(disks[idx])

elif page == "모델 성능":
    st.markdown('<div class="section-title">모델 성능</div>', unsafe_allow_html=True)
    for p in [
        SCORE_DIR / "storage_model_scores.csv",
        SCORE_DIR / "storage_recall_model_score.csv",
        SCORE_DIR / "storage_threshold_search.csv",
    ]:
        if p.exists():
            st.markdown(f"### {p.name}")
            st.dataframe(pd.read_csv(p), use_container_width=True)
    if not any(p.exists() for p in [SCORE_DIR / "storage_model_scores.csv", SCORE_DIR / "storage_recall_model_score.csv", SCORE_DIR / "storage_threshold_search.csv"]):
        st.warning("scores 폴더에 저장장치 성능 CSV가 없습니다.")

elif page == "컬럼 설명":
    st.markdown('<div class="section-title">SMART 컬럼 설명</div>', unsafe_allow_html=True)
    desc = pd.DataFrame([
        ["model", "저장장치 모델명", "HDD/SSD 제품 모델명"],
        ["capacity_bytes", "용량", "byte 단위 디스크 용량"],
        ["smart_5_raw", "재할당섹터", "불량 섹터가 예비 영역으로 대체된 횟수"],
        ["smart_9_raw", "가동시간", "디스크 누적 사용 시간"],
        ["smart_187_raw", "에러", "수정 불가능 오류 수"],
        ["smart_188_raw", "명령타임아웃", "명령 처리 지연/실패 횟수"],
        ["smart_194_raw", "온도", "디스크 온도"],
        ["smart_197_raw", "대기섹터", "불량 의심 섹터 수"],
        ["smart_198_raw", "정정불가섹터", "오프라인 검사에서 복구 불가능한 섹터 수"],
        ["smart_199_raw", "CRC오류", "케이블/포트 등 전송 오류 가능성"],
    ], columns=["모델 컬럼명", "화면 표시명", "의미"])
    st.dataframe(desc, use_container_width=True)

st.markdown('<div class="mock-tag">PDFS Streamlit · mockup style</div>', unsafe_allow_html=True)
