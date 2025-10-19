"""
클라우드타입(CloudType) 배포를 위한 설정 파일

이 파일은 클라우드타입 환경에서 실행될 때 사용되는 설정들을 관리합니다.
환경변수를 통해 민감한 정보를 안전하게 관리합니다.
"""

import os
import json
import base64
from typing import Dict, Any

# 환경 확인
ENVIRONMENT = os.getenv('ENVIRONMENT', 'development')
IS_PRODUCTION = ENVIRONMENT == 'production'

# DART API 설정
DART_API_KEY = os.getenv('DART_API_KEY')
if not DART_API_KEY:
    raise ValueError("DART_API_KEY 환경변수가 설정되지 않았습니다.")

# 구글 서비스 계정 설정
def get_google_service_account_info() -> Dict[str, Any]:
    """
    환경변수에서 Base64로 인코딩된 구글 서비스 계정 JSON을 디코딩합니다.
    
    Returns:
        Dict[str, Any]: 서비스 계정 정보
        
    Raises:
        ValueError: 환경변수가 설정되지 않았거나 잘못된 형식인 경우
    """
    encoded_json = os.getenv('GOOGLE_SERVICE_ACCOUNT_JSON')
    if not encoded_json:
        raise ValueError("GOOGLE_SERVICE_ACCOUNT_JSON 환경변수가 설정되지 않았습니다.")
    
    try:
        # Base64 디코딩
        decoded_json = base64.b64decode(encoded_json).decode('utf-8')
        # JSON 파싱
        service_account_info = json.loads(decoded_json)
        return service_account_info
    except Exception as e:
        raise ValueError(f"구글 서비스 계정 JSON 디코딩 실패: {e}")

# 구글 스프레드시트 설정
SPREADSHEET_URL = os.getenv('SPREADSHEET_URL')
if not SPREADSHEET_URL:
    raise ValueError("SPREADSHEET_URL 환경변수가 설정되지 않았습니다.")

GOOGLE_SERVICE_ACCOUNT_INFO = get_google_service_account_info()

# 슬랙 웹훅 설정 (선택사항)
SLACK_WEBHOOK_URL = os.getenv('SLACK_WEBHOOK')

# 시트 이름 설정
SHEET_NAMES = {
    'CONTRACT': "계약",
    'EXCLUDED': "분석제외", 
    'COMPANY_LIST': "종목코드"
}

# 시트 컬럼 정의
SHEET_COLUMNS = [
    '종목코드', '조회코드', '종목명', '시장구분', '상장일자', '업종코드', '업종명', '결산월', '지정자문인',
    '상장주식수', '액면가', '자본금', '대표이사', '대표전화', '주소', '접수일자', '보고서명',
    '접수번호', '보고서링크', '계약(수주)일자', '계약상대방', '판매ㆍ공급계약 내용', '시작일',
    '종료일', '계약금액', '최근 매출액', '매출액 대비 비율'
]

# DART API 설정
DART_API_CONFIG = {
    'base_url': 'https://opendart.fss.or.kr/api',
    'list_endpoint': '/list.json',
    'document_endpoint': '/document.xml',
    'search_start_date': '20200101',
    'page_size': 100,
    'request_delay': 0.2 if IS_PRODUCTION else 0.1  # 프로덕션에서는 더 안전한 간격
}

# 로깅 설정 (한국 시간대 적용)
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
LOGGING_CONFIG = {
    'level': LOG_LEVEL,
    'format': '{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}',
    'file_path': '/tmp/dart_scraper.log' if IS_PRODUCTION else 'logs/dart_scraper.log',
    'rotation': '1 day',
    'retention': '7 days' if IS_PRODUCTION else '30 days',  # 프로덕션에서는 짧게
    'serialize': True,
    'timezone': 'Asia/Seoul'  # 한국 시간대 설정
}

# 클라우드타입 전용 설정
CLOUDTYPE_CONFIG = {
    'port': int(os.getenv('PORT', 8080)),
    'host': '0.0.0.0',
    'max_memory_usage': '512MB',  # 메모리 사용량 제한
    'timeout': 300,  # 5분 타임아웃
    'max_concurrent_requests': 5  # 동시 요청 제한
}

# 필수 데이터 필드 정의
REQUIRED_FIELDS = ['계약(수주)일자', '시작일', '종료일', '계약금액']

# 보고서 검색 키워드 설정
REPORT_SEARCH_CONFIG = {
    'include_keywords': ['단일판매'],
    'exclude_keywords': ['정정', '해지', '정지']
}

