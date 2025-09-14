# 🌥️ 클라우드타입 환경변수 설정 가이드

## 🚨 중요 보안 공지
**절대 민감한 정보를 코드에 하드코딩하거나 GitHub에 업로드하지 마세요!**  
모든 민감 정보는 클라우드타입 환경변수로만 관리합니다.

---

## 📋 클라우드타입에서 설정해야 할 환경변수

### 1. **DART_API_KEY** (필수)
```
변수명: DART_API_KEY
설명: DART 오픈API 인증키
값 예시: 95aa8b9247edaaf3fd89be2f0f063c8cdf9893cc
```
- **획득 방법**: [DART 오픈API](https://opendart.fss.or.kr/) 사이트에서 회원가입 후 발급
- **주의사항**: 절대 공개하지 말 것

### 2. **GOOGLE_SERVICE_ACCOUNT_JSON** (필수)
```
변수명: GOOGLE_SERVICE_ACCOUNT_JSON
설명: 구글 서비스 계정 JSON을 Base64로 인코딩한 값
값 예시: eyJ0eXBlIjoic2VydmljZV9hY2NvdW50IiwicHJvamVjdF9pZCI6...
```

#### Base64 인코딩 방법:

**Windows PowerShell:**
```powershell
[Convert]::ToBase64String([IO.File]::ReadAllBytes("C:\path\to\service-account.json"))
```

**Linux/macOS:**
```bash
base64 -i /path/to/service-account.json
```

**온라인 도구 (권장하지 않음):**
- 보안상 로컬에서 인코딩하는 것을 강력히 권장

### 3. **SPREADSHEET_URL** (필수)
```
변수명: SPREADSHEET_URL
설명: 구글 스프레드시트 URL
값 예시: https://docs.google.com/spreadsheets/d/1FOreBqJdIfshsbTumxybVzfDOz9dvQGDZTLcQNIy6Q4/edit?usp=sharing
```
- **주의사항**: 서비스 계정에 스프레드시트 편집 권한 부여 필요

### 4. **ENVIRONMENT** (필수)
```
변수명: ENVIRONMENT
설명: 실행 환경 구분
값: production
```
- **고정값**: `production` (클라우드타입에서는 항상 이 값 사용)

### 5. **PORT** (필수)
```
변수명: PORT
설명: 클라우드타입에서 사용할 포트 번호
값: 8080
```
- **기본값**: 8080 (클라우드타입 기본 포트)

### 6. **LOG_LEVEL** (선택사항)
```
변수명: LOG_LEVEL
설명: 로그 출력 레벨
값: INFO
```
- **가능한 값**: `DEBUG`, `INFO`, `WARNING`, `ERROR`
- **기본값**: `INFO`

---

## 🛠️ 클라우드타입 배포 설정

### 빌드 명령어:
```bash
pip install --upgrade pip && pip install -r requirements.txt
```

### 시작 명령어:
```bash
python cloudtype_run.py
```

### Python 버전:
- **권장**: Python 3.8 이상
- **테스트됨**: Python 3.13.2

---

## 🔒 보안 체크리스트

### ✅ 해야 할 것:
- [ ] 모든 민감 정보를 클라우드타입 환경변수로 설정
- [ ] 구글 서비스 계정 JSON을 Base64로 인코딩
- [ ] 스프레드시트에 서비스 계정 이메일 공유 권한 부여
- [ ] DART API 키를 안전하게 보관
- [ ] 환경변수 이름을 정확히 입력

### ❌ 하지 말아야 할 것:
- [ ] 코드에 API 키나 민감 정보 하드코딩
- [ ] GitHub에 서비스 계정 JSON 파일 업로드
- [ ] 공개 저장소에 스프레드시트 URL 노출
- [ ] 환경변수를 공개 채널에 공유

---

## 🚨 트러블슈팅

### 자주 발생하는 오류들:

#### 1. `DART_API_KEY 환경변수가 설정되지 않았습니다`
**원인**: DART_API_KEY 환경변수가 설정되지 않음  
**해결**: 클라우드타입에서 `DART_API_KEY` 환경변수 추가

#### 2. `GOOGLE_SERVICE_ACCOUNT_JSON 환경변수가 설정되지 않았습니다`
**원인**: 구글 서비스 계정 JSON 환경변수가 설정되지 않음  
**해결**: Base64로 인코딩한 JSON을 `GOOGLE_SERVICE_ACCOUNT_JSON`에 설정

#### 3. `구글 서비스 계정 JSON 디코딩 실패`
**원인**: Base64 인코딩이 잘못되었거나 JSON 형식 오류  
**해결**: JSON 파일을 다시 Base64로 인코딩

#### 4. `SPREADSHEET_URL 환경변수가 설정되지 않았습니다`
**원인**: 스프레드시트 URL이 설정되지 않음  
**해결**: 구글 스프레드시트 전체 URL을 `SPREADSHEET_URL`에 설정

#### 5. 스프레드시트 접근 권한 오류
**원인**: 서비스 계정에 스프레드시트 권한이 없음  
**해결**: 구글 스프레드시트에서 서비스 계정 이메일에 편집 권한 부여

---

## 📊 환경변수 설정 예시

클라우드타입 대시보드에서 다음과 같이 설정:

```
DART_API_KEY = 95aa8b9247edaaf3fd89be2f0f063c8cdf9893cc
GOOGLE_SERVICE_ACCOUNT_JSON = eyJ0eXBlIjoic2VydmljZV9hY2NvdW50IiwicHJvamVjdF9pZCI6ImxpZmUtY29vcmRpbmF0b3IiLCJwcml2YXRlX2tleV9pZCI6...
SPREADSHEET_URL = https://docs.google.com/spreadsheets/d/1FOreBqJdIfshsbTumxybVzfDOz9dvQGDZTLcQNIy6Q4/edit?usp=sharing
ENVIRONMENT = production
PORT = 8080
LOG_LEVEL = INFO
```

---

## 🔍 환경변수 검증

애플리케이션 시작 시 자동으로 모든 필수 환경변수가 설정되었는지 검증합니다:

- ✅ **DART_API_KEY**: DART API 인증키 확인
- ✅ **GOOGLE_SERVICE_ACCOUNT_JSON**: Base64 디코딩 및 JSON 형식 검증
- ✅ **SPREADSHEET_URL**: URL 형식 검증
- ✅ **ENVIRONMENT**: production 값 확인

검증 실패 시 명확한 오류 메시지와 함께 애플리케이션이 중단됩니다.

---

## 📞 지원

환경변수 설정 중 문제가 발생하면:
1. 오류 메시지를 정확히 확인
2. 환경변수 이름과 값을 다시 한 번 점검
3. 이 가이드의 트러블슈팅 섹션 참조

**중요**: 민감한 정보는 절대 공개 채널에 공유하지 마세요!
