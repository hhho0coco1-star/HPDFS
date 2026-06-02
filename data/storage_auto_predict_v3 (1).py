import argparse
import json
import re
import shutil
import subprocess
from pathlib import Path

import joblib
import pandas as pd


BASE_DIR = Path(__file__).resolve().parent
MODEL_PATH = BASE_DIR / "models" / "storage_best_model.pkl"

STORAGE_FEATURES = [
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
    5: "smart_5_raw",       # Reallocated Sectors Count
    9: "smart_9_raw",       # Power-On Hours
    187: "smart_187_raw",   # Reported Uncorrectable Errors
    188: "smart_188_raw",   # Command Timeout
    194: "smart_194_raw",   # Temperature Celsius
    197: "smart_197_raw",   # Current Pending Sector Count
    198: "smart_198_raw",   # Offline Uncorrectable Sector Count
    199: "smart_199_raw",   # UDMA CRC Error Count
}


def run_cmd(cmd):
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="ignore",
    )
    if not result.stdout.strip():
        raise RuntimeError(
            "smartctl 실행 결과가 비어 있습니다.\n"
            f"cmd: {' '.join(cmd)}\n"
            f"stderr: {result.stderr}"
        )
    return result.stdout


def parse_scan_line(line):
    pure = line.split("#", 1)[0].strip()
    if not pure:
        return None
    return pure.split()


def scan_devices():
    out = run_cmd(["smartctl", "--scan"])
    devices = []
    for line in out.splitlines():
        args = parse_scan_line(line)
        if args:
            devices.append(args)
    return devices


def read_smart_json(device_args):
    cmd = ["smartctl", "-a", "-j"] + device_args
    out = run_cmd(cmd)
    return json.loads(out)


def get_nested(data, path, default=None):
    cur = data
    for key in path:
        if not isinstance(cur, dict) or key not in cur:
            return default
        cur = cur[key]
    return cur


def safe_int(value, default=0):
    try:
        if value is None:
            return default
        return int(value)
    except Exception:
        return default


def parse_temperature_raw(raw):
    """
    smartctl JSON에서 194 Temperature_Celsius의 raw.value가
    206158823457처럼 비정상적으로 큰 packed integer로 나오는 경우가 있음.
    이때 raw.string의 첫 숫자 또는 value의 하위 1바이트를 온도로 사용한다.
    """
    raw_string = str(raw.get("string", "")).strip()

    # 예: "33 (Min/Max 6/48)" -> 33
    m = re.search(r"-?\d+", raw_string)
    if m:
        return safe_int(m.group(0))

    value = safe_int(raw.get("value", 0))

    # 정상 온도라면 보통 0~100 근처
    if 0 <= value <= 120:
        return value

    # Hitachi 계열에서 packed integer인 경우 하위 byte가 현재 온도인 경우가 많음
    low_byte = value & 0xFF
    if 0 <= low_byte <= 120:
        return low_byte

    return 0


def extract_from_ata(data, row):
    table = get_nested(data, ["ata_smart_attributes", "table"], default=[])

    for attr in table:
        attr_id = attr.get("id")
        col = SMART_ID_TO_COL.get(attr_id)
        if not col:
            continue

        raw = attr.get("raw", {})

        if attr_id == 194:
            row[col] = parse_temperature_raw(raw)
            continue

        value = raw.get("value", 0)
        row[col] = safe_int(value, 0)

    return row


def extract_from_nvme(data, row):
    # NVMe는 ATA SMART ID 5/9/187... 구조가 아님.
    # Backblaze HDD 기반 모델과 완전히 대응되지는 않지만 가능한 값만 매핑한다.
    temp = get_nested(data, ["temperature", "current"], default=None)
    if temp is None:
        temp = get_nested(data, ["nvme_smart_health_information_log", "temperature"], default=None)
    row["smart_194_raw"] = safe_int(temp, 0)

    power_on_hours = get_nested(data, ["power_on_time", "hours"], default=None)
    if power_on_hours is None:
        power_on_hours = get_nested(data, ["nvme_smart_health_information_log", "power_on_hours"], default=None)
    row["smart_9_raw"] = safe_int(power_on_hours, 0)

    return row