# 주목 업종 코드 매핑 (IT, 바이오, 제조 등 성장 산업)
TARGET_INDUSTRIES = {
    '32102': '의약품 제조업',
    '32902': '특수 목적용 기계 제조업',
    '32702': '측정, 시험, 항해, 제어 및 기타 정밀기기 제조업; 광학기기 제외',
    '32101': '기초 의약물질 제조업',
    '32901': '일반 목적용 기계 제조업',
    '32602': '전자부품 제조업',
    '32603': '컴퓨터 및 주변장치 제조업',
    '32701': '의료용 기기 제조업',
    '106201': '컴퓨터 프로그래밍, 시스템 통합 및 관리업',
    '105802': '소프트웨어 개발 및 공급업',
    '32802': '일차전지 및 이차전지 제조업',
    '32601': '반도체 제조업',
    '32801': '전동기, 발전기 및 전기 변환 · 공급 · 제어 장치 제조업',
    '32804': '전구 및 조명장치 제조업',
    '32809': '기타 전기장비 제조업',
    '32604': '통신 및 방송 장비 제조업',
    '32103': '의료용품 및 기타 의약 관련제품 제조업',
    '32805': '가정용 기기 제조업',
    '33109': '그외 기타 운송장비 제조업',
    '106301': '자료처리, 호스팅, 포털 및 기타 인터넷 정보매개 서비스업',
    '32803': '절연선 및 케이블 제조업',
    '32703': '사진장비 및 광학기기 제조업',
    '33003': '자동차 신품 부품 제조업',
    '106309': '기타 정보 서비스업',
    '33101': '선박 및 보트 건조업',
    '33102': '철도장비 제조업',
    '33001': '자동차용 엔진 및 자동차 제조업',
    '32606': '마그네틱 및 광학 매체 제조업',
    '32605': '영상 및 음향기기 제조업',
}

# 키움증권 API 설정
KIWOOM_APP_KEY = os.getenv('KIWOOM_APP_KEY')
KIWOOM_APP_SECRET = os.getenv('KIWOOM_APP_SECRET')
KIWOOM_ACCOUNT_NUMBER = os.getenv('KIWOOM_ACCOUNT_NUMBER')

# 거래 모드 설정
TRADING_MODE = os.getenv('TRADING_MODE', 'LIVE')  # LIVE or DRY_RUN

# 거래 설정 (Decimal 타입 사용)
from decimal import Decimal

TRADING_CONFIG = {
    'profit_target': Decimal('0.03'),       # 3% 익절 목표
    'stop_loss_5days': Decimal('-0.01'),    # -1% 손절 (5일 경과 시)
    'hold_period_soft': 5,                   # 5일 경과 시 조건부 매도
    'hold_period_hard': 10,                  # 10일 경과 시 무조건 매도
    'min_score': 8,                          # 최소 투자 점수
    'commission_rate': Decimal('0.00018'),   # 수수료 0.018%
    'monitoring_interval': 300,              # 공시 모니터링 주기 (5분)
    'position_check_interval': 600,          # 포지션 체크 주기 (10분)
    'min_balance': Decimal('10000'),         # 최소 예수금 (1만원)
}

# 에러 처리 설정
ERROR_HANDLING_CONFIG = {
    'max_retries': 3,
    'retry_delay': 1.0,
    'circuit_breaker_threshold': 5,  # 연속 실패 5회 시 중단
    'health_check_interval': 60  # 1분마다 헬스체크
}

# 성능 최적화 설정
PERFORMANCE_CONFIG = {
    'batch_size': 10,  # 배치 처리 크기
    'memory_limit_mb': 400,  # 메모리 사용량 제한 (MB)
    'gc_threshold': 100,  # 가비지 컬렉션 임계값
    'connection_pool_size': 10  # 연결 풀 크기
}

def validate_environment():
    """
    환경 설정이 올바른지 검증합니다.
    
    Raises:
        ValueError: 필수 환경변수가 누락된 경우
    """
    required_vars = [
        'DART_API_KEY',
        'GOOGLE_SERVICE_ACCOUNT_JSON'
    ]
    
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        raise ValueError(f"다음 환경변수들이 설정되지 않았습니다: {', '.join(missing_vars)}")
    
    # 구글 서비스 계정 정보 유효성 검사
    try:
        service_account_info = get_google_service_account_info()
        required_keys = ['type', 'project_id', 'private_key_id', 'private_key', 'client_email']
        missing_keys = [key for key in required_keys if key not in service_account_info]
        
        if missing_keys:
            raise ValueError(f"구글 서비스 계정 JSON에 다음 키들이 누락되었습니다: {', '.join(missing_keys)}")
            
    except Exception as e:
        raise ValueError(f"구글 서비스 계정 설정 검증 실패: {e}")

# 환경 설정 검증 실행
if __name__ != '__main__':
    validate_environment()
