"""
키움증권 REST API 클라이언트

이 모듈은 키움증권 OpenAPI를 통해 실제 주식 거래를 수행합니다.
실제 자금이 사용되므로 각별한 주의가 필요합니다.
"""

import os
import time
import requests
from typing import Dict, Optional, Any
from decimal import Decimal
from datetime import datetime, timedelta
from loguru import logger
import hashlib


class APIRateLimiter:
    """API 호출 제한을 관리하는 클래스"""
    
    def __init__(self, max_calls_per_second: int = 5, max_calls_per_day: int = 10000):
        """
        API 호출 제한 관리자를 초기화합니다.
        
        Args:
            max_calls_per_second: 초당 최대 호출 횟수 (기본 5회)
            max_calls_per_day: 일일 최대 호출 횟수 (기본 10,000회)
        """
        self.max_calls_per_second = max_calls_per_second
        self.max_calls_per_day = max_calls_per_day
        self.call_timestamps = []
        self.daily_call_count = 0
        self.last_reset_date = datetime.now().date()
    
    def wait_if_needed(self):
        """필요한 경우 API 호출 전 대기합니다."""
        now = datetime.now()
        
        # 일일 호출 횟수 초기화 (날짜가 바뀐 경우)
        if now.date() != self.last_reset_date:
            self.daily_call_count = 0
            self.last_reset_date = now.date()
            logger.info(f"API 호출 카운터 초기화: {now.date()}")
        
        # 일일 호출 한도 체크
        if self.daily_call_count >= self.max_calls_per_day:
            error_msg = f"🚨 키움증권 API 일일 호출 한도 초과! 현재: {self.daily_call_count}/{self.max_calls_per_day}회"
            logger.error(error_msg)
            raise Exception(error_msg)
        
        # 최근 1초 이내의 호출만 유지
        one_second_ago = now - timedelta(seconds=1)
        self.call_timestamps = [ts for ts in self.call_timestamps if ts > one_second_ago]
        
        # 초당 호출 제한 체크
        if len(self.call_timestamps) >= self.max_calls_per_second:
            wait_time = 1.0 - (now - self.call_timestamps[0]).total_seconds()
            if wait_time > 0:
                logger.debug(f"API 호출 제한으로 {wait_time:.2f}초 대기 중...")
                time.sleep(wait_time)
        
        # 현재 호출 기록
        self.call_timestamps.append(datetime.now())
        self.daily_call_count += 1


