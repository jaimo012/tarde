"""
주식 시장 데이터 분석 모듈

이 모듈은 pykrx 라이브러리를 사용하여 주식 데이터를 수집하고
계약 정보와 함께 종목 분석을 수행합니다.
"""

from typing import Dict, Optional, Tuple
from datetime import datetime, timedelta
from loguru import logger
from dataclasses import dataclass
import io
import os
import tempfile

try:
    from pykrx import stock
    PYKRX_AVAILABLE = True
except ImportError:
    PYKRX_AVAILABLE = False
    logger.warning("pykrx 라이브러리가 설치되지 않았습니다. pip install pykrx로 설치하세요.")

try:
    import matplotlib
    matplotlib.use('Agg')  # GUI 없는 환경에서 실행
    import matplotlib.pyplot as plt
    import matplotlib.font_manager as fm
    from matplotlib import dates as mdates
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    logger.warning("matplotlib 라이브러리가 설치되지 않았습니다.")


@dataclass
class StockAnalysisResult:
    """주식 분석 결과를 담는 데이터 클래스"""
    stock_code: str
    stock_name: str
    market_type: str  # KOSPI, KOSDAQ
    industry_code: str  # 업종 코드
    industry_name: str  # 업종명
    is_target_industry: bool  # 주목 업종 여부
    
    current_price: int
    opening_price: int  # 당일 시가
    price_change_rate: float  # 등락률 (%)
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
    
    # 차트 이미지 경로
    chart_image_path: Optional[str] = None


