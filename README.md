# 📊 DART 공시 스크래핑 및 구글 시트 자동화 시스템

이 시스템은 DART(전자공시시스템)에서 단일판매공급계약 관련 공시를 자동으로 수집하고, 구글 스프레드시트에 정리하는 파이썬 애플리케이션입니다.

## 🎯 주요 기능

1. **구글 스프레드시트 연동**: 분석 대상 회사 목록을 자동으로 가져오고 결과를 저장
2. **DART API 연동**: 공시 검색 및 보고서 다운로드 자동화
3. **보고서 분석**: HTML/XML 보고서에서 계약 정보 자동 추출
4. **중복 제거**: 이미 처리된 보고서는 자동으로 건너뛰기
5. **데이터 분류**: 완전한 데이터는 '계약' 시트에, 불완전한 데이터는 '분석제외' 시트에 자동 분류

## 🚀 시작하기

### 1. 개발환경 설정

#### Python 설치 확인
```bash
py --version  # Python 3.8 이상 필요
```

#### 가상환경 생성 및 활성화
```bash
# 가상환경 생성
py -m venv venv

# 가상환경 활성화 (Windows)
.\venv\Scripts\Activate.ps1

# 가상환경 활성화 (macOS/Linux)
source venv/bin/activate
```

#### 패키지 설치
```bash
pip install --upgrade pip
pip install requests pandas numpy python-dateutil python-dotenv loguru fastapi uvicorn pytest black flake8 schedule beautifulsoup4 selenium matplotlib plotly cryptography gspread google-auth google-auth-oauthlib google-auth-httplib2
```

### 2. 환경변수 설정

⚠️ **중요**: 민감한 정보는 절대 코드에 하드코딩하지 마세요!

#### 로컬 개발환경
1. `env-template.txt` 파일을 참고하여 `.env` 파일 생성
2. 실제 값으로 환경변수 설정:
   ```env
   DART_API_KEY=your_actual_dart_api_key
   SPREADSHEET_URL=your_actual_spreadsheet_url
   SERVICE_ACCOUNT_FILE=config/your_service_account.json
   ENVIRONMENT=development
   LOG_LEVEL=DEBUG
   SLACK_WEBHOOK=https://hooks.slack.com/services/YOUR/WEBHOOK/URL
   KIWOOM_APP_KEY=your_kiwoom_app_key
   KIWOOM_APP_SECRET=your_kiwoom_app_secret
   ```

#### 클라우드타입 배포환경
**📋 자세한 설정 방법은 `CLOUDTYPE_ENV_SETUP.md` 참조**

필수 환경변수:
- `DART_API_KEY`: DART API 인증키
- `GOOGLE_SERVICE_ACCOUNT_JSON`: Base64 인코딩된 구글 서비스 계정 JSON
- `SPREADSHEET_URL`: 구글 스프레드시트 URL
- `ENVIRONMENT`: production
- `PORT`: 8080

선택사항 환경변수:
- `SLACK_WEBHOOK`: 슬랙 웹훅 URL (신규 계약 알림용)
- `KIWOOM_APP_KEY`: 키움증권 OpenAPI 앱키 (주식 분석용)
- `KIWOOM_APP_SECRET`: 키움증권 OpenAPI 앱시크릿 (주식 분석용)

### 3. 실행

```bash
python run.py
```

## 📁 프로젝트 구조

```
trade/
├── src/                          # 소스 코드
│   ├── dart_api/                 # DART API 연동 모듈
│   │   ├── client.py             # API 클라이언트
│   │   └── analyzer.py           # 보고서 분석기
│   ├── google_sheets/            # 구글 시트 연동 모듈
│   │   └── client.py             # 스프레드시트 클라이언트
│   ├── utils/                    # 유틸리티 함수
│   │   ├── slack_notifier.py     # 슬랙 알림 모듈
│   │   ├── market_schedule.py    # 시장 스케줄 관리
│   │   └── stock_analyzer.py     # 주식 분석 모듈
│   └── main.py                   # 메인 실행 로직
├── config/                       # 설정 파일
│   └── settings.py               # 시스템 설정
├── logs/                         # 로그 파일
├── document/                     # 문서 파일
│   ├── rules.md                  # 개발 규칙
│   ├── 키움 REST API 문서.pdf
│   └── 키움 REST API 문서.xlsx
├── venv/                         # 가상환경
├── requirements.txt              # 패키지 의존성
├── .gitignore                    # Git 무시 파일
├── run.py                        # 로컬 실행 스크립트
├── cloudtype_run.py              # 클라우드타입 실행 스크립트
├── deploy.bat                    # Windows 배포 자동화 스크립트
├── git_helper.py                 # Git 명령어 헬퍼 도구
├── fix_git_config.py             # Git 설정 자동화 도구
├── CLOUDTYPE_ENV_SETUP.md        # 클라우드타입 배포 가이드
├── SLACK_SETUP_GUIDE.md          # 슬랙 웹훅 설정 가이드
├── KIWOOM_API_SETUP_GUIDE.md     # 키움증권 API 설정 가이드
├── env-template.txt              # 환경변수 템플릿 파일
└── README.md                     # 프로젝트 문서

```

