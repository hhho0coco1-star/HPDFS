from __future__ import annotations

import time
from datetime import datetime
from uuid import uuid4

import requests

from config import API_URL, INTERVAL_MINUTES, REQUEST_TIMEOUT
from smart_collector import extract_features, scan_devices


def log(msg: str):
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}")


def collect_and_send():
    try:
        devices = scan_devices()
        log(f"디스크 {len(devices)}개 감지")
        scan_id = datetime.now().strftime("%Y%m%d%H%M%S") + "-" + uuid4().hex[:8]
    except Exception as e:
        log(f"디스크 스캔 실패: {e}")
        return

    for device in devices:
        device_str = " ".join(device)
        try:
            df = extract_features(device)
            row = df.iloc[0].to_dict()
            payload = {
                "scan_id":        scan_id,
                "serial":         str(row.get("serial", "UNKNOWN")),
                "device":         device_str,
                "model":          str(row.get("model", "Unknown")),
                "capacity_bytes": int(row.get("capacity_bytes", 0)),
                "smart_5_raw":    int(row.get("smart_5_raw", 0)),
                "smart_9_raw":    int(row.get("smart_9_raw", 0)),
                "smart_187_raw":  int(row.get("smart_187_raw", 0)),
                "smart_188_raw":  int(row.get("smart_188_raw", 0)),
                "smart_194_raw":  int(row.get("smart_194_raw", 0)),
                "smart_197_raw":  int(row.get("smart_197_raw", 0)),
                "smart_198_raw":  int(row.get("smart_198_raw", 0)),
                "smart_199_raw":  int(row.get("smart_199_raw", 0)),
            }

            res = requests.post(
                f"{API_URL}/api/diagnose",
                json=payload,
                timeout=REQUEST_TIMEOUT,
            )
            result = res.json()
            serial = row.get("serial", "UNKNOWN")
            log(f"{device_str} [{serial}] → {result.get('final_level', '?')} (위험도 {result.get('risk', 0)}%)")

        except requests.exceptions.ConnectionError:
            log(f"{device_str} 전송 실패: API 서버에 연결할 수 없습니다. ({API_URL})")
        except Exception as e:
            log(f"{device_str} 오류: {e}")


if __name__ == "__main__":
    log(f"PDFS 에이전트 시작 — {INTERVAL_MINUTES}분 간격 수집 ({API_URL})")
    log("종료하려면 Ctrl+C 또는 터미널을 닫으세요.")
    print("-" * 60)

    collect_and_send()  # 시작 즉시 1회 실행

    while True:
        time.sleep(INTERVAL_MINUTES * 60)
        collect_and_send()
