# HPDFS 작업 목록

> 최종 목표: 온프레미스 EXE → 실무형 인프라 (Docker + Nginx + Kubernetes + GitHub Actions CI/CD)
> 작성일: 2026-06-09 · 최종 수정: 2026-06-10

---

## 전체 아키텍처 목표

```
GitHub push
    ↓
[GitHub Actions CI/CD]
  → Docker 이미지 빌드
  → 테스트 실행
  → 서버 자동 배포
    ↓
[서버 — Docker Compose]
  ├── Nginx        (포트 80 — 라우팅)
  ├── FastAPI      (포트 8010)
  ├── Streamlit    (포트 8501)
  └── PostgreSQL   (포트 5432)
    ↓
[Kubernetes]
  → Pod 자동 재시작
  → 무중단 배포
  → 스케일 관리
```

---

## 진행 현황

- [x] EXE 포터블 배포 완료 (HPDFS.zip)
- [x] ML 모델 학습 완료 (storage · battery · symptom)
- [x] 기획 문서 최신화
- [x] 인프라 설계 (docs/07_클라우드전환설계.md)
- [x] backend/ 폴더 구조 + FastAPI 완성
- [x] agent/ 폴더 구조 + 에이전트 완성

---

## 1단계 — FastAPI 백엔드 ✅ 완료

### 1-1. predictor.py — ML 예측 코드 이식 ✅
### 1-2. requirements.txt — 의존성 정의 ✅
### 1-3. database.py — PostgreSQL 연결 ✅
### 1-4. models.py — DB 테이블 정의 ✅
### 1-5. router_diagnose.py — POST /api/diagnose ✅
### 1-6. router_disks.py — 조회·수정 API ✅
### 1-7. main.py — 전체 연결 ✅
### 1-8. 로컬 테스트 ✅

---

## 2단계 — 로컬 에이전트 ✅ 완료

### 2-1. agent/ 폴더 구조 생성 ✅
### 2-2. smart_collector.py — SMART 수집 ✅
### 2-3. config.py — 설정 ✅
### 2-4. agent.py — 수집·전송 메인 ✅
### 2-5. start_agent.bat / stop_agent.bat ✅
### 2-6. 에이전트 테스트 ✅

---

## 3단계 — Streamlit 대시보드 리팩토링

### 3-1. frontend/ 폴더 생성
- [x] frontend/app.py (기존 app_hpdfs_portable.py 기반)
- [x] frontend/requirements.txt

### 3-2. 데이터 소스 교체
- [x] CSV/session_state → GET /api/disks 호출로 교체
- [x] 자동진단 화면 → 에이전트 상태 안내로 교체
- [x] 수동진단 → POST /api/diagnose 호출로 교체
- [x] 데모 토글 → POST /api/demo 호출로 교체

### 3-3. F-08 조치 상태 UI 추가
- [x] 디스크 상세 화면에 상태 버튼 3개 (미확인→확인됨→조치완료)
- [x] 버튼 클릭 → PATCH /api/disks/{serial}/status 호출

### 3-4. 로컬 테스트
- [x] streamlit run app.py 실행
- [x] API 데이터 대시보드 표시 확인
- [x] F-08 버튼 동작 확인
- [x] UI 다크 테마 통일 (버튼, 드롭다운, 테이블, 컬럼설명)
- [x] Streamlit 기본 메뉴바 숨김

---

## 4단계 — 코드 개선 / 리팩토링 (Docker 전 필수)

> 프로젝트 전체 분석 후 발견한 설계 결함·정리 항목. Docker화 전에 처리.

### 4-1. 🔴 디스크 식별을 serial_number 기반으로 변경 ✅
- [x] agent/smart_collector.py — extract_features에서 serial_number 추출
- [x] agent/agent.py — payload에 serial 포함
- [x] backend/router_diagnose.py — SmartData에 serial 필드 추가
- [x] backend/router_diagnose.py — Disk 식별을 device → serial로 변경
- [x] backend/models.py — device는 참고용 컬럼으로 분리
- [x] DB 초기화 + device 컬럼 추가