class KiwoomAPIClient:
    """키움증권 REST API 클라이언트"""
    
    # 키움증권 REST API 공식 URL
    BASE_URL_LIVE = "https://api.kiwoom.com"  # 실전투자
    BASE_URL_MOCK = "https://mockapi.kiwoom.com"  # 모의투자 (KRX만 지원)
    
    def __init__(self, app_key: str, app_secret: str, account_number: str):
        """
        키움증권 API 클라이언트를 초기화합니다.
        
        Args:
            app_key: 키움증권 앱 키
            app_secret: 키움증권 앱 시크릿
            account_number: 계좌번호
        """
        # 입력 검증
        if not app_key or not app_secret or not account_number:
            raise ValueError("키움증권 API 인증 정보가 필요합니다 (APP_KEY, APP_SECRET, ACCOUNT_NUMBER)")
        
        self.app_key = app_key
        self.app_secret = app_secret
        self.account_number = account_number  # 키움증권 API는 토큰으로 계좌 식별 (분리 불필요)
        
        # 거래 모드에 따른 BASE_URL 설정
        from config.settings import TRADING_MODE
        if TRADING_MODE == 'LIVE':
            self.base_url = self.BASE_URL_LIVE
            logger.info("✅ 키움증권 실전투자 모드로 초기화")
        else:
            self.base_url = self.BASE_URL_MOCK
            logger.info("✅ 키움증권 모의투자 모드로 초기화")
        
        # 민감정보 마스킹을 위한 해시
        self.app_key_masked = self._mask_sensitive_data(app_key)
        self.account_masked = self._mask_sensitive_data(account_number)
        
        # 토큰 관리
        self.access_token: Optional[str] = None
        self.token_expires_at: Optional[datetime] = None
        
        # API 호출 제한 관리
        self.rate_limiter = APIRateLimiter()
        
        # 세션 설정
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json; charset=utf-8',
            'User-Agent': 'DART-Trading-System/1.0'
        })
        
        logger.info(f"키움증권 API 클라이언트 초기화 완료 (계좌: {self.account_masked}, URL: {self.base_url})")
    
    def _mask_sensitive_data(self, data: str) -> str:
        """민감 데이터를 마스킹합니다."""
        if len(data) <= 4:
            return "****"
        return data[:2] + "*" * (len(data) - 4) + data[-2:]
    
    def _get_headers(self, api_id: str, cont_yn: str = 'N', next_key: str = '') -> Dict[str, str]:
        """
        키움증권 API 요청 헤더를 생성합니다.
        
        Args:
            api_id: TR명 (예: au10001, ka01690, kt10000)
            cont_yn: 연속조회여부 (N/Y)
            next_key: 연속조회키
        """
        if not self.access_token:
            raise Exception("액세스 토큰이 없습니다. authenticate()를 먼저 호출하세요.")
        
        headers = {
            'Content-Type': 'application/json;charset=UTF-8',
            'authorization': f'Bearer {self.access_token}',
            'api-id': api_id,  # TR명 (필수)
        }
        
        # 연속조회 헤더 추가
        if cont_yn:
            headers['cont-yn'] = cont_yn
        if next_key:
            headers['next-key'] = next_key
            
        return headers
    
    def _request_with_retry(self, method: str, url: str, **kwargs) -> requests.Response:
        """
        지수 백오프로 재시도하는 API 요청을 수행합니다.
        
        Args:
            method: HTTP 메서드 (GET, POST)
            url: 요청 URL
            **kwargs: requests 라이브러리에 전달할 추가 인자
            
        Returns:
            requests.Response: API 응답
        """
        max_retries = 3
        backoff_delays = [0.5, 1.0, 2.0]
        
        for attempt in range(max_retries):
            try:
                # API 호출 제한 체크 및 대기
                self.rate_limiter.wait_if_needed()
                
                # 타임아웃 설정
                if 'timeout' not in kwargs:
                    kwargs['timeout'] = 30
                
                # 요청 실행
                response = self.session.request(method, url, **kwargs)
                
                # 응답 로깅 (민감정보 제외)
                logger.debug(f"API 요청: {method} {url} - 상태: {response.status_code}")
                
                # 성공 또는 비가역 오류인 경우 즉시 반환
                if response.status_code < 500:
                    return response
                
                # 서버 오류인 경우 재시도
                logger.warning(f"서버 오류 발생 (시도 {attempt + 1}/{max_retries}): {response.status_code}")
                
                if attempt < max_retries - 1:
                    time.sleep(backoff_delays[attempt])
                    
            except requests.exceptions.Timeout:
                logger.warning(f"API 요청 타임아웃 (시도 {attempt + 1}/{max_retries})")
                if attempt < max_retries - 1:
                    time.sleep(backoff_delays[attempt])
                else:
                    raise
                    
            except requests.exceptions.RequestException as e:
                logger.error(f"API 요청 중 오류 발생: {e}")
                if attempt < max_retries - 1:
                    time.sleep(backoff_delays[attempt])
                else:
                    raise
        
        raise Exception(f"API 요청 실패: 최대 재시도 횟수 초과 ({max_retries}회)")
    
    def authenticate(self) -> bool:
        """
        OAuth 2.0 인증을 수행하고 액세스 토큰을 획득합니다.
        키움증권 REST API 공식 문서: TR au10001
        
        Returns:
            bool: 인증 성공 여부
        """
        try:
            logger.info("🔐 키움증권 API 인증 시작... (TR: au10001)")
            
            url = f"{self.base_url}/oauth2/token"
            
            # 키움증권 API 인증 요청 (공식 문서 규격)
            data = {
                'grant_type': 'client_credentials',
                'appkey': self.app_key,
                'secretkey': self.app_secret  # ⚠️ 'appsecret'이 아니라 'secretkey'!
            }
            
            # 인증은 토큰 없이 직접 호출
            headers = {
                'Content-Type': 'application/json;charset=UTF-8'
            }
            
            response = requests.post(url, headers=headers, json=data, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                
                # 키움증권 API 응답 검증 (return_code 체크)
                if result.get('return_code') != 0:
                    error_msg = f"🚨 키움증권 API 인증 실패!\n"
                    error_msg += f"return_code: {result.get('return_code')}\n"
                    error_msg += f"return_msg: {result.get('return_msg')}\n"
                    logger.error(error_msg)
                    return False
                
                # 토큰 추출 (키움증권은 'token' 필드 사용)
                self.access_token = result.get('token')
                
                # 만료 시간 파싱 (키움증권은 'expires_dt' 문자열 사용)
                # 형식: "20241107083713" (YYYYMMDDHHmmss)
                expires_dt_str = result.get('expires_dt', '')
                if expires_dt_str:
                    try:
                        self.token_expires_at = datetime.strptime(expires_dt_str, '%Y%m%d%H%M%S')
                        # 안전을 위해 1시간 전에 갱신하도록 설정
                        self.token_expires_at = self.token_expires_at - timedelta(hours=1)
                    except ValueError:
                        logger.warning(f"만료 시간 파싱 실패: {expires_dt_str}, 기본값(23시간) 사용")
                        self.token_expires_at = datetime.now() + timedelta(hours=23)
                else:
                    # 만료 시간 없으면 기본 23시간
                    self.token_expires_at = datetime.now() + timedelta(hours=23)
                
                logger.info(f"✅ 키움증권 API 인증 성공! (만료: {self.token_expires_at.strftime('%Y-%m-%d %H:%M:%S')})")
                return True
            else:
                error_msg = f"🚨 키움증권 API 인증 실패!\n"
                error_msg += f"HTTP 상태코드: {response.status_code}\n"
                error_msg += f"응답: {response.text}\n"
                error_msg += f"\n확인사항:\n"
                error_msg += f"1. KIWOOM_APP_KEY가 올바른지 확인\n"
                error_msg += f"2. KIWOOM_APP_SECRET이 올바른지 확인\n"
                error_msg += f"3. 키움증권 REST API 서비스 승인 상태 확인\n"
                error_msg += f"4. 서버 IP가 키움증권 화이트리스트에 등록되었는지 확인\n"
                error_msg += f"5. URL: {url}"
                logger.error(error_msg)
                return False
                
        except Exception as e:
            logger.error(f"🚨 키움증권 API 인증 중 예외 발생: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False
    
    def _ensure_authenticated(self):
        """토큰이 유효한지 확인하고 필요시 재인증합니다."""
        if not self.access_token or not self.token_expires_at:
            if not self.authenticate():
                raise Exception("키움증권 API 인증 실패")
        elif datetime.now() >= self.token_expires_at:
            logger.info("액세스 토큰이 만료되어 재인증합니다...")
            if not self.authenticate():
                raise Exception("키움증권 API 재인증 실패")
    
    def get_balance(self) -> Optional[Dict[str, Any]]:
        """
        일별잔고수익률 조회 (예수금 포함)
        키움증권 REST API: TR ka01690
        
        Returns:
            Optional[Dict]: 잔고 정보 (실패 시 None)
                - deposit: 예수금 (Decimal)
                - total_buy_amount: 총 매입가 (Decimal)
                - total_eval_amount: 총 평가금액 (Decimal)
                - estimated_asset: 추정자산 (Decimal)
        """
        try:
            self._ensure_authenticated()
            
            # 키움증권 일별잔고수익률 API (TR: ka01690)
            url = f"{self.base_url}/api/dostk/acnt"
            headers = self._get_headers(api_id='ka01690')
            
            # Body: 조회일자 (오늘)
            data = {
                'qry_dt': datetime.now().strftime('%Y%m%d')  # 예: "20250825"
            }
            
            response = self._request_with_retry('POST', url, headers=headers, json=data)
            
            if response.status_code == 200:
                result = response.json()
                
                # 키움증권 API 응답 검증 (return_code 체크)
                if result.get('return_code') != 0:
                    logger.error(f"잔고 조회 실패: {result.get('return_msg', 'Unknown error')}")
                    return None
                
                # 응답 파싱
                balance_info = {
                    'deposit': Decimal(str(result.get('dbst_bal', '0'))),  # 예수금
                    'total_buy_amount': Decimal(str(result.get('tot_buy_amt', '0'))),  # 총 매입가
                    'total_eval_amount': Decimal(str(result.get('tot_evlt_amt', '0'))),  # 총 평가금액
                    'estimated_asset': Decimal(str(result.get('day_stk_asst', '0'))),  # 추정자산
                    'available_amount': Decimal(str(result.get('dbst_bal', '0'))),  # 매수가능금액 (예수금과 동일)
                }
                
                logger.info(f"✅ 잔고 조회 성공 - 예수금: {balance_info['deposit']:,}원, 추정자산: {balance_info['estimated_asset']:,}원")
                return balance_info
            else:
                logger.error(f"잔고 조회 API HTTP 오류: {response.status_code}, {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"잔고 조회 중 오류 발생: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None
    
    def get_positions(self) -> Optional[list]:
        """
        보유 주식 잔고를 조회합니다.
        키움증권 REST API: TR ka01690 (day_bal_rt 배열 사용)
        
        Returns:
            Optional[list]: 보유 종목 리스트 (실패 시 None)
                각 종목은 다음 정보를 포함:
                - stock_code: 종목코드
                - stock_name: 종목명
                - quantity: 보유수량
                - avg_price: 매입단가 (Decimal)
                - current_price: 현재가 (Decimal)
                - eval_amount: 평가금액 (Decimal)
                - profit_loss: 평가손익 (Decimal)
                - profit_rate: 수익률 (Decimal, %)
        """
        try:
            self._ensure_authenticated()
            
            # 키움증권 일별잔고수익률 API (TR: ka01690)
            url = f"{self.base_url}/api/dostk/acnt"
            headers = self._get_headers(api_id='ka01690')
            
            # Body: 조회일자 (오늘)
            data = {
                'qry_dt': datetime.now().strftime('%Y%m%d')
            }
            
            response = self._request_with_retry('POST', url, headers=headers, json=data)
            
            if response.status_code == 200:
                result = response.json()
                
                # 키움증권 API 응답 검증
                if result.get('return_code') != 0:
                    logger.error(f"포지션 조회 실패: {result.get('return_msg', 'Unknown error')}")
                    return None
                
                # day_bal_rt 배열 파싱
                day_bal_rt = result.get('day_bal_rt', [])
                positions = []
                
                for item in day_bal_rt:
                    # 보유수량이 0이 아닌 종목만 추가
                    quantity = int(item.get('rmnd_qty', '0'))
                    if quantity > 0:
                        position = {
                            'stock_code': item.get('stk_cd', ''),
                            'stock_name': item.get('stk_nm', ''),
                            'quantity': quantity,
                            'avg_price': Decimal(str(item.get('buy_uv', '0'))),  # 매입단가
                            'current_price': Decimal(str(item.get('cur_prc', '0'))),
                            'eval_amount': Decimal(str(item.get('evlt_amt', '0'))),
                            'profit_loss': Decimal(str(item.get('evltv_prft', '0'))),
                            'profit_rate': Decimal(str(item.get('prft_rt', '0')))
                        }
                        positions.append(position)
                
                logger.info(f"✅ 포지션 조회 성공 - 보유 종목: {len(positions)}개")
                return positions
            else:
                logger.error(f"포지션 조회 API HTTP 오류: {response.status_code}, {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"포지션 조회 중 오류 발생: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None
    
    def get_current_price(self, stock_code: str) -> Optional[Dict[str, Any]]:
        """
        종목의 현재가 정보를 조회합니다.
        
        Args:
            stock_code: 종목코드 (6자리)
            
        Returns:
            Optional[Dict]: 현재가 정보 (실패 시 None)
                - current_price: 현재가 (Decimal)
                - open_price: 시가 (Decimal)
                - high_price: 고가 (Decimal)
                - low_price: 저가 (Decimal)
                - volume: 거래량
        """
        try:
            # 종목코드 검증
            if not stock_code or len(stock_code) != 6 or not stock_code.isdigit():
                logger.error(f"잘못된 종목코드 형식: {stock_code}")
                return None
            
            self._ensure_authenticated()
            
            url = f"{self.base_url}/uapi/domestic-stock/v1/quotations/inquire-price"
            headers = self._get_headers('FHKST01010100')
            
            params = {
                'FID_COND_MRKT_DIV_CODE': 'J',  # 시장분류 (J: 주식)
                'FID_INPUT_ISCD': stock_code
            }
            
            response = self._request_with_retry('GET', url, headers=headers, params=params)
            
            if response.status_code == 200:
                result = response.json()
                
                if result.get('rt_cd') == '0':
                    output = result.get('output', {})
                    
                    price_info = {
                        'current_price': Decimal(str(output.get('stck_prpr', '0'))),
                        'open_price': Decimal(str(output.get('stck_oprc', '0'))),
                        'high_price': Decimal(str(output.get('stck_hgpr', '0'))),
                        'low_price': Decimal(str(output.get('stck_lwpr', '0'))),
                        'volume': int(output.get('acml_vol', '0'))
                    }
                    
                    logger.debug(f"현재가 조회 성공 - {stock_code}: {price_info['current_price']:,}원")
                    return price_info
                else:
                    logger.error(f"현재가 조회 실패: {result.get('msg1', 'Unknown error')}")
                    return None
            else:
                logger.error(f"현재가 조회 API 오류: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"현재가 조회 중 오류 발생: {e}")
            return None
    
    def place_order(self, stock_code: str, order_type: str, quantity: int, 
                    price: Optional[Decimal] = None) -> Optional[Dict[str, Any]]:
        """
        주식 주문을 실행합니다.
        키움증권 REST API: TR kt10000 (매수), kt10001 (매도)
        
        Args:
            stock_code: 종목코드 (6자리)
            order_type: 주문유형 ('buy_market', 'buy_limit', 'sell_market', 'sell_limit')
            quantity: 주문수량
            price: 주문가격 (지정가인 경우 필수, Decimal)
            
        Returns:
            Optional[Dict]: 주문 결과 (실패 시 None)
                - order_number: 주문번호 (ord_no)
                - exchange: 거래소구분 (dmst_stex_tp)
        """
        try:
            # 입력 검증
            if not stock_code or len(stock_code) != 6 or not stock_code.isdigit():
                logger.error(f"❌ 잘못된 종목코드 형식: {stock_code}")
                return None
            
            if quantity <= 0:
                logger.error(f"❌ 잘못된 주문수량: {quantity}")
                return None
            
            if order_type not in ['buy_market', 'buy_limit', 'sell_market', 'sell_limit']:
                logger.error(f"❌ 잘못된 주문유형: {order_type}")
                return None
            
            if order_type in ['buy_limit', 'sell_limit'] and not price:
                logger.error("❌ 지정가 주문에는 가격이 필요합니다")
                return None
            
            self._ensure_authenticated()
            
            # 키움증권 API 주문 파라미터 설정
            if order_type in ['buy_market', 'buy_limit']:
                api_id = 'kt10000'  # 매수주문
                side = '매수'
            else:
                api_id = 'kt10001'  # 매도주문
                side = '매도'
            
            # 매매구분 (trde_tp)
            if order_type in ['buy_market', 'sell_market']:
                trde_tp = '3'  # 시장가
                ord_uv = ''  # 시장가는 주문단가 빈 문자열
            else:
                trde_tp = '0'  # 보통 (지정가)
                ord_uv = str(int(price)) if price else ''
            
            url = f"{self.base_url}/api/dostk/ordr"
            headers = self._get_headers(api_id=api_id)
            
            # 키움증권 주문 Body (공식 문서 규격)
            data = {
                'dmst_stex_tp': 'KRX',  # 국내거래소구분 (KRX, NXT, SOR)
                'stk_cd': stock_code,  # 종목코드
                'ord_qty': str(quantity),  # 주문수량 (문자열)
                'ord_uv': ord_uv,  # 주문단가 (시장가는 빈 문자열)
                'trde_tp': trde_tp,  # 매매구분 (3: 시장가, 0: 보통)
                'cond_uv': ''  # 조건단가 (빈 문자열)
            }
            
            logger.warning(f"🚨 실제 주문 실행 (키움증권 API TR: {api_id})")
            logger.warning(f"  종목: {stock_code}")
            logger.warning(f"  {side}: {quantity}주")
            logger.warning(f"  가격: {price if price else '시장가'}원")
            logger.warning(f"  Body: {data}")
            
            response = self._request_with_retry('POST', url, headers=headers, json=data)
            
            if response.status_code == 200:
                result = response.json()
                
                # 키움증권 API 응답 검증
                if result.get('return_code') != 0:
                    error_msg = f"🚨 주문 실패!\n"
                    error_msg += f"종목: {stock_code}\n"
                    error_msg += f"{side} {order_type}\n"
                    error_msg += f"수량: {quantity}주\n"
                    error_msg += f"가격: {price if price else '시장가'}원\n"
                    error_msg += f"return_code: {result.get('return_code')}\n"
                    error_msg += f"return_msg: {result.get('return_msg')}"
                    logger.error(error_msg)
                    return None
                
                # 주문 성공
                order_result = {
                    'order_number': result.get('ord_no', ''),
                    'exchange': result.get('dmst_stex_tp', 'KRX'),
                }
                
                logger.info(f"✅ 주문 성공!")
                logger.info(f"  주문번호: {order_result['order_number']}")
                logger.info(f"  거래소: {order_result['exchange']}")
                logger.info(f"  메시지: {result.get('return_msg', '')}")
                return order_result
            else:
                logger.error(f"🚨 주문 API HTTP 오류: {response.status_code}, {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"🚨 주문 실행 중 예외 발생: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None
    
    def get_order_status(self, order_number: Optional[str] = None) -> Optional[list]:
        """
        당일 주문/체결 내역을 조회합니다.
        키움증권 REST API: TR kt10076 (체결요청) 또는 kt10075 (미체결요청)
        
        ⚠️ 현재 미구현 상태입니다. 필요 시 kt10075/kt10076 TR을 사용하여 구현해야 합니다.
        
        Args:
            order_number: 특정 주문번호 (None인 경우 전체 조회)
            
        Returns:
            Optional[list]: 주문/체결 내역 리스트 (현재는 항상 빈 리스트 반환)
        """
        logger.warning("⚠️ get_order_status()는 현재 미구현 상태입니다. 체결 확인이 필요하면 TR kt10075/kt10076을 구현하세요.")
        return []

