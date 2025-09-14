"""
주식 시장 데이터 분석 모듈

이 모듈은 키움증권 OpenAPI를 사용하여 주식 데이터를 수집하고
계약 정보와 함께 종목 분석을 수행합니다.
"""

import requests
import json
from typing import Dict, Optional, Tuple, List
from datetime import datetime, timedelta
from loguru import logger
import time
from dataclasses import dataclass


@dataclass
class StockAnalysisResult:
    """주식 분석 결과를 담는 데이터 클래스"""
    stock_code: str
    stock_name: str
    market_type: str  # KOSPI, KOSDAQ
    current_price: int
    market_cap: int  # 시가총액 (억원)
    
    # 분석 결과
    is_index_above_ma200: bool  # 시장지수가 200일 이동평균 위에 있는가
    is_market_cap_in_range: bool  # 시가총액이 500억~5000억 사이인가
    is_contract_ratio_over_20: bool  # 매출 대비 계약금액 비율이 20% 넘는가
    trading_conditions_met: int  # 거래 조건 만족 개수 (0-2)
    
    # 상세 데이터
    index_current: float  # 현재 시장지수
    index_ma200: float  # 시장지수 200일 이동평균
    contract_sales_ratio: float  # 매출 대비 계약금액 비율
    volume_ratio: float  # 거래대금 비율 (20일 평균 대비)
    is_positive_candle: bool  # 양봉 여부
    
    # 메시지용 요약
    analysis_summary: str
    recommendation_score: int  # 0-10점