### 4-2. 🔴 수동진단(MANUAL) DB 오염 방지 ✅
- [x] router_diagnose.py — serial == MANUAL이면 DB 저장 건너뛰고 결과만 반환
- [x] frontend/app.py — 수동진단 payload에 serial: MANUAL 포함

### 4-3. 🟡 DB 접속 기본값 일치 ✅
- [x] database.py 기본값을 .env(pdfs:pdfs1234)와 일치

### 4-4. 🟢 안 쓰는 모델 로드 제거 + 주석 정리 ✅
- [x] main.py — battery·symptom 로드 제거 (storage만 로드)
- [x] 불필요 주석 전체 제거

### 4-5. 🟢 CORS 주석 정리 ✅
- [x] main.py — 옛 Streamlit Cloud 주석 제거

### 4-6. 🟢 모델 주입 방식 개선 (app.state) ✅
- [x] router_diagnose.py — 함수 내 import 제거 → app.state 사용

### 4-7. 회귀 테스트 ✅
- [x] 에이전트 재실행 → serial 기반으로 디스크 1건 등록 확인
- [x] 수동진단 실행 → DB에 MANUAL 안 남는지 확인
- [x] 대시보드 정상 표시 확인

---

## 5단계 — Docker 컨테이너화 ✅ 완료

### 5-1. backend/Dockerfile ✅
- [x] Python 베이스 이미지 선택 (python:3.11-slim)
- [x] requirements.txt 설치
- [x] 모델 파일 복사
- [x] uvicorn 실행 CMD 작성
- [x] 빌드 테스트 (docker build)

### 5-2. frontend/Dockerfile ✅
- [x] Python 베이스 이미지 선택
- [x] requirements.txt 설치
- [x] streamlit run 실행 CMD 작성
- [x] 빌드 테스트 (docker build)

