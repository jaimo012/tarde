#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SNT에너지(100840) 주가 차트 생성 및 슬랙 전송 테스트

이 스크립트는 기존의 stock_analyzer.py의 함수들을 사용하여
SNT에너지의 차트를 생성하고 슬랙으로 전송합니다.
"""

import sys
import os
import io

# Windows 콘솔 인코딩 문제 해결
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# 프로젝트 루트 디렉토리를 Python 경로에 추가
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# 환경변수 로드 (.env 파일이 있으면 로드)
from dotenv import load_dotenv
load_dotenv(os.path.join(project_root, '.env'))

from src.utils.stock_analyzer import StockAnalyzer
from src.utils.slack_notifier import SlackNotifier
import logging

# 환경변수 직접 가져오기
SLACK_WEBHOOK_URL = os.getenv('SLACK_WEBHOOK')
SERVICE_ACCOUNT_FILE = os.getenv('SERVICE_ACCOUNT_FILE')
GOOGLE_DRIVE_FOLDER_ID = os.getenv('GOOGLE_DRIVE_FOLDER_ID')

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def test_snt_energy_chart():
    """SNT에너지 차트 생성 및 슬랙 전송 테스트"""
    
    print("=" * 80)
    print("📊 SNT에너지(100840) 차트 생성 및 슬랙 전송 테스트")
    print("=" * 80)
    
    # 테스트 데이터 생성 (공시 정보 형식)
    test_contract = {
        '종목코드': '100840',
        '조회코드': '100840',
        '종목명': 'SNT에너지',
        '시장구분': '코스피',
        '접수일자': '20251026',
        '계약(수주)일자': '20251026',
        '계약상대방': '테스트 계약상대방',
        '계약금액': '1000000000',  # 10억원
        '시작일': '20251026',
        '종료일': '20251226',
        '보고서링크': 'https://dart.fss.or.kr/dsaf001/main.do?rcpNo=test',
        '접수번호': 'TEST123456'
    }
    
    try:
        # 1. 주식 분석기 초기화
        print("\n[1/4] 주식 분석기 초기화 중...")
        analyzer = StockAnalyzer()
        print("✅ 주식 분석기 초기화 완료")
        
        # 2. SNT에너지 분석 수행
        print("\n[2/4] SNT에너지 주가 분석 중...")
        analysis = analyzer.analyze_stock_for_contract(test_contract)
        
        if analysis is None:
            print("❌ 주가 분석 실패")
            return False
        
        print("✅ 주가 분석 완료")
        print(f"   - 현재가: {analysis.current_price:,}원")
        print(f"   - 등락률: {analysis.price_change_rate:+.2f}%")
        print(f"   - 추천점수: {analysis.recommendation_score}/10점")
        
        # 차트 파일 경로 확인
        if analysis.chart_image_path:
            print(f"   - 차트 파일: {analysis.chart_image_path}")
            
            # 파일 존재 여부 확인
            if os.path.exists(analysis.chart_image_path):
                file_size = os.path.getsize(analysis.chart_image_path)
                print(f"   - 파일 크기: {file_size:,} bytes")
            else:
                print("   ⚠️ 차트 파일이 존재하지 않습니다.")
                return False
        else:
            print("   ⚠️ 차트 이미지 경로가 없습니다.")
            return False
        
        # 3. 슬랙 알림기 초기화
        print("\n[3/4] 슬랙 알림기 초기화 중...")
        slack_notifier = SlackNotifier(
            webhook_url=SLACK_WEBHOOK_URL,
            service_account_file=SERVICE_ACCOUNT_FILE,
            drive_folder_id=GOOGLE_DRIVE_FOLDER_ID
        )
        
        if not slack_notifier.is_enabled:
            print("⚠️ 슬랙 웹훅 URL이 설정되지 않았습니다.")
            print("   SLACK_WEBHOOK 환경변수를 설정해주세요.")
            print(f"   차트 파일 위치: {analysis.chart_image_path}")
            return False
        
        print("✅ 슬랙 알림기 초기화 완료")
        
        # 4. 슬랙으로 테스트 메시지 전송
        print("\n[4/4] 슬랙으로 테스트 메시지 전송 중...")
        success = slack_notifier.send_new_contract_notification([test_contract])
        
        if success:
            print("✅ 슬랙 메시지 전송 성공!")
            print(f"   📊 차트가 포함된 메시지가 슬랙으로 전송되었습니다.")
        else:
            print("❌ 슬랙 메시지 전송 실패")
            return False
        
        print("\n" + "=" * 80)
        print("🎉 테스트 완료!")
        print("=" * 80)
        
        return True
        
    except Exception as e:
        print(f"\n❌ 테스트 중 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    success = test_snt_energy_chart()
    sys.exit(0 if success else 1)