class KiwoomStockDataClient:
    """키움증권 OpenAPI 클라이언트"""
    
    BASE_URL = "https://openapi.kiwoom.com:9443"
    
    def __init__(self, app_key: str = None, app_secret: str = None):
        """
        키움증권 API 클라이언트를 초기화합니다.
        
        Args:
            app_key (str): 키움증권 API 앱키
            app_secret (str): 키움증권 API 앱시크릿
        """
        self.app_key = app_key
        self.app_secret = app_secret
        self.access_token = None
        self.token_expires_at = None
        
        if app_key and app_secret:
            self._get_access_token()
        else:
            logger.warning("키움증권 API 키가 설정되지 않아 Mock 데이터를 사용합니다.")
    
    def _get_access_token(self) -> bool:
        """액세스 토큰을 발급받습니다."""
        try:
            url = f"{self.BASE_URL}/oauth2/tokenP"
            headers = {"Content-Type": "application/json"}
            data = {
                "grant_type": "client_credentials",
                "appkey": self.app_key,
                "appsecret": self.app_secret
            }
            
            response = requests.post(url, headers=headers, data=json.dumps(data))
            
            if response.status_code == 200:
                result = response.json()
                self.access_token = result.get("access_token")
                expires_in = result.get("expires_in", 86400)  # 기본 24시간
                self.token_expires_at = datetime.now() + timedelta(seconds=expires_in - 300)  # 5분 여유
                
                logger.info("키움증권 API 액세스 토큰 발급 성공")
                return True
            else:
                logger.error(f"키움증권 API 토큰 발급 실패: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"키움증권 API 토큰 발급 중 오류: {e}")
            return False
    
    def _ensure_valid_token(self) -> bool:
        """유효한 토큰이 있는지 확인하고 필요시 갱신합니다."""
        if not self.access_token or not self.token_expires_at:
            return self._get_access_token()
        
        if datetime.now() >= self.token_expires_at:
            return self._get_access_token()
        
        return True
    
    def get_stock_price(self, stock_code: str) -> Optional[Dict]:
        """주식 현재가 정보를 조회합니다."""
        if not self._ensure_valid_token():
            return self._get_mock_stock_price(stock_code)
        
        try:
            # 키움증권 주식 현재가 조회 API
            url = f"{self.BASE_URL}/uapi/domestic-stock/v1/quotations/inquire-price"
            headers = {
                "Content-Type": "application/json",
                "authorization": f"Bearer {self.access_token}",
                "appkey": self.app_key,
                "appsecret": self.app_secret,
                "tr_id": "FHKST01010100"  # 키움증권 현재가 조회 TR
            }
            params = {
                "fid_cond_mrkt_div_code": "J",
                "fid_input_iscd": stock_code
            }
            
            response = requests.get(url, headers=headers, params=params)
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.warning(f"주식가격 조회 실패 ({stock_code}): {response.status_code}")
                return self._get_mock_stock_price(stock_code)
                
        except Exception as e:
            logger.error(f"주식가격 조회 중 오류 ({stock_code}): {e}")
            return self._get_mock_stock_price(stock_code)
    
    def get_market_index(self, market_type: str) -> Optional[Dict]:
        """시장 지수 정보를 조회합니다."""
        if not self._ensure_valid_token():
            return self._get_mock_market_index(market_type)
        
        try:
            # 키움증권 지수 코드: KOSPI: 0001, KOSDAQ: 1001
            index_code = "0001" if market_type == "KOSPI" else "1001"
            
            url = f"{self.BASE_URL}/uapi/domestic-stock/v1/quotations/inquire-index-price"
            headers = {
                "Content-Type": "application/json",
                "authorization": f"Bearer {self.access_token}",
                "appkey": self.app_key,
                "appsecret": self.app_secret,
                "tr_id": "FHKUP03500100"  # 키움증권 지수 조회 TR
            }
            params = {
                "fid_cond_mrkt_div_code": "U",
                "fid_input_iscd": index_code
            }
            
            response = requests.get(url, headers=headers, params=params)
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.warning(f"시장지수 조회 실패 ({market_type}): {response.status_code}")
                return self._get_mock_market_index(market_type)
                
        except Exception as e:
            logger.error(f"시장지수 조회 중 오류 ({market_type}): {e}")
            return self._get_mock_market_index(market_type)
    
    def _get_mock_stock_price(self, stock_code: str) -> Dict:
        """Mock 주식 가격 데이터를 반환합니다."""
        # 실제 서비스에서는 제거하고 실제 API 데이터만 사용
        mock_data = {
            "005930": {"price": 71000, "volume": 15000000, "market": "KOSPI"},  # 삼성전자
            "000660": {"price": 95000, "volume": 8000000, "market": "KOSPI"},   # SK하이닉스
            "035420": {"price": 48000, "volume": 12000000, "market": "KOSDAQ"}, # NAVER
        }
        
        base_data = mock_data.get(stock_code, {"price": 50000, "volume": 5000000, "market": "KOSPI"})
        
        return {
            "output": {
                "stck_prpr": str(base_data["price"]),  # 현재가
                "prdy_vrss": "1000",  # 전일대비
                "prdy_vrss_sign": "2",  # 등락구분 (2: 상승)
                "acml_vol": str(base_data["volume"]),  # 누적거래량
                "acml_tr_pbmn": str(base_data["volume"] * base_data["price"]),  # 누적거래대금
                "hts_kor_isnm": "Mock종목",  # 종목명
                "stck_mxpr": str(int(base_data["price"] * 1.3)),  # 상한가
                "stck_llam": str(int(base_data["price"] * 0.7)),  # 하한가
            }
        }
    
    def _get_mock_market_index(self, market_type: str) -> Dict:
        """Mock 시장 지수 데이터를 반환합니다."""
        if market_type == "KOSPI":
            return {
                "output": {
                    "bstp_nmix_prpr": "2650.50",  # 현재지수
                    "bstp_nmix_prdy_vrss": "15.20",  # 전일대비
                    "prdy_vrss_sign": "2",  # 등락구분
                }
            }
        else:  # KOSDAQ
            return {
                "output": {
                    "bstp_nmix_prpr": "850.30",
                    "bstp_nmix_prdy_vrss": "8.50",
                    "prdy_vrss_sign": "2",
                }
            }


class StockAnalyzer:
    """주식 분석 메인 클래스"""
    
    def __init__(self, kiwoom_app_key: str = None, kiwoom_app_secret: str = None):
        """
        주식 분석기를 초기화합니다.
        
        Args:
            kiwoom_app_key (str): 키움증권 API 앱키
            kiwoom_app_secret (str): 키움증권 API 앱시크릿
        """
        self.kiwoom_client = KiwoomStockDataClient(kiwoom_app_key, kiwoom_app_secret)
        
        # Mock 데이터 (실제 API 연동 전까지 사용)
        self.mock_ma200_data = {
            "KOSPI": {"current": 2650.50, "ma200": 2580.30},
            "KOSDAQ": {"current": 850.30, "ma200": 820.50}
        }
        
        logger.info("주식 분석기가 초기화되었습니다.")
    
    def analyze_stock_for_contract(self, contract_data: Dict) -> StockAnalysisResult:
        """
        계약 정보와 함께 종목을 분석합니다.
        
        Args:
            contract_data (Dict): 계약 정보
            
        Returns:
            StockAnalysisResult: 분석 결과
        """
        stock_code = contract_data.get('종목코드', '')
        stock_name = contract_data.get('종목명', '')
        market_type = contract_data.get('시장구분', 'KOSPI')
        listed_shares = self._parse_number(contract_data.get('상장주식수', '0'))
        contract_amount = self._parse_number(contract_data.get('계약금액', '0'))
        recent_sales = self._parse_number(contract_data.get('최근 매출액', '0'))
        
        logger.info(f"종목 분석 시작: {stock_name}({stock_code})")
        
        try:
            # 1. 주식 가격 정보 조회
            stock_data = self.kiwoom_client.get_stock_price(stock_code)
            if not stock_data:
                return self._create_error_result(stock_code, stock_name, "주식 데이터 조회 실패")
            
            current_price = int(stock_data['output']['stck_prpr'])
            
            # 2. 시장 지수 정보 조회
            index_data = self.kiwoom_client.get_market_index(market_type)
            if not index_data:
                return self._create_error_result(stock_code, stock_name, "시장 지수 조회 실패")
            
            # 3. 분석 수행
            analysis_result = self._perform_analysis(
                stock_code, stock_name, market_type, current_price, listed_shares,
                contract_amount, recent_sales, stock_data, index_data
            )
            
            logger.info(f"종목 분석 완료: {stock_name} (점수: {analysis_result.recommendation_score}/10)")
            return analysis_result
            
        except Exception as e:
            logger.error(f"종목 분석 중 오류 발생 ({stock_name}): {e}")
            return self._create_error_result(stock_code, stock_name, f"분석 오류: {str(e)}")
    
    def _perform_analysis(self, stock_code: str, stock_name: str, market_type: str, 
                         current_price: int, listed_shares: int, contract_amount: int,
                         recent_sales: int, stock_data: Dict, index_data: Dict) -> StockAnalysisResult:
        """실제 분석을 수행합니다."""
        
        # 시가총액 계산 (억원 단위)
        market_cap = (current_price * listed_shares) // 100000000
        
        # 1. 시장지수 200일 이동평균 비교 (Mock 데이터 사용)
        mock_data = self.mock_ma200_data.get(market_type, {"current": 2500, "ma200": 2400})
        index_current = mock_data["current"]
        index_ma200 = mock_data["ma200"]
        is_index_above_ma200 = index_current > index_ma200
        
        # 2. 시가총액 범위 체크 (500억 ~ 5,000억)
        is_market_cap_in_range = 500 <= market_cap <= 5000
        
        # 3. 매출 대비 계약금액 비율
        contract_sales_ratio = (contract_amount / recent_sales * 100) if recent_sales > 0 else 0
        is_contract_ratio_over_20 = contract_sales_ratio > 20
        
        # 4. 거래 조건 체크 (Mock 데이터 사용)
        volume_ratio = 2.3  # Mock: 20일 평균 대비 2.3배
        is_positive_candle = True  # Mock: 양봉
        
        trading_conditions_met = 0
        if volume_ratio >= 2.0:  # 20일 평균의 2배 이상
            trading_conditions_met += 1
        if is_positive_candle:  # 양봉
            trading_conditions_met += 1
        
        # 분석 요약 및 점수 계산
        analysis_summary, recommendation_score = self._create_analysis_summary(
            is_index_above_ma200, is_market_cap_in_range, is_contract_ratio_over_20, 
            trading_conditions_met, market_cap, contract_sales_ratio
        )
        
        return StockAnalysisResult(
            stock_code=stock_code,
            stock_name=stock_name,
            market_type=market_type,
            current_price=current_price,
            market_cap=market_cap,
            is_index_above_ma200=is_index_above_ma200,
            is_market_cap_in_range=is_market_cap_in_range,
            is_contract_ratio_over_20=is_contract_ratio_over_20,
            trading_conditions_met=trading_conditions_met,
            index_current=index_current,
            index_ma200=index_ma200,
            contract_sales_ratio=contract_sales_ratio,
            volume_ratio=volume_ratio,
            is_positive_candle=is_positive_candle,
            analysis_summary=analysis_summary,
            recommendation_score=recommendation_score
        )
    
    def _create_analysis_summary(self, is_index_above_ma200: bool, is_market_cap_in_range: bool,
                               is_contract_ratio_over_20: bool, trading_conditions_met: int,
                               market_cap: int, contract_sales_ratio: float) -> Tuple[str, int]:
        """분석 요약과 추천 점수를 생성합니다."""
        
        # 기본 점수 계산
        score = 0
        summary_parts = []
        
        # 시장지수 조건 (2점)
        if is_index_above_ma200:
            score += 2
            summary_parts.append("✅ 시장지수 > 200일 이평선")
        else:
            summary_parts.append("❌ 시장지수 < 200일 이평선")
        
        # 시가총액 조건 (2점)
        if is_market_cap_in_range:
            score += 2
            summary_parts.append(f"✅ 시가총액 적정 ({market_cap:,}억원)")
        else:
            summary_parts.append(f"❌ 시가총액 부적정 ({market_cap:,}억원)")
        
        # 매출 비율 조건 (3점)
        if is_contract_ratio_over_20:
            score += 3
            summary_parts.append(f"✅ 매출 대비 계약 비율 높음 ({contract_sales_ratio:.1f}%)")
        else:
            summary_parts.append(f"❌ 매출 대비 계약 비율 낮음 ({contract_sales_ratio:.1f}%)")
        
        # 거래 조건 (각 1.5점, 총 3점)
        score += trading_conditions_met * 1.5
        if trading_conditions_met == 2:
            summary_parts.append("✅ 거래 조건 모두 만족")
        elif trading_conditions_met == 1:
            summary_parts.append("⚠️ 거래 조건 일부 만족")
        else:
            summary_parts.append("❌ 거래 조건 미만족")
        
        # 등급 결정
        if score >= 8:
            grade = "🔥 매우 유망"
        elif score >= 6:
            grade = "⭐ 유망"
        elif score >= 4:
            grade = "⚠️ 보통"
        else:
            grade = "❌ 주의"
        
        summary = f"{grade} | " + " | ".join(summary_parts)
        
        return summary, int(score)
    
    def _create_error_result(self, stock_code: str, stock_name: str, error_msg: str) -> StockAnalysisResult:
        """오류 발생 시 기본 결과를 생성합니다."""
        return StockAnalysisResult(
            stock_code=stock_code,
            stock_name=stock_name,
            market_type="UNKNOWN",
            current_price=0,
            market_cap=0,
            is_index_above_ma200=False,
            is_market_cap_in_range=False,
            is_contract_ratio_over_20=False,
            trading_conditions_met=0,
            index_current=0,
            index_ma200=0,
            contract_sales_ratio=0,
            volume_ratio=0,
            is_positive_candle=False,
            analysis_summary=f"❌ 분석 실패: {error_msg}",
            recommendation_score=0
        )
    
    def _parse_number(self, value: str) -> int:
        """문자열을 숫자로 변환합니다."""
        if not value or value.strip() == '':
            return 0
        
        try:
            # 쉼표 제거 후 숫자만 추출
            import re
            numbers = re.findall(r'[\d,]+', str(value))
            if numbers:
                return int(numbers[0].replace(',', ''))
            return 0
        except:
            return 0
