# HPDFS 배포용 패키지

SMART 기반 저장장치 고장예측 로컬 모니터링 시스템 배포용 최소 구성입니다.

## 실행 방법

### 자동진단까지 사용할 때
`run_hpdfs_admin.bat`을 더블클릭하세요.

관리자 권한으로 다시 실행한 뒤 Streamlit 대시보드를 엽니다.

### 화면 확인/수동진단만 사용할 때
`run_hpdfs.bat`을 더블클릭하세요.

## 최초 실행 시

필요한 Python 패키지가 없으면 BAT 파일이 자동으로 설치를 시도합니다.

수동으로 먼저 설치하려면:

```powershell
.\install_requirements.bat
```

## smartctl

저장장치 자동진단을 사용하려면 smartmontools가 필요합니다.

```powershell
winget install smartmontools.smartmontools
```

설치 확인:

```powershell
smartctl --version
```

## 포함 파일

```text
app_pdfs_mockup_v3.py
requirements_pdfs.txt
run_hpdfs.bat
run_hpdfs_admin.bat
install_requirements.bat
stop_hpdfs.bat
.streamlit/config.toml
models/storage_best_model.pkl
scores/storage_model_scores.csv
```

## 제외한 파일

배포에 불필요한 학습 코드, 원본 데이터, 배터리/증상 모델, PyInstaller build/dist 파일, 중간 실험 파일은 제거했습니다.
