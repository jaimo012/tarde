"""
포지션 관리 모듈

이 모듈은 보유 주식 포지션을 관리하고 보유 기간별 매도 전략을 실행합니다.
"""

from typing import Dict, Optional, List
from decimal import Decimal
from datetime import datetime, timedelta
from loguru import logger

from src.trading.kiwoom_client import KiwoomAPIClient


class PositionManager:
    """포지션 관리 클래스"""
    
    def __init__(self, kiwoom_client: KiwoomAPIClient):
        """
        포지션 관리자를 초기화합니다.
        
        Args:
            kiwoom_client: 키움증권 API 클라이언트
        """
        self.kiwoom = kiwoom_client
        logger.info("포지션 관리자 초기화 완료")
    
    def get_current_position(self) -> Optional[Dict]:
        """
        현재 보유 중인 포지션을 조회합니다 (1종목만 보유하는 전략).
        
        Returns:
            Optional[Dict]: 보유 포지션 정보 (없으면 None)
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
            positions = self.kiwoom.get_positions()
            
            if not positions or len(positions) == 0:
                logger.debug("보유 중인 포지션 없음")
                return None
            
            if len(positions) > 1:
                logger.warning(f"⚠️ 주의: 여러 종목 보유 중 ({len(positions)}개). 첫 번째 종목만 처리합니다.")
            
            position = positions[0]
            logger.info(f"현재 포지션: {position['stock_name']}({position['stock_code']}) "
                       f"{position['quantity']}주 @ {position['avg_price']:,}원 "
                       f"(수익률: {position['profit_rate']:.2f}%)")
            
            return position
            
        except Exception as e:
            logger.error(f"포지션 조회 중 오류 발생: {e}")
            return None
    
    def calculate_holding_days(self, buy_date: datetime) -> int:
        """
        보유 일수를 계산합니다.
        
        Args:
            buy_date: 매수일시
            
        Returns:
            int: 보유 일수
        """
        now = datetime.now()
        delta = now - buy_date
        holding_days = delta.days
        
        logger.debug(f"보유 기간: {holding_days}일 (매수일: {buy_date.strftime('%Y-%m-%d')})")
        return holding_days
    
    def should_sell_by_holding_period(self, buy_date: datetime, current_price: Decimal, 
                                     avg_price: Decimal) -> Dict[str, any]:
        """
        보유 기간에 따른 매도 여부를 판단합니다.
        
        Args:
            buy_date: 매수일시
            current_price: 현재가
            avg_price: 평균 매수가
            
        Returns:
            Dict: 매도 전략 정보
                - should_sell: 매도 여부 (bool)
                - sell_type: 매도 유형 ('market' or 'limit' or None)
                - reason: 매도 사유
                - target_price: 목표가 (지정가 매도 시, Decimal)
        """
        holding_days = self.calculate_holding_days(buy_date)
        
        # 현재가 대비 매수가 비율 계산
        price_ratio = (current_price - avg_price) / avg_price
        
        logger.info(f"보유 기간 분석: {holding_days}일 경과, "
                   f"현재가={current_price:,}원, 매수가={avg_price:,}원, "
                   f"등락률={price_ratio*100:.2f}%")
        
        # 10일 경과: 무조건 시장가 매도
        if holding_days >= 10:
            logger.warning(f"⚠️ 10일 경과 → 무조건 시장가 매도")
            return {
                'should_sell': True,
                'sell_type': 'market',
                'reason': f'10일 경과 (보유 {holding_days}일)',
                'target_price': None
            }
        
        # 5일 경과: 조건부 매도
        if holding_days >= 5:
            # 현재가가 매수가 ~ 매수가+3% 사이: 시장가 매도
            if Decimal('0') <= price_ratio < Decimal('0.03'):
                logger.warning(f"⚠️ 5일 경과 + 현재가 매수가~매수가+3% → 시장가 매도")
                return {
                    'should_sell': True,
                    'sell_type': 'market',
                    'reason': f'5일 경과, 현재가 {price_ratio*100:.2f}% (0~3% 구간)',
                    'target_price': None
                }
            
            # 현재가가 매수가 미만: 매수가 -1% 손절가 설정
            elif price_ratio < Decimal('0'):
                stop_loss_price = avg_price * Decimal('0.99')
                logger.warning(f"⚠️ 5일 경과 + 현재가 매수가 미만 → 손절가 설정 ({stop_loss_price:,}원)")
                return {
                    'should_sell': True,
                    'sell_type': 'limit',
                    'reason': f'5일 경과, 손절가 설정 (매수가 -1%)',
                    'target_price': stop_loss_price
                }
        
        # 매도 조건 미충족
        logger.debug("보유 기간 기준 매도 조건 미충족")
        return {
            'should_sell': False,
            'sell_type': None,
            'reason': '보유 유지',
            'target_price': None
        }
    
    def get_sell_strategy(self, position: Dict, buy_date: datetime, 
                         has_sell_order: bool) -> Optional[Dict]:
        """
        포지션에 대한 매도 전략을 결정합니다.
        
        Args:
            position: 포지션 정보
            buy_date: 매수일시
            has_sell_order: 매도 주문 설정 여부
            
        Returns:
            Optional[Dict]: 매도 전략 (None이면 매도 불필요)
                - action: 실행할 동작 ('place_order' or None)
                - sell_type: 매도 유형 ('market' or 'limit')
                - target_price: 목표가 (Decimal, 지정가인 경우)
                - profit_rate: 목표 수익률 (Decimal, 지정가인 경우)
                - reason: 사유
        """
        try:
            stock_code = position['stock_code']
            stock_name = position['stock_name']
            avg_price = position['avg_price']
            current_price = position['current_price']
            
            logger.info(f"매도 전략 분석: {stock_name}({stock_code})")
            
            # 1. 매도 주문이 설정되지 않은 경우 → 기본 익절가(+3%) 설정
            if not has_sell_order:
                logger.info("매도 주문 미설정 → 기본 익절가(+3%) 설정")
                return {
                    'action': 'place_order',
                    'sell_type': 'limit',
                    'target_price': avg_price * Decimal('1.03'),
                    'profit_rate': Decimal('0.03'),
                    'reason': '기본 익절가 설정 (매수가 +3%)'
                }
            
            # 2. 보유 기간에 따른 매도 전략
            holding_strategy = self.should_sell_by_holding_period(buy_date, current_price, avg_price)
            
            if holding_strategy['should_sell']:
                if holding_strategy['sell_type'] == 'market':
                    # 시장가 매도
                    return {
                        'action': 'place_order',
                        'sell_type': 'market',
                        'target_price': None,
                        'profit_rate': None,
                        'reason': holding_strategy['reason']
                    }
                elif holding_strategy['sell_type'] == 'limit':
                    # 지정가 매도 (손절가)
                    target_price = holding_strategy['target_price']
                    profit_rate = (target_price - avg_price) / avg_price
                    return {
                        'action': 'place_order',
                        'sell_type': 'limit',
                        'target_price': target_price,
                        'profit_rate': profit_rate,
                        'reason': holding_strategy['reason']
                    }
            
            # 3. 매도 조건 미충족
            logger.debug("매도 조건 미충족 → 보유 유지")
            return None
            
        except Exception as e:
            logger.error(f"매도 전략 분석 중 오류 발생: {e}")
            return None

