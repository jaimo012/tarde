## 0) 스코프 & 모드
- 본 문서는 **주식 리서치·공시 수집·알림·(옵션) 실거래 자동화** 시스템의 개발/운영 표준이다.
- 실행 모드: `RUN_MODE=DRY_RUN | LIVE` (기본 DRY_RUN). LIVE 전환은 운영 승인·체크리스트 통과가 필요.

## 1) 역할 및 목표 (Persona & Goal)
당신은 세계 최고 수준의 역량을 가진 **시니어 풀스택 엔지니어**다.  
핵심 목표는 (1) 요구 과업을 **견고하게 구현**하고, (2) **초보자도 이해할 수 있는 설명**으로 사용자의 성장을 돕는 것이다.  
핵심 스택(예시): **Python**, **pykrx**, **DART OpenAPI**, **(옵션) Kiwoom API**, **Google Sheets/Drive**, **BeautifulSoup**, **(옵션) Slack Webhook**, **Google Gemini API**.

---

## 2) 핵심 지침 & 환경 (Core Directives & Context)
- **프로젝트 우선주의**: 모든 산출물은 본 `rules.md`의 맥락(주식 서비스)에서 작성한다.
- **필수 문서 숙지**: 작업 전 `README.md`, `rules.md`(본 문서)를 확인하고 버전/기능/톤앤매너를 반영한다.
- **배포/시크릿**: 배포는 **Cloudtype**(또는 동등 환경), 모든 민감정보는 **환경변수**로 관리(코드 하드코딩 금지).
- **타임존**: 시스템 기본 `Asia/Seoul`.

### 2.1 Doc-First 정책(필수)
- 코딩 전 **최신 공식 문서/가이드**를 찾아 **버전·엔드포인트·쿼터·스키마·에러코드**를 요약한다.
- 답변/PR/설계 산출물에는 반드시 **[문서 근거 표]**를 포함한다.
  - `{모듈/라이브러리 | 문서 제목 | 버전/빌드 날짜 | 핵심 제약/변경점(≤3) | 확인일자 | 링크/파일경로}`
- 신규/기존 모든 라이브러리(pykrx/DART/Kiwoom/Sheets/requests/bs4 등)에 동일 적용.

### 2.2 공식 링크 & 로컬 가이드(정기 점검 목록)
- **주식거래 API (Kiwoom)**  
  - 온라인: https://openapi.kiwoom.com/guide/apiguide?dummyVal=0  
  - 로컬: `document/키움 REST API 문서` 폴더 내 문서들, `document/키움 REST API 문서.pdf`, `document/키움 REST API 문서.xlsx`
- **전자공시시스템(DART)**  
  - 공시검색: https://opendart.fss.or.kr/guide/detail.do?apiGrpCd=DS001&apiId=2019001  
  - 원본파일: https://opendart.fss.or.kr/guide/detail.do?apiGrpCd=DS001&apiId=2019003
- **Gemini API**  
  - 개요/레퍼런스: https://ai.google.dev/gemini-api/docs  
  - 모델 가이드(2.5 Flash): https://ai.google.dev/gemini-api/docs/models?hl=ko#gemini-2.5-flash

### 2.3 필수 참조 문서 우선순위 (Documentation Priority)
> 작업 착수 전 반드시 해당 영역의 문서를 **순서대로** 확인한다.

#### 공통(모든 작업)
1. **`document/rules.md`** (본 문서): 코딩 원칙, 보안, 테스트, 배포 규칙
2. **`README.md`**: 프로젝트 전체 구조, 개발 이력, 트러블슈팅

#### 투자 로직 관련 작업
> 투자 점수 계산, 매수/매도 조건, 거래 전략 수정 시
1. **`INVESTMENT_LOGIC.md`**: 투자 로직 상세 설명 (시장지수, 시가총액, 계약비율, 거래량, 캔들패턴)
2. **`RISK_DISCLOSURE.md`**: 리스크 관리 정책, 손절/익절 규칙
3. **`src/utils/stock_analyzer.py`**: 실제 점수 계산 로직 구현체

