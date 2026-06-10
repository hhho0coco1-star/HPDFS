# PDFS 데이터 흐름 · 상태 설계

> Streamlit 단일 앱 기준 — HTTP API·DB 대신 함수 호출·session_state·CSV 로그
> 작성일: 2026-06-02 · 최종 수정: 2026-06-02 (실제 구현 기준 재정비)
> 관련 문서: [02_핵심기능.md](02_핵심기능.md) · [04_기술스택.md](04_기술스택.md) · [05_화면설계.md](05_화면설계.md)

---

## 1. 구조 요약

초기 계획(Spring Boot + FastAPI + PostgreSQL)에서 **Streamlit 단일 앱**으로 단순화됐다.
외부 HTTP 통신 대신 Python 함수 호출, DB 대신 CSV 로그·session_state로 동일한 역할을 수행한다.

```
[smartctl]  →  extract_features()  →  predict()
                                           ↓
                                    save_log() → logs/storage_diagnosis_log.csv
                                           ↓
                               st.session_state["real_disks"]
                                           ↓
                                   대시보드·상세 화면 렌더링
```

---

## 2. 핵심 함수 (앱 내부 API 역할)

### 2-1. 예측 파이프라인

| 함수 | 역할 | 입력 → 출력 |
|------|------|-------------|
| `extract_features(device_args)` | smartctl 실행·파싱 | 디스크 경로 → `pd.DataFrame` (10개 피처) |
| `predict(df, model)` | ML + 규칙 하이브리드 판정 | DataFrame → 예측 결과 dict |
| `rule_level(row)` | 규칙 기반 등급 판정 | Series → `"정상"/"주의"/"위험"` |
| `combine_level(a, b)` | ML·규칙 중 더 높은 등급 채택 | 두 등급 → 최종 등급 |
| `reasons_actions(row, prob)` | 위험 원인·권장 조치 생성 | Series·확률 → 원인 리스트·조치 리스트 |

### 2-2. 데이터 로드·저장

| 함수 | 역할 |
|------|------|
| `load_model()` | `models/storage_best_model.pkl` 로드 (`@st.cache_resource`) |
| `save_log(df, result, device)` | 진단 결과를 `logs/storage_diagnosis_log.csv`에 누적 저장 |
| `load_log_as_disks()` | CSV 로그에서 최근 5개 디스크 결과 로드 → 대시보드 표시용 |
| `demo_disks()` | 발표용 더미 디스크 7개 반환 |
| `scan_devices()` | `smartctl --scan` 실행 → 연결 디스크 목록 |

---

## 3. 예측 결과 구조 (dict)

```python
{
    "prob":       0.92,       # ML 모델 고장 확률 (0.0 ~ 1.0)
    "threshold":  0.5,        # 판정 임계값 (storage_threshold.json 또는 기본 0.5)
    "pred":       1,          # 이진 예측 (0=정상, 1=고장위험)
    "ml_level":   "위험",     # ML 확률 기준 등급
    "rule_level": "위험",     # 규칙 기반 등급
    "final":      "위험",     # 최종 등급 = max(ml_level, rule_level)
    "reasons":    ["대기섹터(197) 48 — 불량 의심 섹터 존재", ...],
    "actions":    ["즉시 백업 후 디스크 교체를 권장합니다.", ...]
}
```

---

## 4. 디스크 카드 구조 (session_state 저장 단위)

대시보드·디스크 상세·알림 렌더링에 공통으로 사용하는 dict 형태.

```python
{
    "status":   "위험",           # 최종 등급
    "serial":   "ZA12B9KL",      # 시리얼 번호 (자동진단: 디바이스 경로, 수동: "MANUAL")
    "model":    "ST4000DM000",
    "capacity": "4TB",
    "risk":     92.0,            # 위험도 % (prob × 100)
    "hours":    "38,210h",       # 가동시간 (smart_9_raw)
    "s5":       120,             # 재할당섹터
    "s197":     48,              # 대기섹터
    "s198":     32,              # 정정불가섹터
    "s187":     2,               # 에러
    "s188":     0,               # 명령타임아웃
    "s199":     0,               # CRC오류
    "temp":     36,              # 온도
    "actions":  ["즉시 백업 후 교체 권장"]
}
```

