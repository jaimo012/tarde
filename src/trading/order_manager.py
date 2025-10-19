"""
주문 관리 모듈

이 모듈은 주식 매수/매도 주문을 관리하고 체결을 확인합니다.
"""

import time
from typing import Dict, Optional, Tuple
from decimal import Decimal, ROUND_DOWN
from datetime import datetime
from loguru import logger

from src.trading.kiwoom_client import KiwoomAPIClient


class OrderManager:
    """주문 관리 클래스"""
    
    # 수수료율 (매수/매도 수수료 + 거래세)
    COMMISSION_RATE = Decimal('0.00018')  # 0.018%
    
    def __init__(self, kiwoom_client: KiwoomAPIClient):
        """
        주문 관리자를 초기화합니다.
        
        Args:
            kiwoom_client: 키움증권 API 클라이언트
        """
        self.kiwoom = kiwoom_client
        logger.info("주문 관리자 초기화 완료")
    
    def _calculate_buy_quantity(self, available_amount: Decimal, price: Decimal) -> int:
        """
        매수 가능 수량을 계산합니다.
        
        Args:
            available_amount: 매수 가능 금액
            price: 주문 가격
            
        Returns:
            int: 매수 가능 수량
        """
        # 수수료를 고려한 매수 가능 수량 계산
        # 총 금액 = 주문금액 + 수수료
        # 주문금액 = 가격 * 수량
        # 수수료 = 주문금액 * 수수료율
        # 따라서: 총 금액 = 주문금액 * (1 + 수수료율)
        # 주문금액 = 총 금액 / (1 + 수수료율)
        
        order_amount = available_amount / (Decimal('1') + self.COMMISSION_RATE)
        quantity = int((order_amount / price).quantize(Decimal('1'), rounding=ROUND_DOWN))
        
        logger.debug(f"매수 가능 수량 계산: 가용금액={available_amount:,}원, 가격={price:,}원 → {quantity}주")
        return quantity
    
    def _calculate_sell_price(self, buy_price: Decimal, profit_rate: Decimal) -> int:
        """
        매도 가격을 계산합니다.
        
        Args:
            buy_price: 매수 가격
            profit_rate: 목표 수익률 (예: 0.03 = 3%)
            
        Returns:
            int: 매도 가격 (호가 단위로 조정)
        """
        target_price = buy_price * (Decimal('1') + profit_rate)
        
        # 호가 단위 조정 (한국 증시 호가 단위)
        if target_price < 1000:
            tick_size = 1
        elif target_price < 5000:
            tick_size = 5
        elif target_price < 10000:
            tick_size = 10
        elif target_price < 50000:
            tick_size = 50
        elif target_price < 100000:
            tick_size = 100
        elif target_price < 500000:
            tick_size = 500
        else:
            tick_size = 1000
        
        # 호가 단위로 반올림
        adjusted_price = int((target_price / tick_size).quantize(Decimal('1'), rounding=ROUND_DOWN) * tick_size)
        
        logger.debug(f"매도 가격 계산: 매수가={buy_price:,}원, 수익률={profit_rate*100:.1f}% → {adjusted_price:,}원")
        return adjusted_price
    
    def place_market_buy_order(self, stock_code: str, stock_name: str) -> Optional[Dict]:
        """
        시장가 전액 매수 주문을 실행합니다.
        
        Args:
            stock_code: 종목코드
            stock_name: 종목명
            
        Returns:
            Optional[Dict]: 주문 결과 (실패 시 None)
                - order_number: 주문번호
                - stock_code: 종목코드
                - stock_name: 종목명
                - quantity: 주문수량
                - order_time: 주문시각
        """
        try:
            logger.info(f"🔵 시장가 매수 주문 시작: {stock_name}({stock_code})")
            
            # 1. 예수금 조회
            balance = self.kiwoom.get_balance()
            if not balance:
                logger.error("예수금 조회 실패")
                return None
            
            available_amount = balance['available_amount']
            
            # 최소 예수금 체크 (1만원)
            if available_amount < Decimal('10000'):
                logger.error(f"매수 가능 금액 부족: {available_amount:,}원 (최소 10,000원 필요)")
                return None
            
            logger.info(f"매수 가능 금액: {available_amount:,}원")
            
            # 2. 현재가 조회
            price_info = self.kiwoom.get_current_price(stock_code)
            if not price_info:
                logger.error("현재가 조회 실패")
                return None
            
            current_price = price_info['current_price']
            logger.info(f"현재가: {current_price:,}원")
            
            # 3. 매수 수량 계산
            quantity = self._calculate_buy_quantity(available_amount, current_price)
            
            if quantity <= 0:
                logger.error("매수 가능 수량이 0입니다")
                return None
            
            logger.info(f"매수 수량: {quantity}주")
            
            # 4. 시장가 매수 주문 실행
            logger.warning(f"⚠️ 실제 매수 주문 실행 중... {stock_name}({stock_code}) {quantity}주")
            order_result = self.kiwoom.place_order(
                stock_code=stock_code,
                order_type='buy_market',
                quantity=quantity
            )
            
            if not order_result:
                logger.error("매수 주문 실패")
                return None
            
            logger.info(f"✅ 매수 주문 성공 - 주문번호: {order_result['order_number']}")
            
            return {
                'order_number': order_result['order_number'],
                'stock_code': stock_code,
                'stock_name': stock_name,
                'quantity': quantity,
                'order_time': order_result['order_time']
            }
            
        except Exception as e:
            logger.error(f"매수 주문 중 오류 발생: {e}")
            return None
    
    def place_limit_sell_order(self, stock_code: str, stock_name: str, quantity: int, 
                               buy_price: Decimal, profit_rate: Decimal) -> Optional[Dict]:
        """
        지정가 매도 주문을 실행합니다.
        
        Args:
            stock_code: 종목코드
            stock_name: 종목명
            quantity: 매도 수량
            buy_price: 매수 가격
            profit_rate: 목표 수익률 (예: 0.03 = 3%)
            
        Returns:
            Optional[Dict]: 주문 결과 (실패 시 None)
                - order_number: 주문번호
                - stock_code: 종목코드
                - stock_name: 종목명
                - quantity: 주문수량
                - sell_price: 매도가격
                - order_time: 주문시각
        """
        try:
            logger.info(f"🔴 지정가 매도 주문 시작: {stock_name}({stock_code})")
            
            # 매도 가격 계산
            sell_price = self._calculate_sell_price(buy_price, profit_rate)
            logger.info(f"매도 가격: {sell_price:,}원 (수익률: {profit_rate*100:.1f}%)")
            
            # 지정가 매도 주문 실행
            logger.warning(f"⚠️ 실제 매도 주문 실행 중... {stock_name}({stock_code}) {quantity}주 @ {sell_price:,}원")
            order_result = self.kiwoom.place_order(
                stock_code=stock_code,
                order_type='sell_limit',
                quantity=quantity,
                price=Decimal(str(sell_price))
            )
            
            if not order_result:
                logger.error("매도 주문 실패")
                return None
            
            logger.info(f"✅ 매도 주문 성공 - 주문번호: {order_result['order_number']}")
            
            return {
                'order_number': order_result['order_number'],
                'stock_code': stock_code,
                'stock_name': stock_name,
                'quantity': quantity,
                'sell_price': Decimal(str(sell_price)),
                'order_time': order_result['order_time']
            }
            
        except Exception as e:
            logger.error(f"매도 주문 중 오류 발생: {e}")
            return None
    
    def place_market_sell_order(self, stock_code: str, stock_name: str, quantity: int) -> Optional[Dict]:
        """
        시장가 매도 주문을 실행합니다.
        
        Args:
            stock_code: 종목코드
            stock_name: 종목명
            quantity: 매도 수량
            
        Returns:
            Optional[Dict]: 주문 결과 (실패 시 None)
        """
        try:
            logger.info(f"🔴 시장가 매도 주문 시작: {stock_name}({stock_code})")
            
            # 시장가 매도 주문 실행
            logger.warning(f"⚠️ 실제 시장가 매도 주문 실행 중... {stock_name}({stock_code}) {quantity}주")
            order_result = self.kiwoom.place_order(
                stock_code=stock_code,
                order_type='sell_market',
                quantity=quantity
            )
            
            if not order_result:
                logger.error("시장가 매도 주문 실패")
                return None
            
            logger.info(f"✅ 시장가 매도 주문 성공 - 주문번호: {order_result['order_number']}")
            
            return {
                'order_number': order_result['order_number'],
                'stock_code': stock_code,
                'stock_name': stock_name,
                'quantity': quantity,
                'order_time': order_result['order_time']
            }
            
        except Exception as e:
            logger.error(f"시장가 매도 주문 중 오류 발생: {e}")
            return None
    
    def check_order_execution(self, order_number: str, stock_code: str, max_retries: int = 3) -> Optional[Dict]:
        """
        주문 체결 여부를 확인합니다.
        키움증권 REST API: TR ka10076 (체결요청)
        
        Args:
            order_number: 주문번호
            stock_code: 종목코드
            max_retries: 최대 재시도 횟수
            
        Returns:
            Optional[Dict]: 체결 정보 (미체결 또는 실패 시 None)
                - executed: 체결 여부 (bool)
                - executed_quantity: 체결 수량
                - executed_price: 체결 가격 (Decimal)
                - executed_amount: 체결 금액 (Decimal)
        """
        try:
            logger.info(f"체결 확인 중: 주문번호 {order_number}, 종목 {stock_code}")
            
            for attempt in range(max_retries):
                # 체결 내역 조회 (TR: ka10076)
                orders = self.kiwoom.get_order_status(stock_code=stock_code, order_number=order_number)
                
                if not orders or len(orders) == 0:
                    logger.warning(f"주문 내역을 찾을 수 없음 (시도 {attempt+1}/{max_retries})")
                    time.sleep(1)
                    continue
                
                order = orders[0]
                
                # 체결 확인
                executed_quantity = order['executed_quantity']
                order_quantity = order['order_quantity']
                
                if executed_quantity > 0:
                    executed_price = order['executed_price']
                    executed_amount = executed_price * Decimal(str(executed_quantity))
                    
                    if executed_quantity == order_quantity:
                        logger.info(f"✅ 전량 체결 완료: {executed_quantity}주 @ {executed_price:,}원")
                        return {
                            'executed': True,
                            'executed_quantity': executed_quantity,
                            'executed_price': executed_price,
                            'executed_amount': executed_amount
                        }
                    else:
                        logger.info(f"⚠️ 부분 체결: {executed_quantity}/{order_quantity}주")
                        return {
                            'executed': False,
                            'executed_quantity': executed_quantity,
                            'executed_price': executed_price,
                            'executed_amount': executed_amount
                        }
                else:
                    logger.debug(f"미체결 (시도 {attempt+1}/{max_retries})")
                    time.sleep(2)
            
            logger.warning("주문이 아직 체결되지 않았습니다")
            return None
            
        except Exception as e:
            logger.error(f"체결 확인 중 오류 발생: {e}")
            return None
    
    def has_pending_orders(self, stock_code: str) -> bool:
        """
        특정 종목의 미체결 주문이 있는지 확인합니다.
        키움증권 REST API: TR ka10075 (미체결요청)
        
        Args:
            stock_code: 종목코드
            
        Returns:
            bool: 미체결 주문 존재 여부
        """
        try:
            # 키움증권 클라이언트의 has_pending_orders() 직접 사용
            return self.kiwoom.has_pending_orders(stock_code)
            
        except Exception as e:
            logger.error(f"미체결 주문 확인 중 오류 발생: {e}")
            return False