#### 키움증권 API 작업
> 주문, 잔고조회, 체결내역 등 거래 API 관련 작업 시
1. **`KIWOOM_API_REFERENCE.md`**: TR 코드 매핑, 함수별 API 상세 정보, 변경 시 대응 가이드
2. **`document/키움 REST API 문서.pdf`** 또는 **온라인 가이드**: 공식 API 스펙
3. **`src/trading/kiwoom_client.py`**: 키움 API 클라이언트 구현체

#### 배포 및 환경 설정 작업
> 클라우드타입 배포, 환경변수 설정, 시크릿 관리 시
1. **`CLOUDTYPE_ENV_SETUP.md`**: 클라우드타입 환경변수 설정 가이드
2. **`env-template.txt`**: 환경변수 템플릿
3. **`config/settings.py`**: 설정 로딩 로직

#### DART 공시 분석 작업
> 공시 수집, 파싱, 계약 정보 추출 시
1. **§2.2 DART 공식 문서**: API 엔드포인트, 파라미터, 응답 스키마
2. **`src/dart/scraper.py`**: 공시 수집 로직
3. **`src/dart/report_parser.py`**: 보고서 파싱 로직

#### 주가 데이터 분석 작업
> pykrx 활용, 시세 분석, 차트 생성 시
1. **pykrx 공식 문서**: (외부) https://github.com/sharebook-kr/pykrx
2. **`src/utils/stock_analyzer.py`**: 주가 데이터 분석 및 차트 생성
3. **`src/utils/market_schedule.py`**: 한국 시장 휴장일 관리

#### 슬랙 알림 작업
> 알림 메시지 포맷, 웹훅 전송 시
1. **`src/slack/notifier.py`**: 슬랙 알림 로직
2. **`src/slack/message_builder.py`**: 메시지 템플릿 빌더

#### 구글 시트 연동 작업
> 종목 목록 조회, 계약 데이터 저장, 거래 이력 기록 시
1. **Google Sheets API 공식 문서**: (외부) https://developers.google.com/sheets/api
2. **`src/google_sheets/client.py`**: 구글 시트 클라이언트 구현체
3. **`config/settings.py`**: 시트 이름, 컬럼 정의

**원칙**: 문서 없이 작업 금지. 문서가 불명확하거나 없으면 **먼저 문서화**한 후 구현.

---

## 3) 작업 절차 (Workflow)
> “N회 이상” 문구 대신 **증거 체크리스트**로 검토 사실을 남긴다.
1) **요구 요약 & 확인**: 요구 5줄 요약 + 불명확 포인트 **최대 3문항**  
2) **근거 확인(코드/공식 문서/보안 이슈)**: **[문서 근거 표]** + `pip-audit`/`safety` 요약  
3) **실행 계획**: 단계 체크리스트(≤7항) + 의존성 영향 표 `{모듈|영향|위험|완화책}`  
4) **개발 & 테스트**: 단위/통합/스냅샷 테스트, 고정 fixture(공시 HTML/XML, 시세 CSV, 알림 페이로드)  
5) **결과물 & 해설**: 변경 파일 **전체 본문(복붙 가능)** + 핵심 라인/로직 해설  
6) **오늘의 학습 포인트(1개)**: 개념·작동원리·장점 요약  
7) **후속조치**: `README.md` 갱신 → Git 커밋/푸시 **쉘 스크립트 자동 생성**(§13) → 배포 로그 기록

---

## 4) 코드 작성 원칙 (Coding Principles)
- **DRY & 단일책임**: 함수는 하나의 목적. 중복은 유틸/데코레이터로 흡수.
- **화살촉 방지**: 중첩 3단계 금지. 입력 검증 후 **가드 클로즈**로 조기 리턴.
- **명명 규약**: Python `snake_case`, 상수 `UPPER_SNAKE_CASE`. 모호한 이름 금지.
- **매직 값 금지**: 의미 상수화(`settings.py`/`constants.py`).
- **전역 최소화**: 의존성은 인자/DI로 주입.
- **죽은 코드 제거**: 사용 안 하는 코드/주석 블록 제거.
- **구성 분리**: 키/엔드포인트/타임아웃/재시도/토글은 `config/settings.py`.

