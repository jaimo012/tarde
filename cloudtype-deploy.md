# 🚀 클라우드타입(CloudType) 배포 가이드

## 📋 필수 환경변수 설정

클라우드타입에서 다음 환경변수들을 설정해야 합니다:

### 1. DART API 관련
```
DART_API_KEY=your_dart_api_key_here
```
- **설명**: DART 오픈API 인증키
- **획득 방법**: [DART 오픈API](https://opendart.fss.or.kr/) 사이트에서 발급
- **예시**: `95aa8b9247edaaf3fd89be2f0f063c8cdf9893cc`

### 2. 구글 서비스 계정 JSON (Base64 인코딩)
```
GOOGLE_SERVICE_ACCOUNT_JSON=eyJ0eXBlIjoic2VydmljZV9hY2NvdW50...
```
- **설명**: 구글 서비스 계정 JSON 파일을 Base64로 인코딩한 값
- **획득 방법**: Google Cloud Console에서 서비스 계정 JSON 파일 생성 후 Base64 인코딩
- **인코딩 방법**:
  ```bash
  # Windows PowerShell
  [Convert]::ToBase64String([IO.File]::ReadAllBytes("path\to\service-account.json"))
  
  # Linux/macOS
  base64 -i path/to/service-account.json
  ```

### 3. 로그 레벨 (선택사항)
```
LOG_LEVEL=INFO
```
- **설명**: 로그 출력 레벨
- **가능한 값**: `DEBUG`, `INFO`, `WARNING`, `ERROR`
- **기본값**: `INFO`

### 4. 클라우드타입 전용 설정
```
ENVIRONMENT=production
PORT=8080
```
- **ENVIRONMENT**: 실행 환경 (`production`, `development`)
- **PORT**: 클라우드타입에서 사용할 포트 번호

## 🛠️ 클라우드타입 배포 설정

### 1. 빌드 명령어
```bash
pip install --upgrade pip && pip install -r requirements.txt
```

### 2. 시작 명령어
```bash
python run.py
```

### 3. Python 버전
- **권장**: Python 3.8 이상
- **테스트됨**: Python 3.13.2

## 📁 배포용 파일 구조

클라우드타입 배포 시 다음 파일들이 포함되어야 합니다:

```
trade/
├── src/                    # 소스 코드
├── config/                 # 설정 파일
├── logs/                   # 로그 디렉토리 (빈 폴더)
├── requirements.txt        # Python 패키지 의존성
├── run.py                 # 메인 실행 스크립트
├── cloudtype-settings.py  # 클라우드타입 전용 설정
└── README.md              # 프로젝트 문서
```

## ⚙️ 환경별 설정 관리

### 개발 환경 (.env 파일)
```env
DART_API_KEY=your_development_key
GOOGLE_SERVICE_ACCOUNT_JSON=base64_encoded_json
LOG_LEVEL=DEBUG
ENVIRONMENT=development
```

### 프로덕션 환경 (클라우드타입 환경변수)
- 클라우드타입 대시보드에서 직접 설정
- 민감한 정보는 반드시 환경변수로 관리
- 코드에 하드코딩 금지

## 🔒 보안 주의사항

1. **API 키 보호**: 절대 코드에 하드코딩하지 말 것
2. **서비스 계정 JSON**: Base64 인코딩하여 환경변수로 저장
3. **스프레드시트 권한**: 서비스 계정에 최소한의 권한만 부여
4. **로그 관리**: 민감한 정보가 로그에 출력되지 않도록 주의

## 🚨 트러블슈팅

### 자주 발생하는 문제들

1. **구글 인증 오류**
   - 서비스 계정 JSON이 올바르게 Base64 인코딩되었는지 확인
   - 스프레드시트에 서비스 계정 이메일 공유 권한 확인

2. **DART API 오류**
   - API 키 유효성 확인
   - 일일 호출 한도 확인

3. **메모리 부족**
   - 클라우드타입 플랜 확인
   - 대용량 파일 처리 시 스트리밍 방식 사용

4. **타임아웃 오류**
   - 네트워크 타임아웃 설정 조정
   - API 요청 간격 조정

## 📊 모니터링

### 로그 확인
- 클라우드타입 대시보드에서 실시간 로그 확인
- 로그 레벨을 통한 디버깅 정보 조절

### 성능 모니터링
- CPU/메모리 사용률 확인
- API 호출 빈도 모니터링
- 에러 발생률 추적

## 🔄 자동화 설정

### 정기 실행 (선택사항)
클라우드타입에서 크론 작업 설정:
```bash
# 매일 오전 9시 실행
0 9 * * * cd /app && python run.py
```

### 웹훅 연동 (선택사항)
외부 시스템에서 트리거할 수 있도록 웹 엔드포인트 제공
