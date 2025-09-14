"""
DART API 및 구글 스프레드시트 연동을 위한 설정 파일

이 파일에는 API 키, 스프레드시트 URL 등 중요한 설정값들이 포함되어 있습니다.
실제 운영 시에는 환경변수나 별도의 설정 파일을 통해 관리하는 것을 권장합니다.
"""

import os
from dotenv import load_dotenv

# 환경변수 로드
load_dotenv()

# 환경 감지 및 설정 분기
ENVIRONMENT = os.getenv('ENVIRONMENT', 'development')
IS_CLOUDTYPE = ENVIRONMENT == 'production'

if IS_CLOUDTYPE:
    # 클라우드타입 환경에서는 cloudtype_settings 사용
    try:
        from config.cloudtype_settings import *
        print("✅ 클라우드타입 설정을 사용합니다.")
    except ImportError as e:
        print(f"⚠️ 클라우드타입 설정을 불러올 수 없어 기본 설정을 사용합니다: {e}")
        IS_CLOUDTYPE = False

if not IS_CLOUDTYPE:
    # 로컬 개발 환경 설정
    # DART API 설정
    DART_API_KEY = os.getenv('DART_API_KEY')
    if not DART_API_KEY:
        raise ValueError("DART_API_KEY 환경변수가 설정되지 않았습니다.")

    # 구글 스프레드시트 설정
    SPREADSHEET_URL = os.getenv('SPREADSHEET_URL')
    if not SPREADSHEET_URL:
        raise ValueError("SPREADSHEET_URL 환경변수가 설정되지 않았습니다.")
    
    SERVICE_ACCOUNT_FILE = os.getenv('SERVICE_ACCOUNT_FILE')
    if not SERVICE_ACCOUNT_FILE:
        raise ValueError("SERVICE_ACCOUNT_FILE 환경변수가 설정되지 않았습니다.")

    # 슬랙 웹훅 설정 (선택사항)
    SLACK_WEBHOOK_URL = os.getenv('SLACK_WEBHOOK')
    
    # KIS API 설정 (주식 분석용, 선택사항)
    KIS_APP_KEY = os.getenv('KIS_APP_KEY')
    KIS_APP_SECRET = os.getenv('KIS_APP_SECRET')

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
        'request_delay': 0.1  # API 요청 간 대기시간 (초)
    }

    # 로깅 설정
    LOGGING_CONFIG = {
        'level': os.getenv('LOG_LEVEL', 'INFO'),
        'format': '{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}',
        'file_path': 'logs/dart_scraper.log',
        'rotation': '1 day',
        'retention': '30 days'
    }

    # 필수 데이터 필드 정의 (이 필드들이 모두 채워져야 '계약' 시트에 저장됨)
    REQUIRED_FIELDS = ['계약(수주)일자', '시작일', '종료일', '계약금액']

    # 보고서 검색 키워드 설정
    REPORT_SEARCH_CONFIG = {
        'include_keywords': ['단일판매'],
        'exclude_keywords': ['정정', '해지', '정지']
    }