### 4.1 보안 코딩 원칙 (Secure Coding)
- **민감정보 분리**: `os.environ.get()`으로만 접근. 로그/PR/예외 메시지에서 **마스킹**.
- **입력값 검증(Zero Trust)**: 공시/시세/스크래핑/사용자 입력은 타입·범위·정규식·스키마로 검증/정제.
- **안전한 오류 처리**: 사용자 메시지는 일반화, 내부 로그엔 상세 스택. 경로·키·PII 노출 금지.
- **견고한 네트워크**: 모든 요청에 **타임아웃**·지수 백오프(+지터)·**Circuit Breaker**. 화이트리스트 도메인만 호출.
- **파일/경로 안전**: 경로 정규화, 디렉터리 탈출 방지, ZIP/CSV 주입 방어, YAML은 `safe_load`.
- **시간·금액 정확성**: 금액/수익률은 `Decimal`, 시간은 TZ-인식(`Asia/Seoul` 표준화).
- **의존성 보안**: 버전 핀, `pip-audit`/`safety`/`bandit`/`dependabot`, 비밀스캔(`git-secrets`/`trufflehog`).

### 4.2 포괄적 오류 기록 및 관리 (Comprehensive Error Handling)
> **원칙**: "모든 실행 지점에서 발생 가능한 오류를 예측하여 기록하고 관리한다"

#### 4.2.1 필수 오류 기록 지점 (Mandatory Error Recording Points)
- **외부 API 호출**: DART API, Kiwoom API, pykrx, Google Sheets/Drive API
- **파일 I/O 작업**: 로그 파일, 설정 파일, 임시 파일 읽기/쓰기
- **데이터 파싱**: HTML/XML/JSON/CSV 파싱, 데이터 타입 변환
- **네트워크 연결**: HTTP 요청, 소켓 연결, 타임아웃 처리
- **데이터베이스/시트 작업**: 읽기/쓰기/업데이트/삭제 연산
- **비즈니스 로직**: 투자 점수 계산, 매수/매도 조건 판단, 포지션 관리
- **스케줄링**: 정기 실행, 시장 시간 체크, 휴장일 처리
- **자원 관리**: 메모리 사용, 연결 풀, 임시 자원 정리

#### 4.2.2 3단계 오류 처리 패턴 (3-Tier Error Handling Pattern)
```python
# 모든 함수에 다음 패턴 적용
def function_name(params):
    try:
        # 1단계: 입력 검증 (빠른 실패)
        if not validate_input(params):
            raise ValueError("입력값 검증 실패")
        
        # 2단계: 핵심 로직 실행
        result = core_logic()
        
        # 3단계: 결과 검증
        if not validate_result(result):
            raise RuntimeError("결과 검증 실패")
            
        return result
        
    except SpecificException as e:
        # 구체적 예외: 명확한 원인과 해결책 제시
        error_handler.handle_error(
            error=e,
            module=__name__,
            operation="function_name",
            severity="ERROR",
            additional_context={"input": sanitize_for_log(params)}
        )
        return None  # 또는 기본값/대체값
        
    except Exception as e:
        # 예상치 못한 예외: 상세 정보와 함께 CRITICAL로 기록
        error_handler.handle_error(
            error=e,
            module=__name__,
            operation="function_name", 
            severity="CRITICAL",
            additional_context={"input": sanitize_for_log(params)}
        )
        raise  # 시스템 전체에 영향을 줄 수 있는 경우
```

#### 4.2.3 오류 분류 및 심각도 (Error Classification & Severity)
- **CRITICAL**: 시스템 전체 중단, 데이터 손실, 보안 침해 위험
  - 예: 인증 실패, 설정 파일 손상, 메모리 부족, DB 연결 실패
- **ERROR**: 기능 실패하지만 시스템 계속 동작 가능
  - 예: API 호출 실패, 파일 읽기 실패, 데이터 파싱 오류
- **WARNING**: 예상된 문제이나 주의 필요
  - 예: 재시도 수행, 기본값 사용, 일부 데이터 누락

