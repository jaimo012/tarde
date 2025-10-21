# 키움증권 REST API 사용 현황

이 문서는 본 프로젝트에서 사용하는 키움증권 REST API의 상세 매핑 정보를 제공합니다.
키움증권에서 API 변경 공지가 올 때, 영향받는 함수를 신속하게 파악하기 위한 참조 문서입니다.

## 📚 공식 가이드 문서

- **키움증권 REST API 공식 가이드**: [i.kiwoom.com/api_board](https://i.kiwoom.com/api_board)
- **API 공지사항**: 키움증권 홈페이지 > API 관리 > 공지사항
- **API 키 발급 및 관리**: 키움증권 홈페이지 > API 관리 > 앱 키 관리

## 🔑 인증 (Authentication)

### 1. OAuth 2.0 토큰 발급

- **함수**: `authenticate()`
- **파일 위치**: `src/trading/kiwoom_client.py` (208-283줄)
- **키움증권 TR 코드**: **au10001**
- **API 엔드포인트**: `POST /oauth2/token`
- **요청 방식**: `client_credentials` grant type
- **요청 파라미터**:
  - `grant_type`: "client_credentials"
  - `appkey`: 앱 키
  - `secretkey`: 앱 시크릿
- **응답 필드**:
  - `token`: 액세스 토큰
  - `expires_dt`: 토큰 만료 일시 (YYYYMMDDHHmmss 형식)
  - `return_code`: 응답 코드 (0: 성공)
  - `return_msg`: 응답 메시지
- **토큰 유효기간**: 24시간 (안전을 위해 23시간으로 설정)
- **사용 시점**: 모든 API 호출 전에 토큰이 필요하며, 만료 시 자동 재발급

**주의사항**:
- IP 화이트리스트 등록 필수
- `secretkey` 파라미터명 주의 (appsecret 아님)
- return_code가 0이 아닌 경우 오류

---

## 💰 계좌 조회 (Account Information)

### 2. 예수금 및 잔고 조회

- **함수**: `get_balance()`
- **파일 위치**: `src/trading/kiwoom_client.py` (295-348줄)
- **키움증권 TR 코드**: **ka01690**
- **API 엔드포인트**: `POST /api/dostk/acnt`
- **API 헤더**: `api-id: ka01690`
- **요청 파라미터**:
  - `qry_dt`: 조회일자 (YYYYMMDD 형식, 예: "20251021")
- **응답 필드**:
  - `dbst_bal`: 예수금 (D+2 예수금)
  - `tot_buy_amt`: 총 매입가
  - `tot_evlt_amt`: 총 평가금액
  - `day_stk_asst`: 추정자산 (일별 주식자산)
- **반환값**:
  ```python
  {
      'deposit': Decimal,          # 예수금
      'total_buy_amount': Decimal, # 총 매입가
      'total_eval_amount': Decimal,# 총 평가금액
      'estimated_asset': Decimal,  # 추정자산
      'available_amount': Decimal  # 매수가능금액 (예수금과 동일)
  }
  ```

**사용 시점**:
- 거래 전 예수금 확인
- 투자 가능 금액 체크

---

### 3. 보유 종목 조회 (포지션)

- **함수**: `get_positions()`
- **파일 위치**: `src/trading/kiwoom_client.py` (350-419줄)
- **키움증권 TR 코드**: **ka01690**
- **API 엔드포인트**: `POST /api/dostk/acnt`
- **API 헤더**: `api-id: ka01690`
- **요청 파라미터**:
  - `qry_dt`: 조회일자 (YYYYMMDD 형식)
- **응답 필드** (`day_bal_rt` 배열):
  - `stk_cd`: 종목코드
  - `stk_nm`: 종목명
  - `rmnd_qty`: 잔고수량
  - `buy_uv`: 매입단가
  - `cur_prc`: 현재가
  - `evlt_amt`: 평가금액
  - `evltv_prft`: 평가손익
  - `prft_rt`: 수익률 (%)
- **반환값**:
  ```python
  [
      {
          'stock_code': str,
          'stock_name': str,
          'quantity': int,
          'avg_price': Decimal,       # 매입단가
          'current_price': Decimal,
          'eval_amount': Decimal,     # 평가금액
          'profit_loss': Decimal,     # 평가손익
          'profit_rate': Decimal      # 수익률 (%)
      },
      ...
  ]
  ```

**주의사항**:
- `get_balance()`와 동일한 TR 코드(ka01690)를 사용하지만 `day_bal_rt` 배열을 파싱
- 보유수량(`rmnd_qty`)이 0보다 큰 종목만 반환

**사용 시점**:
- 현재 보유 종목 확인
- 익절/손절 조건 체크

---

### 4. 현재가 조회

- **함수**: `get_current_price()`
- **파일 위치**: `src/trading/kiwoom_client.py` (421-465줄)
- **키움증권 TR 코드**: **없음 (pykrx 라이브러리 사용)**
- **사용 라이브러리**: `pykrx.stock.get_market_ohlcv_by_date()`
- **이유**: 키움증권 REST API에는 개별 종목 현재가 조회 API가 없음
- **반환값**:
  ```python
  {
      'current_price': Decimal
  }
  ```

**주의사항**:
- 키움증권 API 변경 시 영향 없음 (외부 라이브러리 사용)
- 장마감 후 당일 종가를 현재가로 사용

---

## 📊 주문 관리 (Order Management)

### 5. 주식 주문 실행

- **함수**: `place_order()`
- **파일 위치**: `src/trading/kiwoom_client.py` (467-577줄)
- **키움증권 TR 코드**: 
  - **kt10000** (매수 주문)
  - **kt10001** (매도 주문)
- **API 엔드포인트**: `POST /api/dostk/ordr`
- **API 헤더**: `api-id: kt10000` (매수) 또는 `kt10001` (매도)
- **요청 파라미터**:
  - `dmst_stex_tp`: 거래소구분 ("KRX", "NXT", "SOR")
  - `stk_cd`: 종목코드 (6자리)
  - `ord_qty`: 주문수량 (문자열)
  - `ord_uv`: 주문단가 (지정가인 경우, 시장가는 빈 문자열)
  - `trde_tp`: 매매구분
    - "3": 시장가
    - "0": 보통 (지정가)
  - `cond_uv`: 조건단가 (빈 문자열)
- **응답 필드**:
  - `ord_no`: 주문번호
  - `dmst_stex_tp`: 거래소구분
  - `return_code`: 응답 코드 (0: 성공)
  - `return_msg`: 응답 메시지
- **반환값**:
  ```python
  {
      'order_number': str,  # 주문번호
      'exchange': str,      # 거래소구분
      'order_time': str     # 주문시각 (HHmmss)
  }
  ```

**주의사항**:
- **실제 자금이 사용되므로 각별한 주의 필요**
- 매수/매도에 따라 다른 TR 코드 사용
- 시장가 주문 시 `ord_uv`는 빈 문자열
- 지정가 주문 시 `ord_uv`는 정수형 문자열

**사용 시점**:
- 투자 조건 만족 시 매수 주문
- 익절/손절 조건 도달 시 매도 주문

---

### 6. 체결 내역 조회

- **함수**: `get_order_status()`
- **파일 위치**: `src/trading/kiwoom_client.py` (579-660줄)
- **키움증권 TR 코드**: **ka10076**
- **API 엔드포인트**: `POST /api/dostk/acnt`
- **API 헤더**: `api-id: ka10076`
- **요청 파라미터**:
  - `stk_cd`: 종목코드 (빈 문자열이면 전체)
  - `qry_tp`: 조회구분
    - "0": 전체
    - "1": 종목별
  - `sell_tp`: 매매구분
    - "0": 전체
    - "1": 매도
    - "2": 매수
  - `ord_no`: 주문번호 (빈 문자열이면 전체)
  - `stex_tp`: 거래소구분
    - "0": 통합
    - "1": KRX
    - "2": NXT
- **응답 필드** (`cntr` 배열):
  - `ord_no`: 주문번호
  - `stk_cd`: 종목코드
  - `stk_nm`: 종목명
  - `io_tp_nm`: 주문구분 ("-매도", "+매수")
  - `ord_pric`: 주문가격
  - `ord_qty`: 주문수량
  - `cntr_pric`: 체결가격
  - `cntr_qty`: 체결수량
  - `oso_qty`: 미체결수량
  - `ord_stt`: 주문상태 ("체결")
  - `ord_tm`: 주문시간
  - `trde_tp`: 거래유형 ("보통", "시장가")
- **반환값**:
  ```python
  [
      {
          'order_number': str,
          'stock_code': str,
          'stock_name': str,
          'order_type': str,           # "-매도", "+매수"
          'order_price': Decimal,
          'order_quantity': int,
          'executed_price': Decimal,
          'executed_quantity': int,
          'unexecuted_quantity': int,
          'order_status': str,
          'order_time': str,
          'trade_type': str
      },
      ...
  ]
  ```

**사용 시점**:
- 주문 체결 확인
- 거래 이력 조회

---

### 7. 미체결 내역 조회

- **함수**: `get_pending_orders()`
- **파일 위치**: `src/trading/kiwoom_client.py` (662-740줄)
- **키움증권 TR 코드**: **ka10075**
- **API 엔드포인트**: `POST /api/dostk/acnt`
- **API 헤더**: `api-id: ka10075`
- **요청 파라미터**:
  - `all_stk_tp`: 조회구분
    - "0": 전체
    - "1": 종목별
  - `trde_tp`: 매매구분
    - "0": 전체
    - "1": 매도
    - "2": 매수
  - `stk_cd`: 종목코드 (빈 문자열이면 전체)
  - `stex_tp`: 거래소구분
    - "0": 통합
    - "1": KRX
    - "2": NXT
- **응답 필드** (`oso` 배열):
  - `ord_no`: 주문번호
  - `stk_cd`: 종목코드
  - `stk_nm`: 종목명
  - `io_tp_nm`: 주문구분 ("-매도", "+매수")
  - `ord_pric`: 주문가격
  - `ord_qty`: 주문수량
  - `oso_qty`: 미체결수량
  - `cntr_qty`: 체결수량
  - `ord_stt`: 주문상태 ("접수")
  - `tm`: 시간
  - `trde_tp`: 거래유형
  - `cur_prc`: 현재가
- **반환값**:
  ```python
  [
      {
          'order_number': str,
          'stock_code': str,
          'stock_name': str,
          'order_type': str,
          'order_price': Decimal,
          'order_quantity': int,
          'unexecuted_quantity': int,
          'executed_quantity': int,
          'order_status': str,         # "접수"
          'order_time': str,
          'trade_type': str,
          'current_price': Decimal
      },
      ...
  ]
  ```

**사용 시점**:
- 미체결 주문 확인
- 중복 주문 방지

---

### 8. 미체결 주문 존재 여부 확인

- **함수**: `has_pending_orders()`
- **파일 위치**: `src/trading/kiwoom_client.py` (742-770줄)
- **키움증권 TR 코드**: **ka10075** (내부적으로 `get_pending_orders()` 사용)
- **반환값**: `bool` (미체결 주문이 있으면 True, 없으면 False)

**사용 시점**:
- 동일 종목 중복 주문 방지
- 주문 전 미체결 여부 확인

---

## 🔄 API 호출 제한 (Rate Limiting)

### API 호출 제한 관리

- **클래스**: `APIRateLimiter`
- **파일 위치**: `src/trading/kiwoom_client.py` (18-64줄)
- **키움증권 API 아님**: 자체 구현한 호출 제한 관리자
- **제한 사항**:
  - 초당 최대 호출 횟수: 5회 (기본값)
  - 일일 최대 호출 횟수: 10,000회 (기본값)
- **동작 방식**:
  - 모든 API 호출 전 자동으로 제한 체크
  - 초당 제한 초과 시 자동 대기
  - 일일 제한 초과 시 예외 발생

---

## 📋 TR 코드 요약표

| TR 코드 | 함수명 | 용도 | API 엔드포인트 | 비고 |
|---------|--------|------|----------------|------|
| **au10001** | `authenticate()` | OAuth 2.0 인증 | `/oauth2/token` | 토큰 발급 |
| **ka01690** | `get_balance()` | 예수금 조회 | `/api/dostk/acnt` | 일별잔고수익률 |
| **ka01690** | `get_positions()` | 보유종목 조회 | `/api/dostk/acnt` | day_bal_rt 배열 사용 |
| **pykrx** | `get_current_price()` | 현재가 조회 | (외부 라이브러리) | 키움 API 없음 |
| **kt10000** | `place_order()` | 매수 주문 | `/api/dostk/ordr` | 실제 거래 발생 |
| **kt10001** | `place_order()` | 매도 주문 | `/api/dostk/ordr` | 실제 거래 발생 |
| **ka10076** | `get_order_status()` | 체결내역 조회 | `/api/dostk/acnt` | 당일 체결 |
| **ka10075** | `get_pending_orders()` | 미체결내역 조회 | `/api/dostk/acnt` | 당일 미체결 |
| **ka10075** | `has_pending_orders()` | 미체결 확인 | `/api/dostk/acnt` | 위 함수 내부 사용 |

---

## 🚨 API 변경 시 대응 가이드

### 1. 키움증권에서 API 변경 공지가 올 때

1. **TR 코드 확인**: 공지에서 변경된 TR 코드를 확인합니다.
2. **위 요약표 참조**: 해당 TR 코드를 사용하는 함수를 찾습니다.
3. **함수 코드 확인**: 파일 위치로 이동하여 코드를 검토합니다.
4. **변경 사항 적용**: 
   - 요청 파라미터 변경
   - 응답 필드 변경
   - 헤더 형식 변경
   등을 코드에 반영합니다.

### 2. 변경 빈도가 높은 항목

- **헤더 형식**: `api-id`, `cont-yn`, `next-key` 등의 헤더 필드명이나 형식
- **응답 필드명**: 응답 JSON의 필드명이 변경되는 경우 (예: `dbst_bal` → 다른 이름)
- **요청 파라미터**: Body 파라미터의 이름이나 형식 변경

### 3. 테스트 방법

```bash
# test 폴더에 테스트 스크립트 생성
# 예: test/test_kiwoom_balance.py

python test/test_kiwoom_balance.py
```

### 4. 주요 확인 사항

- ✅ `return_code`가 0인지 확인 (키움증권 API는 HTTP 200이어도 return_code로 성공 여부 판단)
- ✅ IP 화이트리스트 등록 여부
- ✅ 토큰 만료 시간 체크
- ✅ API 호출 제한 준수

---

## 📞 문의 및 지원

- **키움증권 API 고객센터**: 1544-9000
- **API 개발자 포럼**: 키움증권 홈페이지 > 고객광장 > API 게시판
- **긴급 장애**: 키움증권 API 관리 페이지에서 공지사항 확인

---

## 📝 문서 이력

- **2025-10-21**: 최초 작성
  - 8개 함수에 대한 TR 코드 매핑 완료
  - API 변경 시 대응 가이드 추가
  - TR 코드 요약표 작성

---

## ⚠️ 중요 보안 주의사항

1. **API 키 관리**:
   - 환경변수로 관리 (`.env` 파일 또는 클라우드타입 환경변수)
   - 절대 Git에 커밋하지 않기
   - 주기적으로 키 교체

2. **IP 화이트리스트**:
   - 서버 IP가 변경되면 키움증권 관리 페이지에서 재등록 필요
   - 테스트 시에도 IP 등록 필요

3. **실제 거래 주의**:
   - `place_order()` 함수는 실제 자금이 사용됨
   - 테스트 시 모의투자 모드(`TRADING_MODE=DRY_RUN`) 사용 권장
   - 주문 전 충분한 검증 필요

---

*이 문서는 키움증권 REST API 공식 문서를 기반으로 작성되었습니다.*
*API 변경 시 본 문서도 함께 업데이트해주세요.*

