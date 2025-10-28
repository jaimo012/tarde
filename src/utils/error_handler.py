"""
통합 오류 처리 모듈

이 모듈은 시스템 전체에서 발생하는 오류를 일관되게 처리하고
로깅, 시트 기록, 슬랙 알림을 자동으로 수행합니다.
"""

import traceback
import uuid
import inspect
from typing import Optional, Dict, Any
from datetime import datetime
from loguru import logger


class ErrorHandler:
    """통합 오류 처리 클래스"""
    
    def __init__(self, sheets_client=None, slack_notifier=None):
        """
        오류 처리기를 초기화합니다.
        
        Args:
            sheets_client: 구글 시트 클라이언트 (선택)
            slack_notifier: 슬랙 알림 클라이언트 (선택)
        """
        self.sheets_client = sheets_client
        self.slack_notifier = slack_notifier
        logger.info("통합 오류 처리기 초기화 완료")
    
    def handle_error(
        self,
        error: Exception,
        module: str,
        operation: str,
        severity: str = 'ERROR',
        related_stock: str = '해당없음',
        trading_status: str = '알 수 없음',
        position_info: str = '없음',
        additional_context: Optional[Dict[str, Any]] = None,
        send_slack: bool = True,
        log_to_sheet: bool = True,
        auto_recovery_attempted: bool = False,
        correlation_id: Optional[str] = None,
        function_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        오류를 처리하고 로깅, 시트 기록, 슬랙 알림을 수행합니다.
        
        Args:
            error: 발생한 예외
            module: 오류 발생 모듈명
            operation: 수행 중이던 작업
            severity: 심각도 (CRITICAL/ERROR/WARNING)
            related_stock: 관련 종목 (선택)
            trading_status: 자동매매 상태 (선택)
            position_info: 보유 종목 정보 (선택)
            additional_context: 추가 컨텍스트 정보 (선택)
            send_slack: 슬랙 알림 전송 여부
            log_to_sheet: 시트 기록 여부
            
        Returns:
            Dict[str, Any]: 오류 처리 결과 정보
        """
        try:
            # 기본 정보 추출
            error_type = type(error).__name__
            error_message = str(error)
            stack_trace = traceback.format_exc()
            
            # correlation_id 생성 (없으면)
            if not correlation_id:
                correlation_id = str(uuid.uuid4())[:8]
            
            # 함수명 자동 감지 (없으면)
            if not function_name:
                try:
                    frame = inspect.currentframe().f_back.f_back
                    function_name = frame.f_code.co_name if frame else 'unknown'
                except:
                    function_name = 'unknown'
            
            # 환경 정보
            try:
                from config.settings import ENVIRONMENT
                environment = ENVIRONMENT
            except:
                environment = 'unknown'
            
            # 1. 구조화된 로거 기록
            logger.error(f"🚨 [{severity}] {module}.{function_name} - {operation}")
            logger.error(f"📋 상관ID: {correlation_id}")
            logger.error(f"🔍 오류 유형: {error_type}")
            logger.error(f"📝 오류 메시지: {error_message}")
            if auto_recovery_attempted:
                logger.info(f"🔄 자동 복구 시도함")
            logger.debug(f"📍 스택 트레이스:\n{stack_trace}")
            
            # 2. 시트에 기록
            sheet_success = False
            if log_to_sheet and self.sheets_client:
                try:
                    error_log = {
                        'timestamp': datetime.now(),
                        'severity': severity,
                        'module': f"{module}.{function_name}",
                        'error_type': error_type,
                        'error_message': error_message[:200],  # 200자 제한
                        'related_stock': related_stock,
                        'trading_status': trading_status,
                        'position_info': position_info,
                        'resolution_status': '자동복구시도' if auto_recovery_attempted else '미해결',
                        'details': (f"작업: {operation}\n상관ID: {correlation_id}\n"
                                  f"환경: {environment}\n{stack_trace[-500:] if len(stack_trace) > 500 else stack_trace}")
                    }
                    
                    sheet_success = self.sheets_client.log_error_to_sheet(error_log)
                    if sheet_success:
                        logger.info("✅ 오류 로그 시트 기록 완료")
                    else:
                        logger.error("❌ 오류 로그 시트 기록 실패")
                except Exception as sheet_error:
                    logger.error(f"❌ 오류 로그 시트 기록 중 예외: {sheet_error}")
            
            # 3. 슬랙 알림 전송
            slack_success = False
            if send_slack and self.slack_notifier and severity in ['CRITICAL', 'ERROR']:
                try:
                    stack_trace_short = stack_trace[-1000:] if len(stack_trace) > 1000 else stack_trace
                    
                    error_details = {
                        "⚠️ 심각도": severity,
                        "🆔 상관ID": correlation_id,
                        "📍 발생 위치": f"{module}.{function_name}",
                        "🔧 작업": operation,
                        "🔍 오류 유형": error_type,
                        "📝 오류 메시지": error_message[:400],
                        "🎯 관련 종목": related_stock,
                        "🤖 자동매매 상태": trading_status,
                        "📊 포지션 정보": position_info,
                        "🔄 자동복구": "시도함" if auto_recovery_attempted else "미시도",
                        "🌍 환경": environment
                    }
                    
                    # 추가 컨텍스트 정보 포함 (필드 수 제한)
                    if additional_context:
                        context_count = 0
                        for key, value in additional_context.items():
                            if context_count >= 5:  # 최대 5개 추가 필드
                                break
                            sanitized_value = str(value)[:80] if value else 'None'
                            error_details[f"📋 {key}"] = sanitized_value
                            context_count += 1
                    
                    self.slack_notifier.send_critical_error(
                        error_title=f"🚨 [{severity}] {operation} 오류",
                        error_details=error_details,
                        stack_trace=stack_trace_short
                    )
                    slack_success = True
                    logger.info("✅ 슬랙 오류 알림 전송 완료")
                except Exception as slack_error:
                    logger.error(f"❌ 슬랙 알림 전송 중 예외: {slack_error}")
            
            # 4. 결과 반환
            return {
                'success': True,
                'correlation_id': correlation_id,
                'error_type': error_type,
                'severity': severity,
                'sheet_logged': sheet_success,
                'slack_sent': slack_success,
                'auto_recovery_attempted': auto_recovery_attempted
            }
            
        except Exception as handler_error:
            # 오류 처리기 자체에서 오류가 발생한 경우
            logger.critical(f"💥 ErrorHandler 자체 오류: {handler_error}")
            logger.critical(f"원본 오류: {error}")
            return {
                'success': False,
                'error': str(handler_error),
                'original_error': str(error)
            }
    
    def log_operation(
        self,
        module: str,
        operation: str,
        status: str,
        details: Optional[str] = None,
        level: str = 'INFO'
    ):
        """
        작업 진행 상황을 로깅합니다.
        
        Args:
            module: 모듈명
            operation: 작업명
            status: 상태 (시작/진행중/완료/실패)
            details: 상세 정보 (선택)
            level: 로그 레벨 (INFO/DEBUG/WARNING)
        """
        emoji_map = {
            '시작': '🚀',
            '진행중': '⚙️',
            '완료': '✅',
            '실패': '❌',
            '경고': '⚠️',
            '성공': '✅'
        }
        
        emoji = emoji_map.get(status, '📌')
        log_message = f"{emoji} [{module}] {operation} - {status}"
        
        if details:
            log_message += f"\n  └─ {details}"
        
        if level == 'INFO':
            logger.info(log_message)
        elif level == 'DEBUG':
            logger.debug(log_message)
        elif level == 'WARNING':
            logger.warning(log_message)
        else:
            logger.info(log_message)
    
    def log_api_call(
        self,
        api_name: str,
        endpoint: str,
        method: str = 'GET',
        params: Optional[Dict] = None,
        status: str = '시작',
        response_code: Optional[int] = None,
        error: Optional[str] = None
    ):
        """
        API 호출 내역을 로깅합니다.
        
        Args:
            api_name: API 이름 (예: DART API, 키움증권 API)
            endpoint: 엔드포인트
            method: HTTP 메서드
            params: 요청 파라미터 (민감정보 제외)
            status: 상태 (시작/성공/실패)
            response_code: HTTP 응답 코드
            error: 오류 메시지
        """
        if status == '시작':
            logger.info(f"🌐 API 호출 시작: {api_name}")
            logger.debug(f"  ├─ 엔드포인트: {method} {endpoint}")
            if params:
                # 민감정보 마스킹
                safe_params = self._mask_sensitive_params(params)
                logger.debug(f"  └─ 파라미터: {safe_params}")
        
        elif status == '성공':
            logger.info(f"✅ API 호출 성공: {api_name}")
            if response_code:
                logger.debug(f"  └─ 응답 코드: {response_code}")
        
        elif status == '실패':
            logger.error(f"❌ API 호출 실패: {api_name}")
            if response_code:
                logger.error(f"  ├─ 응답 코드: {response_code}")
            if error:
                logger.error(f"  └─ 오류: {error}")
    
    def _mask_sensitive_params(self, params: Dict) -> Dict:
        """파라미터에서 민감정보를 마스킹합니다."""
        sensitive_keys = ['api_key', 'crtfc_key', 'appkey', 'secretkey', 'token', 'password']
        masked_params = {}
        
        for key, value in params.items():
            if any(sensitive in key.lower() for sensitive in sensitive_keys):
                if isinstance(value, str) and len(value) > 4:
                    masked_params[key] = value[:2] + '*' * (len(value) - 4) + value[-2:]
                else:
                    masked_params[key] = '****'
            else:
                masked_params[key] = value
        
        return masked_params
    
    def log_data_operation(
        self,
        operation_type: str,
        target: str,
        record_count: int,
        status: str = '완료',
        details: Optional[str] = None
    ):
        """
        데이터 작업 내역을 로깅합니다.
        
        Args:
            operation_type: 작업 유형 (읽기/쓰기/삭제/업데이트)
            target: 대상 (시트명, 테이블명 등)
            record_count: 처리한 레코드 수
            status: 상태
            details: 상세 정보
        """
        emoji_map = {
            '읽기': '📖',
            '쓰기': '✍️',
            '삭제': '🗑️',
            '업데이트': '🔄'
        }
        
        emoji = emoji_map.get(operation_type, '📊')
        log_message = f"{emoji} 데이터 {operation_type}: {target} ({record_count}건)"
        
        if status != '완료':
            log_message += f" - {status}"
        
        if details:
            log_message += f"\n  └─ {details}"
        
        logger.info(log_message)
    
    def log_trading_operation(
        self,
        operation: str,
        stock_code: str,
        stock_name: str,
        quantity: Optional[int] = None,
        price: Optional[float] = None,
        status: str = '시작',
        order_number: Optional[str] = None,
        error: Optional[str] = None
    ):
        """
        거래 작업 내역을 로깅합니다.
        
        Args:
            operation: 작업 (매수/매도)
            stock_code: 종목코드
            stock_name: 종목명
            quantity: 수량
            price: 가격
            status: 상태
            order_number: 주문번호
            error: 오류 메시지
        """
        emoji_map = {
            '매수': '🔵',
            '매도': '🔴'
        }
        
        emoji = emoji_map.get(operation, '💼')
        
        if status == '시작':
            log_message = f"{emoji} {operation} 주문 시작: {stock_name}({stock_code})"
            if quantity:
                log_message += f"\n  ├─ 수량: {quantity:,}주"
            if price:
                log_message += f"\n  └─ 가격: {price:,}원"
            logger.info(log_message)
        
        elif status == '완료':
            log_message = f"✅ {operation} 주문 체결: {stock_name}({stock_code})"
            if quantity:
                log_message += f"\n  ├─ 수량: {quantity:,}주"
            if price:
                log_message += f"\n  ├─ 가격: {price:,}원"
            if order_number:
                log_message += f"\n  └─ 주문번호: {order_number}"
            logger.info(log_message)
        
        elif status == '실패':
            log_message = f"❌ {operation} 주문 실패: {stock_name}({stock_code})"
            if error:
                log_message += f"\n  └─ 오류: {error}"
            logger.error(log_message)

    def _get_recommended_action(self, error_type: str, severity: str) -> str:
        """오류 유형과 심각도에 따른 권장 조치를 반환합니다."""
        action_map = {
            'ConnectionError': '네트워크 연결 확인 후 재시도',
            'TimeoutError': 'API 응답 시간 초과, 잠시 후 재시도',
            'AuthenticationError': 'API 키 및 인증 정보 확인',
            'KeyError': '데이터 스키마 확인 및 필드명 검증',
            'ValueError': '입력값 형식 및 범위 확인',
            'FileNotFoundError': '파일 경로 및 권한 확인',
            'PermissionError': '파일/디렉터리 권한 확인',
            'ImportError': '라이브러리 설치 확인 (pip install)',
            'AttributeError': '객체 속성 및 메서드 존재 여부 확인',
            'IndexError': '배열/리스트 인덱스 범위 확인',
            'TypeError': '데이터 타입 및 함수 시그니처 확인'
        }
        
        if severity == 'CRITICAL':
            return f"{action_map.get(error_type, '시스템 관리자에게 즉시 문의')} (긴급)"
        else:
            return action_map.get(error_type, '로그 분석 후 적절한 조치 수행')

    def _sanitize_context(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """민감정보를 마스킹하고 컨텍스트 데이터를 정제합니다."""
        sanitized = {}
        sensitive_keys = {'password', 'key', 'token', 'secret', 'auth', 'credential'}
        
        for key, value in context.items():
            if any(sensitive in key.lower() for sensitive in sensitive_keys):
                # 민감정보 마스킹
                if isinstance(value, str) and len(value) > 4:
                    sanitized[key] = value[:2] + '*' * (len(value) - 4) + value[-2:]
                else:
                    sanitized[key] = '***'
            else:
                # 일반 정보는 길이 제한
                sanitized[key] = str(value)[:200] if value else 'None'
        
        return sanitized

    def _sanitize_for_display(self, value: str, max_length: int = 100) -> str:
        """디스플레이용 텍스트를 정제합니다."""
        if not value:
            return 'None'
        
        # 민감정보 패턴 마스킹
        import re
        
        # 이메일 마스킹
        value = re.sub(r'(\w+)@(\w+)', r'\1***@\2', value)
        
        # 전화번호 마스킹
        value = re.sub(r'(\d{3})-?(\d{4})-?(\d{4})', r'\1-***-\3', value)
        
        # 길이 제한
        if len(value) > max_length:
            return value[:max_length-3] + '...'
        
        return value


# 전역 오류 처리기 인스턴스 (초기화는 main.py에서 수행)
_global_error_handler: Optional[ErrorHandler] = None


def initialize_error_handler(sheets_client=None, slack_notifier=None):
    """전역 오류 처리기를 초기화합니다."""
    global _global_error_handler
    _global_error_handler = ErrorHandler(sheets_client, slack_notifier)
    logger.info("✅ 전역 오류 처리기 초기화 완료")


def get_error_handler() -> Optional[ErrorHandler]:
    """전역 오류 처리기를 가져옵니다."""
    return _global_error_handler


def handle_error(*args, **kwargs) -> bool:
    """전역 오류 처리기를 통해 오류를 처리합니다."""
    if _global_error_handler:
        return _global_error_handler.handle_error(*args, **kwargs)
    else:
        logger.error("⚠️ 전역 오류 처리기가 초기화되지 않았습니다")
        return False


def log_operation(*args, **kwargs):
    """전역 오류 처리기를 통해 작업을 로깅합니다."""
    if _global_error_handler:
        _global_error_handler.log_operation(*args, **kwargs)
    else:
        logger.warning("⚠️ 전역 오류 처리기가 초기화되지 않았습니다")