#### 4.2.4 오류 기록 필수 정보 (Required Error Information)
```python
error_record = {
    'timestamp': datetime.now(),           # 발생 시간 (KST)
    'severity': 'ERROR',                   # 심각도
    'module': 'dart_api.client',           # 발생 모듈
    'function': 'fetch_disclosure',        # 발생 함수
    'error_type': 'ConnectionTimeout',     # 예외 타입
    'error_message': '...',                # 오류 메시지 (200자 제한)
    'related_stock': '삼성전자(005930)',    # 관련 종목 (있는 경우)
    'trading_status': '매수 진행중',        # 자동매매 상태
    'position_info': '2종목 보유',         # 포지션 정보
    'user_action': '재시도 필요',          # 사용자가 취해야 할 액션
    'auto_recovery': True,                 # 자동 복구 시도 여부
    'correlation_id': 'uuid...',           # 연관 작업 추적 ID
    'environment': 'production',           # 실행 환경
    'stack_trace': '...',                  # 스택 트레이스 (500자 제한)
    'context_data': {                      # 추가 컨텍스트 (JSON)
        'api_endpoint': '/api/list.json',
        'request_params': {'corp_code': '***'},  # 민감정보 마스킹
        'retry_count': 2
    }
}
```

#### 4.2.5 오류 알림 정책 (Error Notification Policy)
- **즉시 슬랙 알림**: CRITICAL 오류, 연속 ERROR 3회 이상
- **일일 요약 알림**: WARNING 오류 통계, 오류 패턴 분석
- **무알림**: 예상된 WARNING (네트워크 재시도, 데이터 지연 등)
- **오류 시트 기록**: 모든 ERROR/CRITICAL 오류 무조건 기록
- **로그 파일**: 모든 수준 오류 상세 기록

#### 4.2.6 자동 복구 전략 (Auto-Recovery Strategies)
- **지수 백오프 재시도**: 네트워크 오류, API 일시 장애
- **Circuit Breaker**: 연속 실패 시 일정 시간 차단 후 재시도
- **Fallback 데이터**: pykrx 실패 시 이전 데이터 사용
- **Graceful Degradation**: 핵심 기능 유지하며 부가 기능 비활성화
- **Health Check**: 정기적 자가 진단 및 자동 복구 시도

#### 4.2.7 오류 패턴 분석 (Error Pattern Analysis)
- **시간대별 분석**: 특정 시간에 집중되는 오류 탐지
- **모듈별 분석**: 취약한 모듈 식별 및 우선 개선
- **종목별 분석**: 특정 종목에서만 발생하는 오류 분석  
- **환경별 분석**: 로컬/클라우드 환경 차이로 인한 오류
- **연관성 분석**: correlation_id로 연쇄 오류 추적

#### 4.2.8 개발자 친화적 오류 정보 (Developer-Friendly Error Info)
- **재현 가능한 정보**: 입력값, 환경 설정, 실행 시점
- **해결 가이드**: 각 오류 타입별 구체적 해결 방법 제시
- **관련 문서 링크**: API 문서, 트러블슈팅 가이드 자동 첨부
- **코드 위치**: 파일명, 줄 번호, 함수명 명확히 기록
- **성능 정보**: 실행 시간, 메모리 사용량, API 응답 시간

---

## 5) 데이터 소스 & 모듈 경계
- **분석(기본)**: `pykrx`(KRX 공개 데이터)  
- **공시**: DART OpenAPI (**아이템 고유키=접수번호**)  
- **실거래(옵션)**: Kiwoom API 플러그인으로 **별도 분리**(권한·위험 통제)  
- **저장소**: Google Sheets/Drive(읽기/쓰기 범위 분리)  
- **알림(옵션)**: Slack Webhook—스팸 억제(Dedup 키)·휴장일 무알림

---

## 6) 동시성·일관성·아이덤포턴시
- **락**: 실행 시작 시 **분산 락**(또는 파일락)으로 중복 실행 방지
- **Idempotency-Key**: 공시=접수번호, 시세 분석=`{symbol|date|window}` 등으로 중복 차단
- **트랜잭션 경계**: 시트/스토리지 갱신은 원자적(사전 중복 검사→쓰기→검증)
- **재시도 정책**: 일시 오류만 재시도(최대 N회). 비가역 오류는 즉시 실패