class PykrxStockDataClient:
    """pykrx를 사용한 주식 데이터 클라이언트"""
    
    def __init__(self):
        """pykrx 클라이언트를 초기화합니다."""
        if not PYKRX_AVAILABLE:
            logger.error("pykrx 라이브러리를 사용할 수 없습니다.")
            raise ImportError("pykrx 라이브러리가 필요합니다: pip install pykrx")
        
        logger.info("pykrx 주식 데이터 클라이언트가 초기화되었습니다.")
    
    def get_stock_ohlcv(self, stock_code: str, start_date: str, end_date: str, retry_with_prev_day: bool = True) -> Optional[object]:
        """
        특정 기간의 주식 OHLCV 데이터를 조회합니다.
        
        Args:
            stock_code (str): 종목코드 (6자리)
            start_date (str): 시작일 (YYYYMMDD)
            end_date (str): 종료일 (YYYYMMDD)
            retry_with_prev_day (bool): 데이터가 없을 때 전일로 재시도 여부
            
        Returns:
            Optional[pd.DataFrame]: OHLCV 데이터프레임 (실패 시 None)
        """
        try:
            logger.debug(f"주식 OHLCV 조회 시도: {stock_code}, 기간: {start_date} ~ {end_date}")
            
            df = stock.get_market_ohlcv_by_date(
                fromdate=start_date,
                todate=end_date,
                ticker=stock_code
            )
            
            # 거래정지일 제거 (시가가 0인 경우)
            if not df.empty:
                df = df[df['시가'] != 0].copy()
            
            # 데이터가 없고 재시도 옵션이 켜져 있으면 전일로 재시도
            if df.empty and retry_with_prev_day:
                logger.warning(f"오늘({end_date}) 데이터 없음. 전일 기준으로 재시도...")
                
                # 전일 계산 (최대 5일 전까지)
                from datetime import datetime, timedelta
                end_dt = datetime.strptime(end_date, "%Y%m%d")
                
                for days_back in range(1, 6):
                    prev_date = (end_dt - timedelta(days=days_back)).strftime("%Y%m%d")
                    logger.debug(f"재시도 {days_back}일 전: {prev_date}")
                    
                    df = stock.get_market_ohlcv_by_date(
                        fromdate=start_date,
                        todate=prev_date,
                        ticker=stock_code
                    )
                    
                    if not df.empty:
                        df = df[df['시가'] != 0].copy()
                        
                    if not df.empty:
                        logger.info(f"✅ {prev_date} 날짜로 데이터 조회 성공 (오늘 데이터 미제공)")
                        break
            
            if df.empty:
                logger.warning(f"주식 OHLCV 조회 결과 없음 ({stock_code}, {start_date}~{end_date})")
                return None
            
            logger.debug(f"데이터 조회 성공: {len(df)}일치 ({stock_code})")
            return df
            
        except Exception as e:
            logger.error(f"주식 OHLCV 조회 실패 ({stock_code}): {e}")
            import traceback
            logger.debug(f"상세 오류:\n{traceback.format_exc()}")
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
    
    def get_market_index(self, market_type: str, start_date: str, end_date: str, retry_with_prev_day: bool = True) -> Optional[object]:
        """
        시장 지수 데이터를 조회합니다.
        
        Args:
            market_type (str): 시장 구분 (KOSPI 또는 KOSDAQ)
            start_date (str): 시작일 (YYYYMMDD)
            end_date (str): 종료일 (YYYYMMDD)
            retry_with_prev_day (bool): 데이터가 없을 때 전일로 재시도 여부
            
        Returns:
            Optional[pd.DataFrame]: 지수 데이터프레임 (실패 시 None)
        """
        try:
            # pykrx API에서 사용하는 정확한 ticker 코드 (숫자)
            # KOSPI: "1001", KOSDAQ: "2001"
            index_ticker = "1001" if market_type == "KOSPI" else "2001"
            
            logger.debug(f"시장지수 조회 시도: {market_type} (ticker={index_ticker}), 기간: {start_date} ~ {end_date}")
            
            df = stock.get_index_ohlcv_by_date(
                fromdate=start_date,
                todate=end_date,
                ticker=index_ticker
            )
            
            # 데이터가 없고 재시도 옵션이 켜져 있으면 전일로 재시도
            if df.empty and retry_with_prev_day:
                logger.warning(f"오늘({end_date}) 지수 데이터 없음. 전일 기준으로 재시도...")
                
                # 전일 계산 (최대 5일 전까지)
                from datetime import datetime, timedelta
                end_dt = datetime.strptime(end_date, "%Y%m%d")
                
                for days_back in range(1, 6):
                    prev_date = (end_dt - timedelta(days=days_back)).strftime("%Y%m%d")
                    logger.debug(f"재시도 {days_back}일 전: {prev_date}")
                    
                    df = stock.get_index_ohlcv_by_date(
                        fromdate=start_date,
                        todate=prev_date,
                        ticker=index_ticker
                    )
                    
                    if not df.empty:
                        logger.info(f"✅ {prev_date} 날짜로 지수 데이터 조회 성공 (오늘 데이터 미제공)")
                        break
            
            if df.empty:
                logger.warning(f"시장지수 조회 결과 없음 ({market_type}, ticker={index_ticker}, {start_date}~{end_date})")
                return None
            
            logger.debug(f"지수 데이터 조회 성공: {len(df)}일치 ({market_type}, ticker={index_ticker})")
            return df
            
        except Exception as e:
            logger.error(f"시장지수 조회 실패 ({market_type}): {e}")
            import traceback
            logger.debug(f"상세 오류:\n{traceback.format_exc()}")
            return None
    
    def get_market_cap(self, stock_code: str, date: str = None, retry_with_prev_day: bool = True) -> Optional[int]:
        """
        특정 종목의 시가총액을 조회합니다.
        
        Args:
            stock_code (str): 종목코드 (6자리)
            date (str): 조회 날짜 (YYYYMMDD), None이면 오늘
            retry_with_prev_day (bool): 데이터가 없을 때 전일로 재시도 여부
            
        Returns:
            Optional[int]: 시가총액 (억원 단위, 실패 시 None)
        """
        try:
            if date is None:
                date = datetime.now().strftime("%Y%m%d")
            
            logger.debug(f"시가총액 조회 시도: {stock_code}, 날짜: {date}")
            
            # 시가총액 조회 (원 단위)
            market_cap_raw = stock.get_market_cap_by_date(
                fromdate=date,
                todate=date,
                ticker=stock_code
            )
            
            # 데이터가 없고 재시도 옵션이 켜져 있으면 전일로 재시도
            if (market_cap_raw is None or market_cap_raw.empty) and retry_with_prev_day:
                logger.warning(f"오늘({date}) 시가총액 데이터 없음. 전일 기준으로 재시도...")
                
                # 전일 계산 (최대 5일 전까지)
                date_dt = datetime.strptime(date, "%Y%m%d")
                
                for days_back in range(1, 6):
                    prev_date = (date_dt - timedelta(days=days_back)).strftime("%Y%m%d")
                    logger.debug(f"재시도 {days_back}일 전: {prev_date}")
                    
                    market_cap_raw = stock.get_market_cap_by_date(
                        fromdate=prev_date,
                        todate=prev_date,
                        ticker=stock_code
                    )
                    
                    if market_cap_raw is not None and not market_cap_raw.empty:
                        logger.info(f"✅ {prev_date} 날짜로 시가총액 조회 성공 (오늘 데이터 미제공)")
                        break
            
            if market_cap_raw is None or market_cap_raw.empty:
                logger.warning(f"시가총액 조회 결과 없음 ({stock_code}, {date})")
                return None
            
            # 시가총액을 억원 단위로 변환
            latest_cap = market_cap_raw.iloc[-1]['시가총액']
            market_cap_eok = int(latest_cap / 100000000)
            
            logger.debug(f"시가총액 조회 성공: {market_cap_eok:,}억원 ({stock_code})")
            return market_cap_eok
            
        except Exception as e:
            logger.error(f"시가총액 조회 실패 ({stock_code}): {e}")
            import traceback
            logger.debug(f"상세 오류:\n{traceback.format_exc()}")
            return None


