"""
거래 전략 모듈

이 모듈은 공시 기반 매수 조건 판단 및 전체 거래 전략을 관리합니다.
"""

from typing import Dict, Optional, List
from decimal import Decimal
from datetime import datetime
from loguru import logger
import pytz

from src.trading.kiwoom_client import KiwoomAPIClient
from src.trading.order_manager import OrderManager
from src.trading.position_manager import PositionManager
from src.utils.market_schedule import is_market_open, is_trading_hours


class TradingStrategy:
    """거래 전략 클래스"""
    
    # 매수 조건
    MIN_SCORE = 8  # 최소 투자 점수
    PROFIT_TARGET = Decimal('0.03')  # 3% 익절 목표
    
    def __init__(self, kiwoom_client: KiwoomAPIClient, 
                 order_manager: OrderManager,
                 position_manager: PositionManager):
        """
        거래 전략을 초기화합니다.
        
        Args:
            kiwoom_client: 키움증권 API 클라이언트
            order_manager: 주문 관리자
            position_manager: 포지션 관리자
        """
        self.kiwoom = kiwoom_client
        self.order_mgr = order_manager
        self.position_mgr = position_manager
        
        logger.info("거래 전략 초기화 완료")
    
    def _is_today_disclosure(self, disclosure_date: str) -> bool:
        """
        공시가 오늘 날짜인지 확인합니다.
        
        Args:
            disclosure_date: 공시 접수일자 (YYYYMMDD)
            
        Returns:
            bool: 오늘 공시 여부
        """
        try:
            # 한국 시간대 기준
            kst = pytz.timezone('Asia/Seoul')
            today = datetime.now(kst).strftime('%Y%m%d')
            
            is_today = disclosure_date == today
            logger.debug(f"공시 날짜 확인: {disclosure_date} (오늘: {today}) → {is_today}")
            
            return is_today
            
        except Exception as e:
            logger.error(f"공시 날짜 확인 중 오류: {e}")
            return False
    
    def should_buy(self, contract_data: Dict, analysis_result: any) -> Dict[str, any]:
        """
        매수 조건을 확인합니다.
        
        Args:
            contract_data: 계약 정보
            analysis_result: 주식 분석 결과 (StockAnalysisResult)
            
        Returns:
            Dict: 매수 판단 결과
                - should_buy: 매수 여부 (bool)
                - reason: 판단 사유
                - score: 투자 점수
        """
        try:
            logger.info("=" * 60)
            logger.info("매수 조건 검토 시작")
            logger.info("=" * 60)
            
            # 조건 체크 결과
            checks = []
            
            # 1. 시장 개장 확인
            if not is_market_open():
                reason = "시장 휴장일"
                logger.warning(f"❌ {reason}")
                return {'should_buy': False, 'reason': reason, 'score': 0}
            checks.append("✅ 시장 개장일")
            
            # 2. 거래 시간 확인 (09:00 ~ 15:20, 마감 10분 전까지만 매수)
            if not is_trading_hours(allow_buy=True):
                reason = "거래 시간 외 (매수는 09:00~15:20만 가능)"
                logger.warning(f"❌ {reason}")
                return {'should_buy': False, 'reason': reason, 'score': 0}
            checks.append("✅ 거래 시간 내")
            
            # 3. 오늘 공시 확인
            disclosure_date = contract_data.get('접수일자', '')
            if not self._is_today_disclosure(disclosure_date):
                reason = f"오늘 공시 아님 (접수일: {disclosure_date})"
                logger.info(f"❌ {reason}")
                return {'should_buy': False, 'reason': reason, 'score': 0}
            checks.append("✅ 오늘 공시")
            
            # 4. 투자 점수 확인
            score = analysis_result.recommendation_score if analysis_result else 0
            if score < self.MIN_SCORE:
                reason = f"투자 점수 부족 ({score}점 < {self.MIN_SCORE}점)"
                logger.info(f"❌ {reason}")
                return {'should_buy': False, 'reason': reason, 'score': score}
            checks.append(f"✅ 투자 점수 충족 ({score}점)")
            
            # 5. 보유 종목 확인 (한 종목만 보유)
            current_position = self.position_mgr.get_current_position()
            if current_position:
                reason = f"이미 보유 중인 종목 있음 ({current_position['stock_name']})"
                logger.warning(f"❌ {reason}")
                return {'should_buy': False, 'reason': reason, 'score': score}
            checks.append("✅ 보유 종목 없음")
            
            # 모든 조건 충족
            logger.info("🎉 모든 매수 조건 충족!")
            for check in checks:
                logger.info(f"  {check}")
            
            return {
                'should_buy': True,
                'reason': '모든 매수 조건 충족',
                'score': score
            }
            
        except Exception as e:
            logger.error(f"매수 조건 확인 중 오류 발생: {e}")
            return {'should_buy': False, 'reason': f'오류 발생: {str(e)}', 'score': 0}
    
    def execute_buy_strategy(self, stock_code: str, stock_name: str) -> Optional[Dict]:
        """
        매수 전략을 실행합니다.
        
        Args:
            stock_code: 종목코드
            stock_name: 종목명
            
        Returns:
            Optional[Dict]: 매수 결과 (실패 시 None)
                - order_number: 주문번호
                - stock_code: 종목코드
                - stock_name: 종목명
                - quantity: 체결수량
                - executed_price: 체결가격 (Decimal)
                - executed_amount: 체결금액 (Decimal)
                - buy_time: 매수시각
        """
        try:
            logger.info("=" * 60)
            logger.info(f"🔵 매수 전략 실행: {stock_name}({stock_code})")
            logger.info("=" * 60)
            
            # 1. 시장가 매수 주문
            order_result = self.order_mgr.place_market_buy_order(stock_code, stock_name)
            if not order_result:
                logger.error("매수 주문 실패")
                return None
            
            order_number = order_result['order_number']
            logger.info(f"매수 주문 완료 - 주문번호: {order_number}")
            
            # 2. 체결 확인 (최대 10초 대기)
            import time
            for attempt in range(5):
                time.sleep(2)
                
                execution = self.order_mgr.check_order_execution(order_number, stock_code)
                if execution and execution['executed']:
                    logger.info(f"✅ 매수 체결 완료: {execution['executed_quantity']}주 @ {execution['executed_price']:,}원")
                    
                    # 3. 익절 매도 주문 설정 (+3%)
                    logger.info("익절 매도 주문 설정 중...")
                    sell_result = self.order_mgr.place_limit_sell_order(
                        stock_code=stock_code,
                        stock_name=stock_name,
                        quantity=execution['executed_quantity'],
                        buy_price=execution['executed_price'],
                        profit_rate=self.PROFIT_TARGET
                    )
                    
                    if sell_result:
                        logger.info(f"✅ 익절 매도 주문 설정 완료: {sell_result['sell_price']:,}원")
                    else:
                        logger.warning("⚠️ 익절 매도 주문 설정 실패 (나중에 다시 시도)")
                    
                    return {
                        'order_number': order_number,
                        'stock_code': stock_code,
                        'stock_name': stock_name,
                        'quantity': execution['executed_quantity'],
                        'executed_price': execution['executed_price'],
                        'executed_amount': execution['executed_amount'],
                        'buy_time': datetime.now(),
                        'sell_order_number': sell_result['order_number'] if sell_result else None
                    }
                
                logger.debug(f"체결 대기 중... (시도 {attempt+1}/5)")
            
            logger.warning("⚠️ 체결 확인 실패 (나중에 다시 확인 필요)")
            return None
            
        except Exception as e:
            logger.error(f"매수 전략 실행 중 오류 발생: {e}")
            return None
    
    def execute_position_management(self, buy_date: datetime) -> Optional[Dict]:
        """
        보유 포지션 관리 전략을 실행합니다.
        
        Args:
            buy_date: 매수일시
            
        Returns:
            Optional[Dict]: 매도 결과 (매도하지 않았으면 None)
                - action: 실행 동작 ('sell_executed' or 'order_placed')
                - stock_code: 종목코드
                - stock_name: 종목명
                - quantity: 수량
                - executed_price: 체결가격 (Decimal, 매도 체결 시)
                - sell_price: 주문가격 (Decimal, 주문 설정 시)
                - profit_rate: 수익률 (Decimal)
                - reason: 사유
        """
        try:
            logger.info("=" * 60)
            logger.info("🔄 포지션 관리 전략 실행")
            logger.info("=" * 60)
            
            # 1. 현재 포지션 조회
            position = self.position_mgr.get_current_position()
            if not position:
                logger.debug("보유 포지션 없음")
                return None
            
            stock_code = position['stock_code']
            stock_name = position['stock_name']
            quantity = position['quantity']
            avg_price = position['avg_price']
            
            # 2. 매도 주문 존재 여부 확인
            has_sell_order = self.order_mgr.has_pending_orders(stock_code)
            
            # 3. 매도 전략 결정
            strategy = self.position_mgr.get_sell_strategy(position, buy_date, has_sell_order)
            
            if not strategy:
                logger.debug("매도 조건 미충족")
                return None
            
            logger.info(f"매도 전략: {strategy['reason']}")
            
            # 4. 매도 주문 실행
            if strategy['action'] == 'place_order':
                if strategy['sell_type'] == 'market':
                    # 시장가 매도
                    sell_result = self.order_mgr.place_market_sell_order(
                        stock_code=stock_code,
                        stock_name=stock_name,
                        quantity=quantity
                    )
                    
                    if sell_result:
                        logger.info(f"✅ 시장가 매도 주문 완료")
                        
                        # 체결 확인
                        import time
                        time.sleep(2)
                        execution = self.order_mgr.check_order_execution(sell_result['order_number'], stock_code)
                        
                        if execution and execution['executed']:
                            executed_price = execution['executed_price']
                            profit_rate = (executed_price - avg_price) / avg_price
                            
                            logger.info(f"✅ 매도 체결 완료: {executed_price:,}원 (수익률: {profit_rate*100:.2f}%)")
                            
                            return {
                                'action': 'sell_executed',
                                'stock_code': stock_code,
                                'stock_name': stock_name,
                                'quantity': quantity,
                                'executed_price': executed_price,
                                'profit_rate': profit_rate,
                                'reason': strategy['reason']
                            }
                        else:
                            logger.warning("⚠️ 매도 체결 대기 중")
                            return {
                                'action': 'order_placed',
                                'stock_code': stock_code,
                                'stock_name': stock_name,
                                'quantity': quantity,
                                'reason': strategy['reason']
                            }
                    
                elif strategy['sell_type'] == 'limit':
                    # 지정가 매도
                    sell_result = self.order_mgr.place_limit_sell_order(
                        stock_code=stock_code,
                        stock_name=stock_name,
                        quantity=quantity,
                        buy_price=avg_price,
                        profit_rate=strategy['profit_rate']
                    )
                    
                    if sell_result:
                        logger.info(f"✅ 지정가 매도 주문 완료: {sell_result['sell_price']:,}원")
                        return {
                            'action': 'order_placed',
                            'stock_code': stock_code,
                            'stock_name': stock_name,
                            'quantity': quantity,
                            'sell_price': sell_result['sell_price'],
                            'reason': strategy['reason']
                        }
            
            return None
            
        except Exception as e:
            logger.error(f"포지션 관리 전략 실행 중 오류 발생: {e}")
            return None