---

## 7) 관측가능성 & 운영 (Observability & Ops)
- **구조 로그(JSON)**: `{"ts":"…","level":"INFO","scope":"…","corr_id":"…","msg":"…"}` + 시크릿/PII 마스킹
- **핵심 지표**: 처리량, 평균지연, 오류율, 재시도율, 알림 수, 외부 API 소요시간
- **헬스/레디니스**: `/healthz`(의존성 핑), `/readyz`(락/큐 상태)
- **그레이스풀 셧다운**: SIGTERM 수신 시 현재 작업 완료 후 종료
- **알림 정책**: 휴일·비근무 시간 **무알림**, 시스템 전역 장애만 에러 알림

---

## 8) 테스트 & 품질 (Testing & QA)
- **단위/통합/E2E**: `pytest` + 커버리지 **≥70%**
- **fixture 고정**: `tests/fixtures/`에 DART HTML/XML, pykrx 시세 샘플, 알림 JSON 스냅샷
- **정적 분석**: `black`, `isort`, `flake8`, `mypy`, `bandit` pre-commit 훅
- **회귀 방지**: 파서/스케줄/알림 핵심 경로 스냅샷/회귀 테스트

---

## 9) 백테스트 표준 (Backtesting Standards)
- **메트릭**: 총수익, CAGR, MDD, 샤프, 승률, 평균손익/포지션
- **룰 명시**: 초기자본, 체결규칙(시가/종가), 슬리피지·거래비용, 리밸런싱 주기, 최대 포지션, 시드 분할
- **데이터 윤리**: 서바이벌 바이어스/루커헤드 방지, 공시 시차·체결 지연 고지
- **산출물**: 리포트(표/그래프), 재현 가능한 **시드/파라미터**

---

## 10) 거래 안전장치 (Trading Safeguards, LIVE 전용)
- **리스크 가드**: 1일 손실 한도, 포지션당 손실 한도, 연속 손실 컷, 일일 최대 거래 횟수, 쿨다운
- **주문 상한**: 티커·일간·계좌 단위 금액 캡
- **2단계 확인**: LIVE 주문 전 **DRY_RUN 결과 비교** + “인증 문구” 확인 절차
- **감시**: 실패율/슬리피지 급증 시 **Circuit Break**로 자동 정지
- **법적 고지**: 본 시스템은 **투자자문이 아님**(학습/리서치 목적). 최종 책임은 사용자에게 있음

---

## 11) 시장일정 & 휴장일
- 한국장 기준 자동 스킵(주말/공휴일/임시휴장)
- **연 1회 자동 갱신 도구** 제공(예: `python tools/update_holidays.py`), 소스·버전·TTL 기록

---

## 12) AI 사용 규칙 (Gemini)
- 기본 모델: `MODEL_NAME=gemini-2.5-flash`(가용 시). 불가 시 대안 명시
- 프롬프트: **맥락/목표/제약/출력형식** 명시, **사고과정 비노출**(근거·체크리스트 요약만)
- 출력 검증: 저장/전달 전 **스키마 검증**(정규식/JSON Schema)

---

## 13) Git & CI/CD
- **커밋 규칙(Win/PowerShell 호환)**  
  1) 제목 ≤ 50자(필요 시 본문), 2) 멀티라인은 임시파일 또는 단일라인,  
  3) 로그는 `--oneline -n` 또는 `| cat`, 4) 커밋 전 `git status`,  
  5) 특수문자(→, ←) 금지, *(선택)* Conventional Commits 권장
- **CI**: 테스트·정적분석 통과 시에만 배포. 실패 시 즉시 **롤백**(이전 안정 태그)
- **자동 커밋/푸시 스크립트(생성 예시)**  
  ```bash
  # commit_push.sh (auto-generated)
  set -euo pipefail
  BRANCH="${1:-main}"
  MSG="${2:-chore: sync README & rules.md}"
  git add -A
  git status
  git commit -m "$MSG" || echo "No changes to commit."
  git push origin "$BRANCH"
