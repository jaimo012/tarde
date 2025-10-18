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

    # 로깅 설정 (한국 시간대 적용)
    LOGGING_CONFIG = {
        'level': os.getenv('LOG_LEVEL', 'INFO'),
        'format': '{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}',
        'file_path': 'logs/dart_scraper.log',
        'rotation': '1 day',
        'retention': '30 days',
        'serialize': True,
        'timezone': 'Asia/Seoul'  # 한국 시간대 설정
    }

    # 필수 데이터 필드 정의 (이 필드들이 모두 채워져야 '계약' 시트에 저장됨)
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