---

## 5. 상태 관리 (session_state)

| 키 | 타입 | 내용 |
|----|------|------|
| `real_disks` | `list[dict]` | 실제 진단된 디스크 카드 목록 (자동·수동진단 결과) |
| `devices` | `list[list[str]]` | smartctl --scan 결과 (자동진단 화면) |
| `demo_injected` | `bool` | 데모 모드 초기 상태 |

> 화면 전환(사이드바 메뉴 변경) 시 session_state가 유지돼 진단 결과가 대시보드에 반영된다.

---

## 6. 데이터 저장 구조

### 6-1. 진단 로그 (CSV)

경로: `logs/storage_diagnosis_log.csv`

| 컬럼 | 예시 |
|------|------|
| `timestamp` | `2026-06-02 14:32:01` |
| `device` | `/dev/sda -d ata` |
| `model` | `ST4000DM000` |
| `capacity_bytes` | `4000787030016` |
| `smart_5_raw` ~ `smart_199_raw` | SMART 10개 피처 값 |
| `ml_probability` | `0.92` |
| `ml_level` | `위험` |
| `smart_rule_level` | `위험` |
| `final_level` | `위험` |

- 진단할 때마다 행이 추가된다. 같은 device는 최신 행이 대시보드에 표시된다.
- `load_log_as_disks()`가 읽어 대시보드·대시보드 메뉴에 반영.

### 6-2. 모델 파일

| 파일 | 내용 |
|------|------|
| `models/storage_best_model.pkl` | 학습된 GradientBoosting 모델 (joblib) |
| `models/storage_threshold.json` | 판정 임계값 (`{"recommended_threshold": 0.5}`) — 없으면 0.5 기본값 |
| `scores/storage_model_scores.csv` | 7개 모델 비교 결과 (모델 성능 화면에서 표시) |

---

## 7. 위험 등급 판정 로직 (상세)

**ML 확률 → 등급:**

| 확률 범위 | 등급 |
|-----------|------|
| < 0.3 | 정상 |
| 0.3 ≤ 확률 < 0.7 | 주의 |
| ≥ 0.7 | 위험 |

**규칙 기반 강제 판정 (ML 확률과 무관):**

| 조건 | 등급 |
|------|------|
| 대기섹터(197) > 0 또는 정정불가(198) > 0 | 위험 |
| 재할당섹터(5) ≥ 100 | 위험 |
| 에러(187) > 0 | 위험 |
| 재할당(5) > 0 또는 CRC(199) > 0 또는 명령타임아웃(188) > 0 | 주의 |
| 온도(194) ≥ 50℃ | 주의 |

**최종 등급 = max(ML 등급, 규칙 등급)**

---

## 8. 담당 분리 (수정)

| 기능 | 담당 |
|------|------|
| 모델 학습·평가·저장 (`storage_best_model.pkl`) | 데이터분석 (김응석) |
| Streamlit 앱 화면 개발 | 프론트/개발 전체 |
| smartctl 연동·자동진단 검증 | 인프라 (안세웅) |
| `.bat` 실행 스크립트·배포 | 인프라 (안세웅) |
| 수동진단·상세 화면 UI | 프론트 |

---

## 9. 확장 계획 (여유 시)

| 항목 | 방법 |
|------|------|
| F-08 조치 상태 관리 | 디스크 상세에 `st.button` + `session_state` 또는 SQLite |
| 진단 이력 시계열 차트 | CSV 로그 날짜별 집계 → Streamlit 차트 |
| 모델 임계값 조정 UI | `storage_threshold.json` 값을 슬라이더로 조정 |
| MLflow 실험 추적 | 학습 단계에 MLflow 연동 |