## 🔧 설정 정보

### 구글 스프레드시트 구조

#### 1. 종목코드 시트
- **목적**: 분석 대상 회사 목록 관리
- **컬럼**: 분석대상, 종목코드, 조회코드, 종목명, 상장일, 시장구분, 업종코드, 업종명, 결산월, 지정자문인, 상장주식수, 액면가, 자본금, 대표이사, 대표전화, 주소

#### 2. 계약 시트  
- **목적**: 완전한 계약 데이터 저장
- **컬럼**: 종목코드, 조회코드, 종목명, 시장구분, 상장일자, 업종코드, 업종명, 결산월, 지정자문인, 상장주식수, 액면가, 자본금, 대표이사, 대표전화, 주소, 접수일자, 보고서명, 접수번호, 보고서링크, 계약(수주)일자, 계약상대방, 판매ㆍ공급계약 내용, 시작일, 종료일, 계약금액, 최근 매출액, 매출액 대비 비율

#### 3. 분석제외 시트
- **목적**: 불완전한 데이터 저장 (추후 수동 보완용)
- **컬럼**: 계약 시트와 동일

### 필수 데이터 필드
시스템은 다음 필드가 모두 추출되어야 '계약' 시트에 저장합니다:
- 계약(수주)일자
- 시작일  
- 종료일
- 계약금액

이 중 하나라도 누락되면 '분석제외' 시트에 저장됩니다.

## 🚀 주요 기능

### 1. 🕐 시장 스케줄 기반 실행
- **한국 주식시장 개장일/시간 자동 감지**
- **주말, 공휴일, 휴장일 자동 스킵**
- **개장시간(08:30~15:30)에만 스크래핑 실행**
- 2024-2025년 공휴일 데이터베이스 내장

### 2. 📊 지능형 주식 분석 시스템
- **실시간 주식 데이터 분석** (키움증권 OpenAPI 연동)
- **시장지수 vs 200일 이동평균** 비교 분석
- **시가총액 범위 체크** (500억~5,000억 적정 구간)
- **매출 대비 계약금액 비율** 분석 (20% 기준)
- **거래량 급증 감지** (20일 평균 대비 2배 이상)
- **양봉/음봉 캔들 패턴** 분석
- **종합 투자 점수** 산출 (0-10점)

### 3. 📢 스마트 슬랙 알림 시스템
- **신규 계약 발견 시에만 실시간 알림** (스팸 방지)
- **주식 분석 결과 포함** 상세 메시지
- 계약금액 읽기 쉬운 형태 포맷팅 (억원, 만원 단위)
- **투자 매력도별 색상 구분** (빨강: 매우유망, 주황: 유망, 초록: 보통, 회색: 주의)
- **휴장일 알림 없음** (불필요한 스팸 제거)
- **중요한 오류만 알림** (데이터 저장 실패, 시스템 전체 오류)

### 4. 🔍 DART API 연동
- 한국 공시시스템(DART)에서 "단일판매ㆍ공급계약체결" 공시 자동 검색
- 실시간 공시 데이터 수집 및 분석

### 5. 📊 구글 스프레드시트 연동
- 종목 리스트 자동 로드 ("분석대상" TRUE인 항목만)
- 신규 계약 정보 자동 저장
- 중복 데이터 자동 제거

### 6. 🧠 지능형 데이터 분석
- HTML/XML 보고서 자동 파싱
- 계약 정보 추출 (계약일자, 금액, 기간 등)
- 완전성 검증 후 분류 저장

## 📊 작업 흐름

