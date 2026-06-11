# HPDFS 작업 목록

> 최종 목표: 온프레미스 EXE → 실무형 인프라 (Docker + Nginx + Kubernetes + GitHub Actions CI/CD)
> 작성일: 2026-06-09 · 최종 수정: 2026-06-11

---

## 완료된 단계 요약

| 단계 | 내용 | 상태 |
|------|------|------|
| 1단계 | FastAPI 백엔드 (predictor, models, router) | ✅ |
| 2단계 | 로컬 에이전트 (smartctl SMART 수집 · 전송) | ✅ |
| 3단계 | Streamlit 대시보드 리팩토링 | ✅ |
| 4단계 | 코드 개선 (serial 기반 식별, MANUAL 방지, CORS, 보안) | ✅ |
| 5단계 | Docker 컨테이너화 (backend / frontend / nginx / postgres) | ✅ |
| 6단계 | Kubernetes 배포 (minikube, 4개 Pod Running 확인) | ✅ |
| 7단계 | GitHub Actions CI/CD (Docker Hub push, 6회 성공 확인) | ✅ |
| 8단계 | 아키텍처 시각화 (README Mermaid, HTML 발표자료 8슬라이드) | ✅ |
| 중간발표 점검 | 버그 수정 8건, 슬라이드 수정 5건 | ✅ |

---

## 9단계 — 기말발표 대비 추가 작업

### 9-1. k8s 안정성 개선 (난이도: 낮음) — 우선 권장

> Pod 내부 앱이 죽었을 때 k8s가 HTTP 수준으로 감지해 자동 재시작하는 기능.
> resource limits 미설정 시 하나의 Pod가 서버 전체 메모리를 점유할 수 있음.

- [x] `k8s/backend-deployment.yaml` — liveness/readiness probe 추가 (httpGet /)
- [x] `k8s/frontend-deployment.yaml` — liveness/readiness probe 추가 (tcpSocket 8501)
- [x] `k8s/nginx-deployment.yaml` — liveness/readiness probe 추가 (httpGet /)
- [x] `k8s/postgres-deployment.yaml` — liveness/readiness probe 추가 (pg_isready)
- [x] 4개 deployment resource limits/requests 설정 완료
  - backend:  cpu 200m~500m / memory 256Mi~512Mi
  - frontend: cpu 200m~300m / memory 256Mi~512Mi
  - nginx:    cpu 50m~100m  / memory 64Mi~128Mi
  - postgres: cpu 200m~300m / memory 256Mi

---

### 9-2. 단위 테스트 (난이도: 중간)

> 현재 테스트 코드 없음. ML 예측 로직과 API 응답 형식 검증.

- [ ] `backend/tests/` 폴더 생성
- [ ] `backend/tests/test_predictor.py`
  - `prob_to_level()` — 0.1 → 정상, 0.5 → 주의, 0.8 → 위험 검증
  - `rule_level()` — smart_197_raw > 0 이면 위험 검증
  - `combine_level()` — 더 높은 등급이 선택되는지 검증
- [ ] `backend/tests/test_router_diagnose.py`
  - POST /api/diagnose 응답에 serial, final_level, risk, reasons, actions 포함 여부 검증
  - serial == MANUAL 이면 DB 저장 안 되는지 검증
- [ ] `backend/requirements.txt`에 pytest 추가
- [ ] pytest 실행 확인

---

### 9-3. 확장 예측 기능 (난이도: 중간)

> battery_best_model.pkl, symptom_best_model.pkl 이미 학습 완료. 연동만 하면 됨.

- [ ] `backend/router_battery.py` — POST /api/battery 엔드포인트 추가
  - 입력: 배터리 관련 지표
  - 출력: 배터리 상태 등급 + 교체 권장 여부
- [ ] `backend/main.py` — battery 모델 로드 + 라우터 등록
- [ ] `frontend/app.py` — 배터리 예측 탭 추가
- [ ] `backend/router_symptom.py` — POST /api/symptom 엔드포인트 추가
- [ ] `frontend/app.py` — 증상 예측 탭 추가

---

### 9-4. 모니터링 대시보드 (난이도: 높음)

> API 응답시간, 요청 수, 에러율을 Grafana로 시각화.

- [ ] `backend/requirements.txt`에 prometheus-fastapi-instrumentator 추가
- [ ] `backend/main.py` — /metrics 엔드포인트 노출
- [ ] `docker-compose.yml`에 prometheus 서비스 추가 (포트 9090)
- [ ] `docker-compose.yml`에 grafana 서비스 추가 (포트 3000)
- [ ] prometheus.yml 스크레이프 설정 (backend:8010/metrics)
- [ ] Grafana 대시보드 구성 (API 응답시간, 요청수, 에러율)
