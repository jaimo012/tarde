#!/usr/bin/env python3
"""
DART 공시 스크래핑 시스템 실행 스크립트

사용법:
    python run.py

이 스크립트는 다음과 같은 작업을 수행합니다:
1. 구글 스프레드시트에서 분석 대상 회사 목록을 가져옵니다
2. 각 회사별로 DART API를 통해 단일판매공급계약 공시를 검색합니다
3. 새로운 공시에 대해 보고서를 다운로드하고 내용을 분석합니다
4. 추출된 데이터를 구글 스프레드시트에 저장합니다
"""

import sys
import os

# 프로젝트 루트 디렉토리를 Python 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.main import main

if __name__ == '__main__':
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n⚠️ 사용자에 의해 중단되었습니다.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 예상치 못한 오류가 발생했습니다: {e}")
        sys.exit(1)