class StockChartGenerator:
    """주식 차트 생성 클래스"""
    
    def __init__(self):
        """차트 생성기를 초기화합니다."""
        if not MATPLOTLIB_AVAILABLE:
            logger.warning("matplotlib을 사용할 수 없어 차트를 생성할 수 없습니다.")
        
        # 한글 폰트 설정 (Windows 환경)
        try:
            if os.name == 'nt':  # Windows
                plt.rcParams['font.family'] = 'Malgun Gothic'
            else:
                plt.rcParams['font.family'] = 'DejaVu Sans'
            plt.rcParams['axes.unicode_minus'] = False
        except Exception as e:
            logger.warning(f"폰트 설정 실패: {e}")
    
    def create_candlestick_chart(self, stock_code: str, stock_name: str, 
                                  df: object, days_to_show: int = 20) -> Optional[str]:
        """
        캔들스틱 차트를 생성합니다.
        
        Args:
            stock_code (str): 종목코드
            stock_name (str): 종목명
            df (pd.DataFrame): OHLCV 데이터 (100일 이상)
            days_to_show (int): 표시할 일수 (기본 20일)
            
        Returns:
            Optional[str]: 저장된 차트 이미지 경로 (실패 시 None)
        """
        if not MATPLOTLIB_AVAILABLE:
            return None
        
        try:
            # 최근 N일 데이터만 표시
            df_display = df.tail(days_to_show).copy()
            
            # 5일, 20일 이동평균 계산 (전체 데이터 사용)
            df['MA5'] = df['종가'].rolling(window=5).mean()
            df['MA20'] = df['종가'].rolling(window=20).mean()
            
            # Figure 생성
            fig, ax = plt.subplots(figsize=(14, 7))
            
            # 캔들스틱 그리기
            for idx, (date, row) in enumerate(df_display.iterrows()):
                # 양봉/음봉 색상 결정
                color = 'red' if row['종가'] >= row['시가'] else 'blue'
                
                # 캔들 몸통
                height = abs(row['종가'] - row['시가'])
                bottom = min(row['시가'], row['종가'])
                ax.bar(idx, height, width=0.6, bottom=bottom, color=color, alpha=0.8)
                
                # 꼬리 (고가-저가)
                ax.plot([idx, idx], [row['저가'], row['고가']], color=color, linewidth=1)
            
            # 이동평균선 추가 (표시 구간에 해당하는 부분만)
            ma5_display = df['MA5'].tail(days_to_show)
            ma20_display = df['MA20'].tail(days_to_show)
            
            x_range = range(len(df_display))
            ax.plot(x_range, ma5_display.values, label='MA5', color='orange', linewidth=1.5)
            ax.plot(x_range, ma20_display.values, label='MA20', color='green', linewidth=1.5)
            
            # X축 날짜 레이블
            dates = [date.strftime('%m/%d') for date in df_display.index]
            ax.set_xticks(range(0, len(dates), max(1, len(dates)//10)))
            ax.set_xticklabels([dates[i] for i in range(0, len(dates), max(1, len(dates)//10))], rotation=45)
            
            # 차트 꾸미기
            ax.set_title(f'{stock_name}({stock_code}) - 최근 {days_to_show}일', fontsize=16, fontweight='bold')
            ax.set_xlabel('날짜', fontsize=12)
            ax.set_ylabel('가격 (원)', fontsize=12)
            ax.legend(loc='best')
            ax.grid(True, alpha=0.3)
            
            # Y축 가격 포맷팅 (천 단위 구분)
            ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{int(x):,}'))
            
            plt.tight_layout()
            
            # 임시 파일로 저장
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.png', prefix=f'chart_{stock_code}_')
            chart_path = temp_file.name
            plt.savefig(chart_path, dpi=100, bbox_inches='tight')
            plt.close(fig)
            
            logger.info(f"차트 생성 완료: {chart_path}")
            return chart_path
            
        except Exception as e:
            logger.error(f"차트 생성 실패 ({stock_code}): {e}")
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
        
        self.chart_generator = StockChartGenerator()
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
        industry_code = contract_data.get('업종코드', '')
        industry_name = contract_data.get('업종명', '')
        contract_amount = self._parse_number(contract_data.get('계약금액', '0'))
        recent_sales = self._parse_number(contract_data.get('최근 매출액', '0'))
        
        logger.info(f"종목 분석 시작: {stock_name}({stock_code})")
        
        try:
            # 업종 확인
            is_target_industry = self._check_target_industry(industry_code)
            
            # 오늘 날짜와 분석 기간 설정
            today = datetime.now().strftime("%Y%m%d")
            # 차트 생성을 위해 100일치 데이터 필요 (거래정지일 고려하여 여유있게)
            start_date = (datetime.now() - timedelta(days=150)).strftime("%Y%m%d")
            
            # 1. 주식 데이터 조회 (100일치 이상)
            logger.info(f"  → 1단계: 주식 OHLCV 데이터 조회 중... (최근 150일)")
            stock_df = self.pykrx_client.get_stock_ohlcv(stock_code, start_date, today)
            if stock_df is None or stock_df.empty:
                error_msg = f"주식 데이터 조회 실패 - pykrx API에서 데이터를 가져올 수 없습니다. 종목코드({stock_code})가 정확한지 확인하세요."
                logger.error(f"  ❌ {error_msg}")
                return self._create_error_result(stock_code, stock_name, industry_code, 
                                                 industry_name, is_target_industry, error_msg)
            
            logger.info(f"  ✅ 주식 데이터 조회 성공: {len(stock_df)}일치")
            
            # 2. 현재가 정보
            logger.info(f"  → 2단계: 현재가 정보 조회 중...")
            current_price_info = self.pykrx_client.get_current_price(stock_code)
            if not current_price_info:
                error_msg = f"현재가 조회 실패 - 최근 5일 거래 데이터가 없습니다. 거래정지 종목일 가능성이 있습니다."
                logger.error(f"  ❌ {error_msg}")
                return self._create_error_result(stock_code, stock_name, industry_code,
                                                 industry_name, is_target_industry, error_msg)
            
            current_price = current_price_info['close']
            opening_price = current_price_info['open']
            
            # 등락률 계산
            if opening_price > 0:
                price_change_rate = ((current_price - opening_price) / opening_price) * 100
            else:
                price_change_rate = 0.0
            
            logger.info(f"  ✅ 현재가 조회 성공: {current_price:,}원 (시가: {opening_price:,}원)")
            
            # 3. 시가총액 조회
            logger.info(f"  → 3단계: 시가총액 조회 중...")
            market_cap = self.pykrx_client.get_market_cap(stock_code)
            if market_cap is None:
                logger.warning(f"  ⚠️ pykrx에서 시가총액 조회 실패 - 계산으로 대체 시도")
                # 시가총액을 직접 계산 (상장주식수 * 현재가)
                listed_shares = self._parse_number(contract_data.get('상장주식수', '0'))
                if listed_shares > 0:
                    market_cap = (current_price * listed_shares) // 100000000
                    logger.info(f"  ✅ 시가총액 계산 완료: {market_cap:,}억원")
                else:
                    market_cap = 0
                    logger.warning(f"  ⚠️ 상장주식수 정보 없음 - 시가총액 0으로 설정")
            else:
                logger.info(f"  ✅ 시가총액 조회 성공: {market_cap:,}억원")
            
            # 4. 시장 지수 데이터 조회
            logger.info(f"  → 4단계: 시장 지수({market_type}) 데이터 조회 중...")
            index_df = self.pykrx_client.get_market_index(market_type, start_date, today)
            if index_df is None or index_df.empty:
                error_msg = f"시장지수 조회 실패 - {market_type} 지수 데이터를 가져올 수 없습니다."
                logger.error(f"  ❌ {error_msg}")
                return self._create_error_result(stock_code, stock_name, industry_code,
                                                 industry_name, is_target_industry, error_msg)
            
            logger.info(f"  ✅ 시장 지수 조회 성공: {len(index_df)}일치")
            
            # 5. 차트 생성 (최근 20일 표시, 100일 데이터 사용)
            logger.info(f"  → 5단계: 주식 차트 생성 중...")
            chart_path = self.chart_generator.create_candlestick_chart(
                stock_code, stock_name, stock_df, days_to_show=20
            )
            
            if chart_path:
                logger.info(f"  ✅ 차트 생성 완료: {chart_path}")
            else:
                logger.warning(f"  ⚠️ 차트 생성 실패 (차트 없이 계속 진행)")
            
            # 6. 분석 수행
            logger.info(f"  → 6단계: 투자 점수 분석 수행 중...")
            analysis_result = self._perform_analysis(
                stock_code, stock_name, market_type, industry_code, industry_name, is_target_industry,
                current_price, opening_price, price_change_rate, market_cap,
                contract_amount, recent_sales, stock_df, index_df, current_price_info, chart_path
            )
            
            logger.info(f"✅ 종목 분석 완료: {stock_name} (투자 점수: {analysis_result.recommendation_score}/10)")
            return analysis_result
            
        except Exception as e:
            logger.error(f"종목 분석 중 오류 발생 ({stock_name}): {e}")
            return self._create_error_result(stock_code, stock_name, industry_code,
                                             industry_name, is_target_industry, f"분석 오류: {str(e)}")
    
    def _check_target_industry(self, industry_code: str) -> bool:
        """주목 업종인지 확인합니다."""
        try:
            from config.settings import TARGET_INDUSTRIES
            return industry_code in TARGET_INDUSTRIES
        except:
            return False
    
    def _perform_analysis(self, stock_code: str, stock_name: str, market_type: str,
                         industry_code: str, industry_name: str, is_target_industry: bool,
                         current_price: int, opening_price: int, price_change_rate: float,
                         market_cap: int, contract_amount: int, recent_sales: int,
                         stock_df: object, index_df: object, current_price_info: Dict,
                         chart_path: Optional[str]) -> StockAnalysisResult:
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
            industry_code=industry_code,
            industry_name=industry_name,
            is_target_industry=is_target_industry,
            current_price=current_price,
            opening_price=opening_price,
            price_change_rate=price_change_rate,
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
            recommendation_score=recommendation_score,
            chart_image_path=chart_path
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
    
    def _create_error_result(self, stock_code: str, stock_name: str, industry_code: str,
                            industry_name: str, is_target_industry: bool, error_msg: str) -> StockAnalysisResult:
        """오류 발생 시 기본 결과를 생성합니다."""
        return StockAnalysisResult(
            stock_code=stock_code,
            stock_name=stock_name,
            market_type="UNKNOWN",
            industry_code=industry_code,
            industry_name=industry_name,
            is_target_industry=is_target_industry,
            current_price=0,
            opening_price=0,
            price_change_rate=0.0,
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
            recommendation_score=0,
            chart_image_path=None
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