### 5-3. Nginx 설정 ✅
- [x] nginx/ 폴더 생성
- [x] nginx.conf 작성
  - /api/* → FastAPI:8010 라우팅
  - /* → Streamlit:8501 라우팅
- [x] nginx/Dockerfile 작성

### 5-4. docker-compose.yml — 전체 통합 ✅
- [x] postgresql 서비스 정의
- [x] backend 서비스 정의 (FastAPI)
- [x] frontend 서비스 정의 (Streamlit)
- [x] nginx 서비스 정의
- [x] 서비스 간 네트워크 연결
- [x] 환경변수 관리 — DB host를 서비스명(postgresql)으로
- [x] 에이전트 config.py API_URL을 서버 주소로 변경

### 5-5. 통합 테스트 ✅
- [x] docker-compose up 실행
- [x] http://localhost 접속 확인
- [x] /api/docs 접속 확인
- [x] 에이전트 → Nginx → FastAPI → DB 흐름 확인

---

## 6단계 — Kubernetes 배포 ✅ 완료

### 6-1. 환경 준비 ✅
- [x] minikube --memory=4096 --cpus=4 로 시작 (메모리 부족 문제 해결)
- [x] kubectl cluster-info 확인

### 6-2. 이미지 로드 ✅
- [x] pdfs-backend:latest, pdfs-frontend:latest, pdfs-nginx:latest 로컬 빌드
- [x] docker save → minikube image load (tar 파일 경유 방식)
> 주의: minikube docker-env 내부 빌드는 캐시 없어 1시간+ 소요. tar 로드 방식 사용.

### 6-3. k8s/ 폴더 및 기반 리소스 작성 ✅
- [x] k8s/namespace.yaml
- [x] k8s/configmap.yaml
- [x] k8s/secret.yaml

### 6-4. PostgreSQL 배포 ✅
- [x] k8s/postgres-pvc.yaml
- [x] k8s/postgres-deployment.yaml
- [x] k8s/postgres-service.yaml

### 6-5. Backend(FastAPI) 배포 ✅
- [x] k8s/backend-deployment.yaml (imagePullPolicy: Never)
- [x] k8s/backend-service.yaml

### 6-6. Frontend(Streamlit) 배포 ✅
- [x] k8s/frontend-deployment.yaml (imagePullPolicy: Never)
- [x] k8s/frontend-service.yaml

### 6-7. Nginx 배포 및 외부 노출 ✅
- [x] k8s/nginx-deployment.yaml (imagePullPolicy: Never)
- [x] k8s/nginx-service.yaml (LoadBalancer)

### 6-8. 배포 및 검증 ✅
- [x] kubectl apply -f k8s/ — 전체 매니페스트 적용
- [x] 4개 Pod 모두 Running 확인
- [x] http://localhost 접속 확인 (minikube tunnel 필요)
- [x] Pod 자동 재시작: backend 삭제 → 2초 내 자동 복구 확인

---

## 버그 수정 / 코드 개선 (프로젝트 전체 분석 결과 — 2026-06-10)

> 전체 코드 분석 후 발견된 문제 목록. 우선순위 순서로 처리.

### 🔴 즉시 수정 (기능 버그)

- [x] **[router_disks.py:59] 진단 이력 조회 버그** ✅
  - DiagnosisLog.serial 컬럼 추가 + 필터 수정 + DB 볼륨 초기화 완료

- [x] **[agent/requirements.txt] 파일 누락** ✅
  - pandas, requests 명세 파일 생성 완료

### 🟡 보안 (GitHub push 전 필수)

- [x] **[k8s/secret.yaml] .gitignore 추가** ✅
- [x] **[k8s/configmap.yaml] DATABASE_URL에서 비밀번호 분리** ✅
  - secret.yaml로 이동, backend-deployment.yaml secretKeyRef로 변경
- [x] **[backend/database.py:9] 하드코딩 비밀번호 제거** ✅
  - 환경변수 없으면 RuntimeError 발생
- [x] **[backend/main.py:30] CORS `allow_origins=["*"]` 제한** ✅
  - ALLOWED_ORIGINS 환경변수 기반으로 변경 (기본값: http://localhost)

### 🟢 개선 권장 (여유 시)

- [x] **[backend/models.py] DiagnosisLog에 serial 컬럼 추가** ✅
- [x] **[k8s/*.yaml] imagePullPolicy: Never → IfNotPresent** ✅
- [x] **[backend/main.py:14] 모델 파일 로드 에러 핸들링** ✅

---

## 7단계 — GitHub Actions CI/CD ✅ 완료

> 방식: A (빌드 + Docker Hub push, 서버 배포 제외)

### 7-1. 사전 준비 ✅
- [x] Docker Hub 계정 생성 (melooong)
- [x] GitHub Secrets 등록 (DOCKER_USERNAME, DOCKER_PASSWORD)
- [x] .gitignore 정비 완료

### 7-2. .github/workflows/deploy.yml 작성 ✅
- [x] 트리거: main 브랜치 push 시 자동 실행
- [x] backend / frontend / nginx 이미지 빌드 + Docker Hub push
- [x] 이미지 태그: latest + git SHA 병행

### 7-3. CI/CD 테스트
- [ ] GitHub Actions 탭에서 워크플로우 실행 확인
- [ ] Docker Hub(melooong)에 이미지 올라갔는지 확인

---

## 8단계 — 아키텍처 시각화 ✅ 완료

- [x] README.md — Mermaid 다이어그램 (v1/v2 아키텍처), 기술스택 비교표, 스크린샷
- [x] v2/docs/presentation.html — 8슬라이드 HTML 발표자료 (애니메이션 효과 포함)
- [x] v2/docs/images/ — 대시보드·디스크상세 스크린샷

---

## 9단계 — 확장 기능 (여유 시)

- [ ] F-09 배터리 예측 UI (battery_best_model.pkl 활용)
- [ ] F-10 증상 예측 UI (symptom_best_model.pkl 활용)
- [ ] Prometheus + Grafana 시스템 모니터링
- [ ] MLflow 실험 추적 연동
