"""
주식 시장 데이터 분석 모듈

이 모듈은 pykrx 라이브러리를 사용하여 주식 데이터를 수집하고
계약 정보와 함께 종목 분석을 수행합니다.
"""

from typing import Dict, Optional, Tuple
from datetime import datetime, timedelta
from loguru import logger
from dataclasses import dataclass

try:
    from pykrx import stock
    PYKRX_AVAILABLE = True
except ImportError:
    PYKRX_AVAILABLE = False
    logger.warning("pykrx 라이브러리가 설치되지 않았습니다. pip install pykrx로 설치하세요.")


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


class PykrxStockDataClient:
    """pykrx를 사용한 주식 데이터 클라이언트"""
    
    def __init__(self):
        """pykrx 클라이언트를 초기화합니다."""
        if not PYKRX_AVAILABLE:
            logger.error("pykrx 라이브러리를 사용할 수 없습니다.")
            raise ImportError("pykrx 라이브러리가 필요합니다: pip install pykrx")
        
        logger.info("pykrx 주식 데이터 클라이언트가 초기화되었습니다.")
    
    def get_stock_ohlcv(self, stock_code: str, start_date: str, end_date: str) -> Optional[object]:
        """
        특정 기간의 주식 OHLCV 데이터를 조회합니다.
        
        Args:
            stock_code (str): 종목코드 (6자리)
            start_date (str): 시작일 (YYYYMMDD)
            end_date (str): 종료일 (YYYYMMDD)
            
        Returns:
            Optional[pd.DataFrame]: OHLCV 데이터프레임 (실패 시 None)
        """
        try:
            df = stock.get_market_ohlcv_by_date(
                fromdate=start_date,
                todate=end_date,
                ticker=stock_code
            )
            
            # 거래정지일 제거 (시가가 0인 경우)
            if not df.empty:
                df = df[df['시가'] != 0].copy()
            
            return df if not df.empty else None
            
        except Exception as e:
            logger.error(f"주식 OHLCV 조회 실패 ({stock_code}): {e}")
            return None
    
    def get_current_price(self, stock_code: str) -> Optional[Dict]:
        """
        종목의 현재가 정보를 조회합니다.
        
        Args:
            stock_code (str): 종목코드 (6자리)
            
        Returns:
            Optional[Dict]: 현재가 정보 딕셔너리 (실패 시 None)
        """
        try:
            today = datetime.now().strftime("%Y%m%d")
            # 최근 5일치 데이터를 가져와서 가장 최근 거래일 사용
            start_date = (datetime.now() - timedelta(days=5)).strftime("%Y%m%d")
            
            df = self.get_stock_ohlcv(stock_code, start_date, today)
            
            if df is None or df.empty:
                logger.warning(f"현재가 조회 실패: 최근 거래 데이터 없음 ({stock_code})")
                return None
            
            # 가장 최근 거래일 데이터
            latest_data = df.iloc[-1]
            
            return {
                'date': latest_data.name.strftime("%Y%m%d"),
                'open': int(latest_data['시가']),
                'high': int(latest_data['고가']),
                'low': int(latest_data['저가']),
                'close': int(latest_data['종가']),
                'volume': int(latest_data['거래량']),
                'value': int(latest_data.get('거래대금', 0)) if '거래대금' in latest_data.index else 0
            }
            
        except Exception as e:
            logger.error(f"현재가 조회 중 오류 ({stock_code}): {e}")
            return None
    
    def get_market_index(self, market_type: str, start_date: str, end_date: str) -> Optional[object]:
        """
        시장 지수 데이터를 조회합니다.
        
        Args:
            market_type (str): 시장 구분 (KOSPI 또는 KOSDAQ)
            start_date (str): 시작일 (YYYYMMDD)
            end_date (str): 종료일 (YYYYMMDD)
            
        Returns:
            Optional[pd.DataFrame]: 지수 데이터프레임 (실패 시 None)
        """
        try:
            # KOSPI: "KOSPI", KOSDAQ: "KOSDAQ"
            index_name = "KOSPI" if market_type == "KOSPI" else "KOSDAQ"
            
            df = stock.get_index_ohlcv_by_date(
                fromdate=start_date,
                todate=end_date,
                ticker=index_name
            )
            
            return df if not df.empty else None
            
        except Exception as e:
            logger.error(f"시장지수 조회 실패 ({market_type}): {e}")
            return None
    
    def get_market_cap(self, stock_code: str, date: str = None) -> Optional[int]:
        """
        특정 종목의 시가총액을 조회합니다.
        
        Args:
            stock_code (str): 종목코드 (6자리)
            date (str): 조회 날짜 (YYYYMMDD), None이면 오늘
            
        Returns:
            Optional[int]: 시가총액 (억원 단위, 실패 시 None)
        """
        try:
            if date is None:
                date = datetime.now().strftime("%Y%m%d")
            
            # 시가총액 조회 (원 단위)
            market_cap_raw = stock.get_market_cap_by_date(
                fromdate=date,
                todate=date,
                ticker=stock_code
            )
            
            if market_cap_raw is None or market_cap_raw.empty:
                return None
            
            # 시가총액을 억원 단위로 변환
            latest_cap = market_cap_raw.iloc[-1]['시가총액']
            market_cap_eok = int(latest_cap / 100000000)
            
            return market_cap_eok
            
        except Exception as e:
            logger.error(f"시가총액 조회 실패 ({stock_code}): {e}")
            return None