def extract_storage_features(device_args):
    data = read_smart_json(device_args)

    model_name = (
        data.get("model_name")
        or data.get("model_number")
        or get_nested(data, ["device", "model_name"], default=None)
        or "Unknown"
    )

    capacity_bytes = get_nested(data, ["user_capacity", "bytes"], default=0)
    capacity_bytes = safe_int(capacity_bytes, 0)

    row = {
        "model": str(model_name),
        "capacity_bytes": capacity_bytes,
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
        row = extract_from_ata(data, row)
    else:
        row = extract_from_nvme(data, row)

    return pd.DataFrame([row], columns=STORAGE_FEATURES)


def model_risk_level(prob):
    if prob < 0.3:
        return "정상"
    if prob < 0.7:
        return "주의"
    return "위험"


def rule_based_level(row):
    """
    머신러닝 모델이 낮은 확률을 내더라도,
    실제 운영 안전상 무시하면 안 되는 SMART 지표를 별도 판정한다.
    """
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


def final_level(model_level, rule_level):
    order = {"정상": 0, "주의": 1, "위험": 2}
    inv = {0: "정상", 1: "주의", 2: "위험"}
    return inv[max(order.get(model_level, 0), order.get(rule_level, 0))]


def make_reasons(row, prob):
    reasons = []
    actions = []

    if row["smart_5_raw"] >= 100:
        reasons.append(f"재할당 섹터 수가 매우 높습니다. 현재 값: {row['smart_5_raw']}")
        actions.append("중요 데이터 즉시 백업 후 디스크 교체를 강하게 권장합니다.")
    elif row["smart_5_raw"] > 0:
        reasons.append(f"재할당 섹터가 발생했습니다. 현재 값: {row['smart_5_raw']}")
        actions.append("중요 데이터 백업 후 디스크 교체 여부를 검토하세요.")

    if row["smart_187_raw"] > 0:
        reasons.append(f"수정 불가능 오류가 보고되었습니다. 현재 값: {row['smart_187_raw']}")
        actions.append("디스크 오류 로그 확인 및 교체 준비가 필요합니다.")

    if row["smart_188_raw"] > 0:
        reasons.append(f"명령 타임아웃이 발생했습니다. 현재 값: {row['smart_188_raw']}")
        actions.append("SATA/전원 케이블, 컨트롤러, 디스크 상태를 점검하세요.")

    if row["smart_197_raw"] > 0:
        reasons.append(f"보류 중인 섹터가 존재합니다. 현재 값: {row['smart_197_raw']}")
        actions.append("디스크 검사를 수행하고 즉시 백업을 권장합니다.")

    if row["smart_198_raw"] > 0:
        reasons.append(f"오프라인 수정 불가능 섹터가 존재합니다. 현재 값: {row['smart_198_raw']}")
        actions.append("즉시 백업 후 디스크 교체를 권장합니다.")

    if row["smart_199_raw"] > 0:
        reasons.append(f"CRC 오류가 발생했습니다. 현재 값: {row['smart_199_raw']}")
        actions.append("데이터 케이블/포트 접촉 상태를 점검하세요.")

    if row["smart_194_raw"] >= 50:
        reasons.append(f"디스크 온도가 높습니다. 현재 온도: {row['smart_194_raw']}℃")
        actions.append("케이스 내부 공기 흐름과 냉각 상태를 확인하세요.")

    if not reasons:
        if prob >= 0.7:
            reasons.append("개별 SMART 지표는 뚜렷하지 않지만, 전체 패턴이 고장 데이터와 유사합니다.")
            actions.append("정밀 검사와 백업을 권장합니다.")
        else:
            reasons.append("주요 SMART 이상 지표가 크게 감지되지 않았습니다.")
            actions.append("정기 모니터링을 유지하세요.")

    # 중복 제거
    actions = list(dict.fromkeys(actions))
    return reasons, actions


def predict_storage(input_df):
    if not MODEL_PATH.exists():
        raise FileNotFoundError(f"모델 파일을 찾을 수 없습니다: {MODEL_PATH}")

    model = joblib.load(MODEL_PATH)
    prob = float(model.predict_proba(input_df)[0][1])
    pred = int(model.predict(input_df)[0])
    return pred, prob


def print_result(device_args, input_df, pred, prob):
    row = input_df.iloc[0]
    m_level = model_risk_level(prob)
    r_level = rule_based_level(row)
    f_level = final_level(m_level, r_level)
    reasons, actions = make_reasons(row, prob)

    print("\n" + "=" * 70)
    print("저장장치 자동 진단 결과")
    print("=" * 70)
    print("device args:", " ".join(device_args))
    print(f"모델명: {row['model']}")
    print(f"용량(bytes): {row['capacity_bytes']}")
    print(f"예측값: {pred}  (0=정상, 1=고장위험)")
    print(f"ML 고장 위험 확률: {prob * 100:.2f}%")
    print(f"ML 위험 등급: {m_level}")
    print(f"SMART 규칙 기반 등급: {r_level}")
    print(f"최종 권고 등급: {f_level}")

    print("\n[수집된 SMART 입력값]")
    for col in STORAGE_FEATURES:
        print(f"- {col}: {row[col]}")

    print("\n[예상 원인]")
    for r in reasons:
        print(f"- {r}")

    print("\n[권장 조치]")
    for a in actions:
        print(f"- {a}")

    print("=" * 70)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--scan", action="store_true", help="smartctl로 감지 가능한 저장장치 목록 출력")
    parser.add_argument("--device", nargs="+", help="예: --device /dev/sda -d ata 또는 --device /dev/nvme0 -d nvme")
    parser.add_argument("--auto-first", action="store_true", help="scan 결과 첫 번째 장치를 자동 선택해서 예측")
    parser.add_argument("--save-input", default="current_storage_input.csv", help="수집 입력 CSV 저장 경로")
    args = parser.parse_args()

    if shutil.which("smartctl") is None:
        raise RuntimeError(
            "smartctl을 찾을 수 없습니다.\n"
            "Windows에서는 smartmontools 설치 후 PATH에 smartctl이 잡혀야 합니다.\n"
            "설치 후 PowerShell에서 smartctl --version 이 되는지 확인하세요."
        )

    if args.scan:
        devices = scan_devices()
        print("[detected devices]")
        for i, dev in enumerate(devices):
            print(f"{i}: {' '.join(dev)}")
        return

    if args.device:
        device_args = args.device
    elif args.auto_first:
        devices = scan_devices()
        if not devices:
            raise RuntimeError("smartctl --scan 결과 감지된 디스크가 없습니다.")
        device_args = devices[0]
        print("[auto selected]", " ".join(device_args))
    else:
        raise RuntimeError(
            "장치를 지정해야 합니다.\n"
            "먼저: py storage_auto_predict_v3.py --scan\n"
            "그다음 예: py storage_auto_predict_v3.py --device /dev/sda -d ata\n"
            "또는: py storage_auto_predict_v3.py --auto-first"
        )

    input_df = extract_storage_features(device_args)
    input_df.to_csv(args.save_input, index=False, encoding="utf-8-sig")
    print("[input saved]", args.save_input)

    pred, prob = predict_storage(input_df)
    print_result(device_args, input_df, pred, prob)


if __name__ == "__main__":
    main()
