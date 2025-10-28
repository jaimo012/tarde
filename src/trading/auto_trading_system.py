"""
자동매매 시스템 통합 모듈

이 모듈은 공시 모니터링과 자동매매를 통합 관리합니다.
"""

import time
from typing import Optional
from datetime import datetime
from loguru import logger
from decimal import Decimal

from config.settings import (
    KIWOOM_APP_KEY,
    KIWOOM_APP_SECRET,
    KIWOOM_ACCOUNT_NUMBER,
    TRADING_MODE,
    TRADING_CONFIG
)

from src.trading.kiwoom_client import KiwoomAPIClient
from src.trading.order_manager import OrderManager
from src.trading.position_manager import PositionManager
from src.trading.trading_strategy import TradingStrategy
from src.google_sheets.client import GoogleSheetsClient
from src.utils.slack_notifier import SlackNotifier
from src.utils.stock_analyzer import StockAnalyzer


class AutoTradingSystem:
    """자동매매 시스템 메인 클래스"""
    
    def __init__(self, sheets_client: GoogleSheetsClient, slack_notifier: SlackNotifier):
        """
        자동매매 시스템을 초기화합니다.
        
        Args:
            sheets_client: 구글 시트 클라이언트
            slack_notifier: 슬랙 알림 클라이언트
        """
        self.sheets_client = sheets_client
        self.slack_notifier = slack_notifier
        self.stock_analyzer = StockAnalyzer()
        
        # 거래 모드 확인
        self.trading_enabled = TRADING_MODE == 'LIVE'
        if not self.trading_enabled:
            logger.warning("⚠️ 거래 모드가 비활성화되어 있습니다 (DRY_RUN 모드)")
            return
        
        # 키움증권 API 설정 확인
        if not all([KIWOOM_APP_KEY, KIWOOM_APP_SECRET, KIWOOM_ACCOUNT_NUMBER]):
            logger.warning("⚠️ 키움증권 API 설정이 누락되어 거래가 비활성화됩니다")
            self.trading_enabled = False
            return
        
        # 거래 시스템 초기화
        try:
            self.kiwoom_client = KiwoomAPIClient(
                app_key=KIWOOM_APP_KEY,
                app_secret=KIWOOM_APP_SECRET,
                account_number=KIWOOM_ACCOUNT_NUMBER
            )
            
            # 인증
            if not self.kiwoom_client.authenticate():
                logger.error("🚨 키움증권 API 인증 실패 - 자동매매가 비활성화됩니다!")
                self.trading_enabled = False
                
                # 긴급 슬랙 알림
                self.slack_notifier.send_critical_error(
                    error_title="🚨 키움증권 API 인증 실패",
                    error_details={
                        "⚠️ 오류 유형": "인증 실패",
                        "📝 오류 메시지": "키움증권 API 인증에 실패했습니다",
                        "📍 발생 위치": "자동매매 시스템 초기화",
                        "🤖 자동매매 상태": "비활성화됨",
                        "확인사항": "1. KIWOOM_APP_KEY 확인\n2. KIWOOM_APP_SECRET 확인\n3. KIWOOM_ACCOUNT_NUMBER 확인\n4. 서버 IP 화이트리스트 등록 확인\n5. 키움증권 서비스 승인 상태 확인"
                    },
                    stack_trace=None
                )
                
                # 오류 시트 기록
                try:
                    import traceback
                    self.sheets_client.log_error_to_sheet({
                        'timestamp': datetime.now(),
                        'severity': 'CRITICAL',
                        'module': '키움증권 API 인증',
                        'error_type': '인증 실패',
                        'error_message': '키움증권 API 인증에 실패하여 자동매매가 비활성화되었습니다',
                        'related_stock': '해당없음',
                        'trading_status': '비활성화됨',
                        'position_info': '확인 불가',
                        'resolution_status': '미해결',
                        'details': 'API KEY, SECRET, 계좌번호 확인 필요. 서버 IP 화이트리스트 등록 확인 필요.'
                    })
                except Exception as log_error:
                    logger.error(f"오류 로그 시트 기록 실패: {log_error}")
                
                return
            
            self.order_mgr = OrderManager(self.kiwoom_client)
            self.position_mgr = PositionManager(self.kiwoom_client)
            self.trading_strategy = TradingStrategy(
                self.kiwoom_client,
                self.order_mgr,
                self.position_mgr
            )
            
            logger.info("🚀 자동매매 시스템이 활성화되었습니다")
            
        except Exception as e:
            logger.error(f"🚨 자동매매 시스템 초기화 실패: {e}")
            self.trading_enabled = False
            
            # 긴급 슬랙 알림
            import traceback
            self.slack_notifier.send_critical_error(
                error_title="🚨 자동매매 시스템 초기화 실패",
                error_details={
                    "⚠️ 오류 유형": type(e).__name__,
                    "📝 오류 메시지": str(e),
                    "📍 발생 위치": "자동매매 시스템 초기화",
                    "🤖 자동매매 상태": "비활성화됨"
                },
                stack_trace=traceback.format_exc()
            )
            
            # 오류 시트 기록
            try:
                stack_trace_str = traceback.format_exc()
                self.sheets_client.log_error_to_sheet({
                    'timestamp': datetime.now(),
                    'severity': 'CRITICAL',
                    'module': '자동매매 시스템 초기화',
                    'error_type': type(e).__name__,
                    'error_message': str(e)[:200],
                    'related_stock': '해당없음',
                    'trading_status': '비활성화됨',
                    'position_info': '확인 불가',
                    'resolution_status': '미해결',
                    'details': stack_trace_str[-500:] if len(stack_trace_str) > 500 else stack_trace_str
                })
            except Exception as log_error:
                logger.error(f"오류 로그 시트 기록 실패: {log_error}")
    
    def process_new_contract(self, contract_data: dict) -> bool:
        """
        신규 계약 정보를 처리하고 매수 조건을 확인합니다.
        
        Args:
            contract_data: 계약 정보
            
        Returns:
            bool: 매수 실행 여부
        """
        if not self.trading_enabled:
            logger.debug("거래가 비활성화되어 있어 건너뜁니다")
            return False
        
        try:
            stock_code = contract_data.get('종목코드', '')
            stock_name = contract_data.get('종목명', '')
            
            logger.info(f"\n{'='*60}")
            logger.info(f"신규 계약 처리: {stock_name}({stock_code})")
            logger.info(f"{'='*60}")
            
            # 1. 주식 분석 수행
            logger.info("1단계: 주식 분석 수행...")
            analysis_result = self.stock_analyzer.analyze_stock_for_contract(contract_data)
            
            if not analysis_result:
                logger.warning("주식 분석 실패")
                return False
            
            logger.info(f"투자 점수: {analysis_result.recommendation_score}/10")
            
            # 2. 매수 조건 확인
            logger.info("2단계: 매수 조건 확인...")
            should_buy_result = self.trading_strategy.should_buy(contract_data, analysis_result)
            
            if not should_buy_result['should_buy']:
                logger.info(f"매수 조건 미충족: {should_buy_result['reason']}")
                return False
            
            # 3. 매수 시작 알림
            logger.info("3단계: 매수 시작 알림 전송...")
            self.slack_notifier.send_buy_start_notification(
                stock_name=stock_name,
                stock_code=stock_code,
                score=should_buy_result['score'],
                disclosure_info=contract_data
            )
            
            # 4. 매수 전략 실행
            logger.info("4단계: 매수 전략 실행...")
            buy_result = self.trading_strategy.execute_buy_strategy(stock_code, stock_name)
            
            # 오류 정보가 있는 경우 상세 처리
            if buy_result and 'error_info' in buy_result:
                error_info = buy_result['error_info']
                
                logger.error("❌ 매수 실행 실패")
                logger.error(f"   📍 실패 단계: {error_info['step']}")
                logger.error(f"   🔍 오류 유형: {error_info['error_type']}")
                logger.error(f"   📝 오류 메시지: {error_info['error_message']}")
                
                # 상세 슬랙 알림 전송
                error_details = {
                    "📊 대상 종목": f"{stock_name}({stock_code})",
                    "📍 실패 단계": error_info['step'],
                    "🔍 오류 유형": error_info['error_type'],
                    "📝 오류 메시지": error_info['error_message']
                }
                
                # 가능한 원인 추가
                if 'possible_causes' in error_info and error_info['possible_causes']:
                    causes_text = "\n".join([f"• {cause}" for cause in error_info['possible_causes']])
                    error_details["💡 가능한 원인"] = causes_text
                
                # 해결방법 추가
                if 'resolution' in error_info and error_info['resolution']:
                    error_details["🛠️ 해결방법"] = error_info['resolution']
                
                # 주문번호가 있는 경우 추가 (체결 확인 실패 시)
                if 'order_number' in error_info:
                    error_details["📋 주문번호"] = error_info['order_number']
                    error_details["🔍 확인사항"] = "키움증권 HTS에서 주문 상태를 직접 확인하세요"
                
                # 추가 컨텍스트 정보
                if 'available_amount' in error_info:
                    error_details["💰 매수 가능 금액"] = error_info['available_amount']
                if 'current_price' in error_info:
                    error_details["📈 현재가"] = error_info['current_price']
                
                self.slack_notifier.send_critical_error(
                    error_title=f"💥 매수 실행 실패: {stock_name}({stock_code})",
                    error_details=error_details,
                    stack_trace=error_info.get('stack_trace', None)
                )
                
                return False
            
            if not buy_result:
                logger.error("매수 실행 실패: 알 수 없는 오류")
                self.slack_notifier.send_system_notification(
                    f"❌ 매수 실행 실패: {stock_name}({stock_code}) (알 수 없는 오류)",
                    "error"
                )
                return False
            
            # 5. 거래내역 저장
            logger.info("5단계: 거래내역 저장...")
            save_success = self.sheets_client.save_buy_transaction(buy_result)
            
            if not save_success:
                logger.warning("거래내역 저장 실패 (주의: 거래는 실행되었음)")
            
            # 6. 매수 체결 알림
            logger.info("6단계: 매수 체결 알림 전송...")
            self.slack_notifier.send_buy_execution_notification(
                stock_name=stock_name,
                stock_code=stock_code,
                quantity=buy_result['quantity'],
                price=float(buy_result['executed_price']),
                amount=float(buy_result['executed_amount'])
            )
            
            logger.info(f"✅ 매수 처리 완료: {stock_name}({stock_code})")
            return True
            
        except Exception as e:
            logger.error(f"신규 계약 처리 중 오류 발생: {e}")
            
            # 상세 오류 정보 수집
            import traceback
            error_details = {
                "⚠️ 오류 유형": type(e).__name__,
                "📝 오류 메시지": str(e),
                "📍 발생 단계": "신규 계약 자동매매 처리",
                "📊 종목": f"{stock_name}({stock_code})",
            }
            
            # 현재 시스템 상태 추가
            try:
                balance = self.kiwoom_client.get_balance()
                if balance:
                    error_details["💰 현재 예수금"] = f"{balance['available_amount']:,}원"
            except:
                pass
            
            stack_trace = traceback.format_exc()
            
            # 슬랙 알림 전송
            self.slack_notifier.send_critical_error(
                error_title=f"매수 처리 실패: {stock_name}({stock_code})",
                error_details=error_details,
                stack_trace=stack_trace
            )
            
            # 구글 시트에 오류 로그 기록
            try:
                error_log = {
                    'timestamp': datetime.now(),
                    'severity': 'ERROR',
                    'module': '매수 처리',
                    'error_type': type(e).__name__,
                    'error_message': str(e)[:200],
                    'related_stock': f"{stock_name}({stock_code})",
                    'trading_status': '활성화',
                    'position_info': '매수 시도 중',
                    'resolution_status': '미해결',
                    'details': f"발생 단계: 신규 계약 자동매매 처리\n{stack_trace[-500:] if len(stack_trace) > 500 else stack_trace}"
                }
                self.sheets_client.log_error_to_sheet(error_log)
            except Exception as log_error:
                logger.error(f"오류 로그 시트 기록 실패: {log_error}")
            
            return False
    
    def manage_positions(self) -> bool:
        """
        보유 포지션을 관리하고 매도 전략을 실행합니다.
        
        Returns:
            bool: 처리 성공 여부
        """
        if not self.trading_enabled:
            logger.debug("거래가 비활성화되어 있어 건너뜁니다")
            return True
        
        try:
            logger.info("\n" + "="*60)
            logger.info("보유 포지션 관리 시작")
            logger.info("="*60)
            
            # 1. 현재 포지션 확인
            position = self.position_mgr.get_current_position()
            
            if not position:
                logger.info("보유 포지션 없음")
                return True
            
            stock_code = position['stock_code']
            stock_name = position['stock_name']
            
            # 2. 거래내역에서 매수일 조회
            trade_info = self.sheets_client.get_latest_buy_transaction(stock_code)
            
            if not trade_info:
                logger.warning(f"⚠️ 매수 거래 정보를 찾을 수 없습니다: {stock_name}")
                # 매수일을 알 수 없는 경우 오늘로 가정 (안전을 위해)
                buy_date = datetime.now()
            else:
                buy_date = trade_info['buy_date']
            
            # 3. 매도 주문 존재 여부 확인
            has_sell_order = self.order_mgr.has_pending_orders(stock_code)
            
            # 4. 매도 전략 실행
            sell_result = self.trading_strategy.execute_position_management(buy_date)
            
            if not sell_result:
                logger.debug("매도 조건 미충족 또는 매도 불필요")
                return True
            
            # 5. 매도 완료 처리
            if sell_result['action'] == 'sell_executed':
                # 거래내역 업데이트
                self.sheets_client.update_sell_transaction(
                    stock_code=stock_code,
                    sell_info={
                        'sell_time': datetime.now(),
                        'executed_price': sell_result['executed_price'],
                        'quantity': sell_result['quantity'],
                        'profit_rate': sell_result['profit_rate'],
                        'reason': sell_result['reason']
                    }
                )
                
                # 매도 체결 알림
                self.slack_notifier.send_sell_execution_notification(
                    stock_name=stock_name,
                    stock_code=stock_code,
                    quantity=sell_result['quantity'],
                    buy_price=float(position['avg_price']),
                    sell_price=float(sell_result['executed_price']),
                    profit_rate=float(sell_result['profit_rate']),
                    reason=sell_result['reason']
                )
                
                logger.info(f"✅ 매도 완료: {stock_name} (수익률: {sell_result['profit_rate']*100:.2f}%)")
                
            elif sell_result['action'] == 'order_placed':
                # 매도 주문 설정 알림
                target_price = sell_result.get('sell_price')
                self.slack_notifier.send_sell_order_notification(
                    stock_name=stock_name,
                    stock_code=stock_code,
                    sell_type='limit' if target_price else 'market',
                    target_price=float(target_price) if target_price else None,
                    reason=sell_result['reason']
                )
                
                logger.info(f"✅ 매도 주문 설정 완료: {stock_name}")
            
            return True
            
        except Exception as e:
            logger.error(f"포지션 관리 중 오류 발생: {e}")
            
            # 상세 오류 정보 수집
            import traceback
            error_details = {
                "⚠️ 오류 유형": type(e).__name__,
                "📝 오류 메시지": str(e),
                "📍 발생 단계": "보유 포지션 관리",
            }
            
            position_info_text = "조회 실패"
            related_stock = "해당없음"
            
            # 현재 포지션 정보 추가 시도
            try:
                position = self.position_mgr.get_current_position()
                if position:
                    error_details["📊 문제 종목"] = f"{position['stock_name']}({position['stock_code']})"
                    error_details["📈 현재가"] = f"{position['current_price']:,}원"
                    error_details["💼 보유수량"] = f"{position['quantity']}주"
                    error_details["📊 수익률"] = f"{position['profit_rate']:.2f}%"
                    
                    position_info_text = f"{position['stock_name']}({position['stock_code']}) {position['quantity']}주"
                    related_stock = f"{position['stock_name']}({position['stock_code']})"
            except:
                pass
            
            stack_trace = traceback.format_exc()
            
            # 슬랙 알림 전송
            self.slack_notifier.send_critical_error(
                error_title="포지션 관리 중 오류 발생",
                error_details=error_details,
                stack_trace=stack_trace
            )
            
            # 구글 시트에 오류 로그 기록
            try:
                error_log = {
                    'timestamp': datetime.now(),
                    'severity': 'ERROR',
                    'module': '포지션 관리',
                    'error_type': type(e).__name__,
                    'error_message': str(e)[:200],
                    'related_stock': related_stock,
                    'trading_status': '활성화',
                    'position_info': position_info_text,
                    'resolution_status': '미해결',
                    'details': f"발생 단계: 보유 포지션 관리\n{stack_trace[-500:] if len(stack_trace) > 500 else stack_trace}"
                }
                self.sheets_client.log_error_to_sheet(error_log)
            except Exception as log_error:
                logger.error(f"오류 로그 시트 기록 실패: {log_error}")
            
            return False

