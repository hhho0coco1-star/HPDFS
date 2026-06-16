# HPDFS 작업 목록

> 최종 목표: 온프레미스 EXE → 실무형 인프라 (Docker + Nginx + GitHub Actions CI/CD + AWS EC2 배포)
> 작성일: 2026-06-09 · 최종 수정: 2026-06-15

---

## 10. AWS 배포

### 10-1. Docker Hub 이미지 준비 ✅

> melooong 계정 기준. 2026-06-15 빌드 완료.

- [x] Docker Hub 로그인 (melooong)
- [x] `melooong/pdfs-backend:latest` 빌드 + push
- [x] `melooong/pdfs-frontend:latest` 빌드 + push
- [x] `melooong/pdfs-nginx:latest` 빌드 + push

### 10-2. 팀원 AWS EC2 준비 (팀원 담당)

- [ ] EC2 t2.micro 인스턴스 생성
- [ ] 보안 그룹 80포트 오픈
- [ ] Docker + Docker Compose 설치
- [ ] SSH 키(.pem) + 퍼블릭 IP 공유

### 10-3. GitHub Actions CI/CD 구성

- [ ] `.github/workflows/deploy.yml` 작성
- [ ] GitHub Secrets 등록 (DOCKERHUB_USERNAME, DOCKERHUB_TOKEN, EC2_HOST, EC2_SSH_KEY, EC2_USER)
- [ ] main 브랜치 push → 자동 빌드/배포 동작 확인

### 10-4. 배포 확인

- [ ] EC2에서 `docker-compose up` 정상 동작 확인
- [ ] `http://{EC2_IP}` 브라우저 접속 확인
- [ ] Agent → EC2 API 전송 동작 확인

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
