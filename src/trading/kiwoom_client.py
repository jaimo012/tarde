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
    
    BASE_URL = "https://openapi.kiwoom.com:9443"
    
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
        self.account_number = account_number
        
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
        
        logger.info(f"키움증권 API 클라이언트 초기화 완료 (계좌: {self.account_masked})")
    
    def _mask_sensitive_data(self, data: str) -> str:
        """민감 데이터를 마스킹합니다."""
        if len(data) <= 4:
            return "****"
        return data[:2] + "*" * (len(data) - 4) + data[-2:]
    
    def _get_headers(self, tr_id: str) -> Dict[str, str]:
        """API 요청 헤더를 생성합니다."""
        if not self.access_token:
            raise Exception("액세스 토큰이 없습니다. authenticate()를 먼저 호출하세요.")
        
        return {
            'authorization': f'Bearer {self.access_token}',
            'appkey': self.app_key,
            'appsecret': self.app_secret,
            'tr_id': tr_id,
            'custtype': 'P',  # 개인
        }
    
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
        
        Returns:
            bool: 인증 성공 여부
        """
        try:
            logger.info("키움증권 API 인증 시작...")
            
            url = f"{self.BASE_URL}/oauth2/token"
            data = {
                'grant_type': 'client_credentials',
                'appkey': self.app_key,
                'appsecret': self.app_secret
            }
            
            response = self._request_with_retry('POST', url, json=data)
            
            if response.status_code == 200:
                result = response.json()
                self.access_token = result.get('access_token')
                
                # 토큰 만료 시간 설정 (기본 24시간, 안전을 위해 23시간으로 설정)
                expires_in = result.get('expires_in', 86400)
                self.token_expires_at = datetime.now() + timedelta(seconds=expires_in - 3600)
                
                logger.info(f"키움증권 API 인증 성공 (만료: {self.token_expires_at})")
                return True
            else:
                error_msg = f"🚨 키움증권 API 인증 실패!\n"
                error_msg += f"상태코드: {response.status_code}\n"
                error_msg += f"응답: {response.text}\n"
                error_msg += f"확인사항:\n"
                error_msg += f"1. KIWOOM_APP_KEY가 올바른지 확인\n"
                error_msg += f"2. KIWOOM_APP_SECRET이 올바른지 확인\n"
                error_msg += f"3. 키움증권 서비스 승인 상태 확인\n"
                error_msg += f"4. 서버 IP가 화이트리스트에 등록되었는지 확인"
                logger.error(error_msg)
                return False
                
        except Exception as e:
            logger.error(f"키움증권 API 인증 중 오류 발생: {e}")
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
        예수금 및 매수 가능 금액을 조회합니다.
        
        Returns:
            Optional[Dict]: 예수금 정보 (실패 시 None)
                - available_amount: 매수 가능 금액 (Decimal)
                - cash_balance: 예수금 (Decimal)
        """
        try:
            self._ensure_authenticated()
            
            url = f"{self.BASE_URL}/uapi/domestic-stock/v1/trading/inquire-psbl-order"
            headers = self._get_headers('TTTC8908R')
            
            params = {
                'CANO': self.account_number,
                'ACNT_PRDT_CD': '01',  # 상품코드 (01: 종합)
                'PDNO': '',  # 종목코드 (공백: 전체)
                'ORD_UNPR': '',  # 주문단가
                'ORD_DVSN': '01',  # 주문구분 (01: 시장가)
                'CMA_EVLU_AMT_ICLD_YN': 'Y',  # CMA 평가금액 포함여부
                'OVRS_ICLD_YN': 'N'  # 해외 포함여부
            }
            
            response = self._request_with_retry('GET', url, headers=headers, params=params)
            
            if response.status_code == 200:
                result = response.json()
                
                if result.get('rt_cd') == '0':  # 성공
                    output = result.get('output', {})
                    
                    balance_info = {
                        'available_amount': Decimal(str(output.get('ord_psbl_cash', '0'))),
                        'cash_balance': Decimal(str(output.get('dnca_tot_amt', '0'))),
                    }
                    
                    logger.info(f"예수금 조회 성공 - 매수가능: {balance_info['available_amount']:,}원")
                    return balance_info
                else:
                    logger.error(f"예수금 조회 실패: {result.get('msg1', 'Unknown error')}")
                    return None
            else:
                logger.error(f"예수금 조회 API 오류: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"예수금 조회 중 오류 발생: {e}")
            return None
    
    def get_positions(self) -> Optional[list]:
        """
        보유 주식 잔고를 조회합니다.
        
        Returns:
            Optional[list]: 보유 종목 리스트 (실패 시 None)
                각 종목은 다음 정보를 포함:
                - stock_code: 종목코드
                - stock_name: 종목명
                - quantity: 보유수량
                - avg_price: 평균단가 (Decimal)
                - current_price: 현재가 (Decimal)
                - eval_amount: 평가금액 (Decimal)
                - profit_loss: 평가손익 (Decimal)
                - profit_rate: 수익률 (Decimal, %)
        """
        try:
            self._ensure_authenticated()
            
            url = f"{self.BASE_URL}/uapi/domestic-stock/v1/trading/inquire-balance"
            headers = self._get_headers('TTTC8434R')
            
            params = {
                'CANO': self.account_number,
                'ACNT_PRDT_CD': '01',
                'AFHR_FLPR_YN': 'N',  # 시간외단일가여부
                'OFL_YN': '',  # 오프라인여부
                'INQR_DVSN': '02',  # 조회구분 (02: 종목별)
                'UNPR_DVSN': '01',  # 단가구분
                'FUND_STTL_ICLD_YN': 'N',  # 펀드결제분포함여부
                'FNCG_AMT_AUTO_RDPT_YN': 'N',  # 융자금액자동상환여부
                'PRCS_DVSN': '01',  # 처리구분
                'CTX_AREA_FK100': '',  # 연속조회검색조건
                'CTX_AREA_NK100': ''  # 연속조회키
            }
            
            response = self._request_with_retry('GET', url, headers=headers, params=params)
            
            if response.status_code == 200:
                result = response.json()
                
                if result.get('rt_cd') == '0':
                    output_list = result.get('output1', [])
                    positions = []
                    
                    for item in output_list:
                        # 보유수량이 0이 아닌 종목만 추가
                        quantity = int(item.get('hldg_qty', '0'))
                        if quantity > 0:
                            position = {
                                'stock_code': item.get('pdno', ''),
                                'stock_name': item.get('prdt_name', ''),
                                'quantity': quantity,
                                'avg_price': Decimal(str(item.get('pchs_avg_pric', '0'))),
                                'current_price': Decimal(str(item.get('prpr', '0'))),
                                'eval_amount': Decimal(str(item.get('evlu_amt', '0'))),
                                'profit_loss': Decimal(str(item.get('evlu_pfls_amt', '0'))),
                                'profit_rate': Decimal(str(item.get('evlu_pfls_rt', '0')))
                            }
                            positions.append(position)
                    
                    logger.info(f"잔고 조회 성공 - 보유 종목: {len(positions)}개")
                    return positions
                else:
                    logger.error(f"잔고 조회 실패: {result.get('msg1', 'Unknown error')}")
                    return None
            else:
                logger.error(f"잔고 조회 API 오류: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"잔고 조회 중 오류 발생: {e}")
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
            
            url = f"{self.BASE_URL}/uapi/domestic-stock/v1/quotations/inquire-price"
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
        
        Args:
            stock_code: 종목코드 (6자리)
            order_type: 주문유형 ('buy_market', 'buy_limit', 'sell_market', 'sell_limit')
            quantity: 주문수량
            price: 주문가격 (지정가인 경우 필수, Decimal)
            
        Returns:
            Optional[Dict]: 주문 결과 (실패 시 None)
                - order_number: 주문번호
                - order_time: 주문시각
        """
        try:
            # 입력 검증
            if not stock_code or len(stock_code) != 6 or not stock_code.isdigit():
                logger.error(f"잘못된 종목코드 형식: {stock_code}")
                return None
            
            if quantity <= 0:
                logger.error(f"잘못된 주문수량: {quantity}")
                return None
            
            if order_type not in ['buy_market', 'buy_limit', 'sell_market', 'sell_limit']:
                logger.error(f"잘못된 주문유형: {order_type}")
                return None
            
            if order_type in ['buy_limit', 'sell_limit'] and not price:
                logger.error("지정가 주문에는 가격이 필요합니다")
                return None
            
            self._ensure_authenticated()
            
            # 주문 구분 코드 결정
            if order_type == 'buy_market':
                tr_id = 'TTTC0802U'
                order_dvsn = '01'  # 시장가
                side = 'buy'
            elif order_type == 'buy_limit':
                tr_id = 'TTTC0802U'
                order_dvsn = '00'  # 지정가
                side = 'buy'
            elif order_type == 'sell_market':
                tr_id = 'TTTC0801U'
                order_dvsn = '01'  # 시장가
                side = 'sell'
            else:  # sell_limit
                tr_id = 'TTTC0801U'
                order_dvsn = '00'  # 지정가
                side = 'sell'
            
            url = f"{self.BASE_URL}/uapi/domestic-stock/v1/trading/order-cash"
            headers = self._get_headers(tr_id)
            
            data = {
                'CANO': self.account_number,
                'ACNT_PRDT_CD': '01',
                'PDNO': stock_code,
                'ORD_DVSN': order_dvsn,
                'ORD_QTY': str(quantity),
                'ORD_UNPR': str(int(price)) if price else '0',
            }
            
            logger.warning(f"🚨 실제 주문 실행: {side.upper()} {stock_code} {quantity}주 @ {price if price else '시장가'}원")
            
            response = self._request_with_retry('POST', url, headers=headers, json=data)
            
            if response.status_code == 200:
                result = response.json()
                
                if result.get('rt_cd') == '0':
                    output = result.get('output', {})
                    
                    order_result = {
                        'order_number': output.get('KRX_FWDG_ORD_ORGNO', ''),
                        'order_time': output.get('ORD_TMD', ''),
                    }
                    
                    logger.info(f"✅ 주문 성공 - 주문번호: {order_result['order_number']}")
                    return order_result
                else:
                    error_msg = f"🚨 주문 실패!\n"
                    error_msg += f"종목: {stock_code}\n"
                    error_msg += f"주문유형: {side} {order_type}\n"
                    error_msg += f"수량: {quantity}주\n"
                    error_msg += f"가격: {price if price else '시장가'}원\n"
                    error_msg += f"오류 메시지: {result.get('msg1', 'Unknown error')}\n"
                    error_msg += f"오류 코드: {result.get('rt_cd', 'N/A')}"
                    logger.error(error_msg)
                    return None
            else:
                logger.error(f"주문 API 오류: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"주문 실행 중 오류 발생: {e}")
            return None
    
    def get_order_status(self, order_number: Optional[str] = None) -> Optional[list]:
        """
        당일 주문/체결 내역을 조회합니다.
        
        Args:
            order_number: 특정 주문번호 (None인 경우 전체 조회)
            
        Returns:
            Optional[list]: 주문/체결 내역 리스트 (실패 시 None)
                각 주문은 다음 정보를 포함:
                - order_number: 주문번호
                - stock_code: 종목코드
                - stock_name: 종목명
                - order_type: 주문유형 (매수/매도)
                - order_quantity: 주문수량
                - order_price: 주문가격 (Decimal)
                - executed_quantity: 체결수량
                - executed_price: 체결가격 (Decimal)
                - order_status: 주문상태
        """
        try:
            self._ensure_authenticated()
            
            url = f"{self.BASE_URL}/uapi/domestic-stock/v1/trading/inquire-daily-ccld"
            headers = self._get_headers('TTTC8001R')
            
            params = {
                'CANO': self.account_number,
                'ACNT_PRDT_CD': '01',
                'INQR_STRT_DT': datetime.now().strftime('%Y%m%d'),
                'INQR_END_DT': datetime.now().strftime('%Y%m%d'),
                'SLL_BUY_DVSN_CD': '00',  # 전체
                'INQR_DVSN': '00',  # 역순
                'PDNO': '',  # 전체
                'CCLD_DVSN': '00',  # 전체
                'ORD_GNO_BRNO': '',
                'ODNO': order_number if order_number else '',
                'INQR_DVSN_3': '00',
                'INQR_DVSN_1': '',
                'CTX_AREA_FK100': '',
                'CTX_AREA_NK100': ''
            }
            
            response = self._request_with_retry('GET', url, headers=headers, params=params)
            
            if response.status_code == 200:
                result = response.json()
                
                if result.get('rt_cd') == '0':
                    output_list = result.get('output1', [])
                    orders = []
                    
                    for item in output_list:
                        order = {
                            'order_number': item.get('odno', ''),
                            'stock_code': item.get('pdno', ''),
                            'stock_name': item.get('prdt_name', ''),
                            'order_type': '매수' if item.get('sll_buy_dvsn_cd') == '02' else '매도',
                            'order_quantity': int(item.get('ord_qty', '0')),
                            'order_price': Decimal(str(item.get('ord_unpr', '0'))),
                            'executed_quantity': int(item.get('tot_ccld_qty', '0')),
                            'executed_price': Decimal(str(item.get('avg_prvs', '0'))),
                            'order_status': item.get('ord_dvsn_name', '')
                        }
                        orders.append(order)
                    
                    logger.debug(f"주문내역 조회 성공 - {len(orders)}건")
                    return orders
                else:
                    logger.error(f"주문내역 조회 실패: {result.get('msg1', 'Unknown error')}")
                    return None
            else:
                logger.error(f"주문내역 조회 API 오류: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"주문내역 조회 중 오류 발생: {e}")
            return None

