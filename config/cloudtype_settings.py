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

# 키움증권 API 설정 (주식 분석용, 선택사항)
KIWOOM_APP_KEY = os.getenv('KIWOOM_APP_KEY')
KIWOOM_APP_SECRET = os.getenv('KIWOOM_APP_SECRET')

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
