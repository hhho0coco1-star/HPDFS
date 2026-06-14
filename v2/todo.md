# HPDFS 작업 목록

> 최종 목표: 온프레미스 EXE → 실무형 인프라 (Docker + Nginx + Kubernetes + GitHub Actions CI/CD)
> 작성일: 2026-06-09 · 최종 수정: 2026-06-15

---

## 이후 예정 작업 (우선순위 낮음)

### 9-3. 확장 예측 기능

> battery_best_model.pkl, symptom_best_model.pkl 이미 학습 완료. 연동만 하면 됨.

- [ ] `backend/router_battery.py` — POST /api/battery 엔드포인트 추가
- [ ] `backend/main.py` — battery 모델 로드 + 라우터 등록
- [ ] `frontend/app.py` — 배터리 예측 탭 추가
- [ ] `backend/router_symptom.py` — POST /api/symptom 엔드포인트 추가
- [ ] `frontend/app.py` — 증상 예측 탭 추가

### 9-4. 모니터링 대시보드

> API 응답시간, 요청 수, 에러율을 Grafana로 시각화.

- [ ] `backend/requirements.txt`에 prometheus-fastapi-instrumentator 추가
- [ ] `backend/main.py` — /metrics 엔드포인트 노출
- [ ] `docker-compose.yml`에 prometheus + grafana 서비스 추가
- [ ] prometheus.yml 스크레이프 설정
- [ ] Grafana 대시보드 구성 (API 응답시간, 요청수, 에러율)