class StockAnalyzer:
    """주식 분석 메인 클래스"""
    
    def __init__(self):
        """
        주식 분석기를 초기화합니다.
        pykrx를 사용하므로 별도 API 키가 필요하지 않습니다.
        """
        if not PYKRX_AVAILABLE:
            logger.error("pykrx 라이브러리를 사용할 수 없습니다.")
            self.pykrx_client = None
        else:
            self.pykrx_client = PykrxStockDataClient()
        
        logger.info("주식 분석기가 초기화되었습니다 (pykrx 기반).")
    
    def analyze_stock_for_contract(self, contract_data: Dict) -> Optional[StockAnalysisResult]:
        """
        계약 정보와 함께 종목을 분석합니다.
        
        Args:
            contract_data (Dict): 계약 정보
            
        Returns:
            Optional[StockAnalysisResult]: 분석 결과 (실패 시 None)
        """
        if not self.pykrx_client:
            logger.error("pykrx 클라이언트를 사용할 수 없습니다.")
            return None
        
        stock_code = contract_data.get('종목코드', '')
        stock_name = contract_data.get('종목명', '')
        market_type = contract_data.get('시장구분', 'KOSPI')
        contract_amount = self._parse_number(contract_data.get('계약금액', '0'))
        recent_sales = self._parse_number(contract_data.get('최근 매출액', '0'))
        
        logger.info(f"종목 분석 시작: {stock_name}({stock_code})")
        
        try:
            # 오늘 날짜와 분석 기간 설정
            today = datetime.now().strftime("%Y%m%d")
            # 200일 이동평균 계산을 위해 최소 250일치 데이터 필요 (거래정지일 고려)
            start_date = (datetime.now() - timedelta(days=300)).strftime("%Y%m%d")
            
            # 1. 주식 데이터 조회
            stock_df = self.pykrx_client.get_stock_ohlcv(stock_code, start_date, today)
            if stock_df is None or stock_df.empty:
                return self._create_error_result(stock_code, stock_name, "주식 데이터 조회 실패")
            
            # 2. 현재가 정보
            current_price_info = self.pykrx_client.get_current_price(stock_code)
            if not current_price_info:
                return self._create_error_result(stock_code, stock_name, "현재가 조회 실패")
            
            current_price = current_price_info['close']
            
            # 3. 시가총액 조회
            market_cap = self.pykrx_client.get_market_cap(stock_code)
            if market_cap is None:
                # 시가총액을 직접 계산 (상장주식수 * 현재가)
                listed_shares = self._parse_number(contract_data.get('상장주식수', '0'))
                if listed_shares > 0:
                    market_cap = (current_price * listed_shares) // 100000000
                else:
                    market_cap = 0
            
            # 4. 시장 지수 데이터 조회
            index_df = self.pykrx_client.get_market_index(market_type, start_date, today)
            if index_df is None or index_df.empty:
                return self._create_error_result(stock_code, stock_name, "시장지수 조회 실패")
            
            # 5. 분석 수행
            analysis_result = self._perform_analysis(
                stock_code, stock_name, market_type, current_price, market_cap,
                contract_amount, recent_sales, stock_df, index_df, current_price_info
            )
            
            logger.info(f"종목 분석 완료: {stock_name} (점수: {analysis_result.recommendation_score}/10)")
            return analysis_result
            
        except Exception as e:
            logger.error(f"종목 분석 중 오류 발생 ({stock_name}): {e}")
            return self._create_error_result(stock_code, stock_name, f"분석 오류: {str(e)}")
    
    def _perform_analysis(self, stock_code: str, stock_name: str, market_type: str, 
                         current_price: int, market_cap: int, contract_amount: int,
                         recent_sales: int, stock_df: object, index_df: object,
                         current_price_info: Dict) -> StockAnalysisResult:
        """실제 분석을 수행합니다."""
        
        # 1. 시장지수 200일 이동평균 비교
        index_current = float(index_df.iloc[-1]['종가'])
        
        # 200일 이동평균 계산 (최소 200일 데이터가 있어야 함)
        if len(index_df) >= 200:
            index_ma200 = float(index_df['종가'].tail(200).mean())
        else:
            # 데이터가 부족한 경우 사용 가능한 모든 데이터의 평균 사용
            index_ma200 = float(index_df['종가'].mean())
            logger.warning(f"시장지수 200일 이동평균 계산에 충분한 데이터가 없습니다 ({len(index_df)}일)")
        
        is_index_above_ma200 = index_current > index_ma200
        
        # 2. 시가총액 범위 체크 (500억 ~ 5,000억)
        is_market_cap_in_range = 500 <= market_cap <= 5000
        
        # 3. 매출 대비 계약금액 비율
        contract_sales_ratio = (contract_amount / recent_sales * 100) if recent_sales > 0 else 0
        is_contract_ratio_over_20 = contract_sales_ratio > 20
        
        # 4. 거래 조건 체크
        # 4-1. 거래대금 비율 (20일 평균 대비)
        if len(stock_df) >= 20:
            recent_20_days = stock_df.tail(20)
            avg_volume_20days = recent_20_days['거래량'].mean()
            today_volume = current_price_info['volume']
            volume_ratio = today_volume / avg_volume_20days if avg_volume_20days > 0 else 0
        else:
            volume_ratio = 1.0
            logger.warning(f"거래량 비율 계산에 충분한 데이터가 없습니다 ({len(stock_df)}일)")
        
        # 4-2. 양봉/음봉 체크
        is_positive_candle = current_price_info['close'] > current_price_info['open']
        
        # 거래 조건 만족 개수
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
