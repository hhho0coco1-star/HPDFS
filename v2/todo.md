# HPDFS 작업 목록

> 최종 목표: 온프레미스 EXE → 실무형 인프라 (Docker + Nginx + GitHub Actions CI/CD)
> 작성일: 2026-06-09 · 최종 수정: 2026-06-19 · 상태: 완료

---

## 10. 배포 준비 ✅

### 10-1. Docker Hub 이미지 준비 ✅

> melooong 계정 기준. 2026-06-15 빌드 완료.

- [x] Docker Hub 로그인 (melooong)
- [x] `melooong/pdfs-backend:latest` 빌드 + push
- [x] `melooong/pdfs-frontend:latest` 빌드 + push
- [x] `melooong/pdfs-nginx:latest` 빌드 + push

### 10-3. GitHub Actions CI/CD 구성

- [x] `.github/workflows/deploy.yml` 작성