1. **📊 시장 상태 확인**: 한국 주식시장 개장 여부 체크
2. **⏸️ 휴장일 처리**: 시장 휴장 시 **조용히 스킵** (알림 없음)
3. **✅ 개장일 스크래핑**:
   - 구글 스프레드시트 연결 및 기존 데이터 로드
   - '종목코드' 시트에서 분석대상이 TRUE인 회사들 조회
   - 각 회사별로 DART API를 통해 단일판매공급계약 공시 검색
   - 이미 처리된 공시는 건너뛰기 (중복 확인)
   - 새로운 공시의 원본 파일(ZIP) 다운로드
   - HTML/XML 파싱을 통한 계약 정보 추출
   - 완전성 검증 후 적절한 시트에 저장
4. **📢 스마트 알림**: **신규 계약 발견 시에만** 슬랙 알림 전송
5. **📝 로그 기록**: 전체 과정의 상세한 로그 생성 (알림과 별개)

## 🛠️ 개발 가이드

### 코드 스타일
- **Black**: 코드 포매팅 자동화
- **Flake8**: 코드 품질 검사
- **타입 힌트**: 가능한 모든 함수에 타입 힌트 적용

### 로깅
- **Loguru**: 구조화된 로깅 시스템
- **로그 레벨**: DEBUG, INFO, WARNING, ERROR
- **로그 파일**: `logs/dart_scraper.log`

### 에러 처리
- **Graceful Degradation**: 개별 회사/공시 처리 실패 시에도 전체 시스템 계속 실행
- **재시도 로직**: 네트워크 오류 등에 대한 자동 재시도
- **상세한 에러 로깅**: 문제 진단을 위한 충분한 정보 기록

## 📈 성능 최적화

- **API 호출 제한**: DART API 정책에 따른 요청 간격 준수
- **메모리 효율성**: 대용량 파일 스트리밍 처리
- **중복 방지**: 효율적인 중복 확인 알고리즘

## 🔍 트러블슈팅

### 일반적인 문제들

1. **구글 시트 연결 실패**
   - 서비스 계정 JSON 파일 경로 확인
   - 스프레드시트 공유 권한 확인

2. **DART API 오류**
   - API 키 유효성 확인
   - 일일 호출 한도 확인

3. **보고서 분석 실패**
   - 보고서 형식 변경 가능성
   - 패턴 매칭 로직 업데이트 필요

4. **시간대 관련 문제**
   - 클라우드타입 서버 시간이 UTC로 표시되는 경우: 자동으로 한국 시간대(KST)로 변환됨
   - 시장 개장시간 오판: 시스템이 자동으로 한국 시간 기준으로 판단
   - `fix_git_config.py` 실행으로 로컬 Git 설정 최적화

5. **PowerShell 관련 문제**
   - Git 명령어 멈춤 현상: `git config --global core.pager ""`로 해결
   - 한글 파일명 문제: `git config --global core.quotepath false`로 해결
   - 멀티라인 커밋 메시지 문제: `git_helper.py` 사용 권장

## 📋 개발 이력

### v2.0.0 (2025-09-14) - 스마트 알림 시스템
- ✨ **스마트 슬랙 알림 시스템**: 신규 계약 발견 시에만 알림 (스팸 방지)
- 🕐 **시장 스케줄 기반 실행**: 한국 주식시장 개장일/시간 자동 감지
- 📊 **지능형 주식 분석**: 키움증권 OpenAPI 연동 실시간 분석
- 🌏 **한국 시간대 완벽 지원**: 클라우드타입 서버 시간대 자동 설정
- 🔧 **PowerShell 호환성**: Windows 환경 Git 설정 자동화
- 📈 **투자 점수 시스템**: 시장지수, 시가총액, 거래량 등 종합 분석
- 🎯 **정확한 휴장일 감지**: 2024-2025년 공휴일 데이터베이스 내장

### v1.0.0 (2025-09-14) - 기본 시스템
- 초기 개발환경 구축
- DART API 연동 구현
- 구글 스프레드시트 연동 구현
- 보고서 분석 엔진 구현
- 메인 실행 로직 구현
- 로깅 시스템 구축

## 🤝 기여 방법

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## 📞 지원

문제가 발생하거나 개선 사항이 있으면 이슈를 등록해 주세요.

## 📄 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다.

---

**🔗 관련 링크**
- [DART 오픈API 가이드](https://opendart.fss.or.kr/guide/detail.do?apiGrpCd=DS001&apiId=2019001)
- [구글 스프레드시트 API 문서](https://developers.google.com/sheets/api)
- [키움 REST API 문서](document/키움%20REST%20API%20문서.pdf)
