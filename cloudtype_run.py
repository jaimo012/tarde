#!/usr/bin/env python3
"""
클라우드타입(CloudType) 전용 실행 스크립트

이 스크립트는 클라우드타입 환경에서 DART 공시 스크래핑 시스템을 실행합니다.
환경변수를 통해 설정을 관리하고, 클라우드 환경에 최적화된 설정을 사용합니다.
"""

import sys
import os
import signal
import time
from typing import Optional

# 프로젝트 루트 디렉토리를 Python 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 클라우드타입 설정 사용
try:
    from config.cloudtype_settings import (
        validate_environment, 
        CLOUDTYPE_CONFIG, 
        LOGGING_CONFIG,
        IS_PRODUCTION
    )
    
    # 환경 검증
    validate_environment()
    print("✅ 환경 설정 검증 완료")
    
except Exception as e:
    print(f"❌ 환경 설정 오류: {e}")
    sys.exit(1)

# 로깅 설정 (한국 시간대 적용)
from loguru import logger
import pytz

# 한국 시간대 설정
kst = pytz.timezone('Asia/Seoul')

# 기존 로거 제거 후 클라우드타입 전용 설정 적용
logger.remove()
logger.add(
    sys.stdout,
    format=LOGGING_CONFIG['format'],
    level=LOGGING_CONFIG['level'],
    colorize=not IS_PRODUCTION,  # 프로덕션에서는 색상 제거
    filter=lambda record: record.update(time=record['time'].astimezone(kst))
)

if IS_PRODUCTION:
    logger.add(
        LOGGING_CONFIG['file_path'],
        format=LOGGING_CONFIG['format'],
        level=LOGGING_CONFIG['level'],
        rotation=LOGGING_CONFIG['rotation'],
        retention=LOGGING_CONFIG['retention'],
        encoding='utf-8',
        filter=lambda record: record.update(time=record['time'].astimezone(kst))
    )

# 전역 변수
system_instance: Optional[object] = None
is_running = True

def signal_handler(signum, frame):
    """시그널 핸들러 - 우아한 종료"""
    global is_running
    logger.info(f"종료 시그널 수신: {signum}")
    is_running = False
    
    if system_instance and hasattr(system_instance, 'stop'):
        system_instance.stop()

def setup_signal_handlers():
    """시그널 핸들러 설정"""
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

def run_scraping_system():
    """스크래핑 시스템 실행"""
    global system_instance
    
    try:
        # 클라우드타입 설정으로 시스템 초기화
        from src.main_cloudtype import CloudTypeDartScrapingSystem
        
        system_instance = CloudTypeDartScrapingSystem()
        logger.info("🚀 클라우드타입에서 DART 스크래핑 시스템을 시작합니다.")
        
        # 시스템 실행
        success = system_instance.run()
        
        if success:
            logger.info("✅ 스크래핑 작업이 성공적으로 완료되었습니다.")
            return 0
        else:
            logger.error("❌ 스크래핑 작업 중 오류가 발생했습니다.")
            return 1
            
    except ImportError:
        # 클라우드타입 전용 클래스가 없는 경우 기본 클래스 사용
        logger.warning("클라우드타입 전용 클래스를 찾을 수 없어 기본 클래스를 사용합니다.")
        
        from src.main import DartScrapingSystem
        system_instance = DartScrapingSystem()
        
        success = system_instance.run()
        return 0 if success else 1
        
    except Exception as e:
        logger.error(f"시스템 실행 중 예상치 못한 오류 발생: {e}")
        return 1

def health_check():
    """헬스체크 함수"""
    try:
        # 기본적인 헬스체크 로직
        logger.debug("헬스체크 실행")
        return True
    except Exception as e:
        logger.error(f"헬스체크 실패: {e}")
        return False

def main():
    """메인 실행 함수"""
    logger.info("=" * 50)
    logger.info("🌥️ 클라우드타입 DART 스크래핑 시스템")
    logger.info(f"환경: {'프로덕션' if IS_PRODUCTION else '개발'}")
    logger.info(f"포트: {CLOUDTYPE_CONFIG['port']}")
    logger.info("=" * 50)
    
    # 시그널 핸들러 설정
    setup_signal_handlers()
    
    try:
        # 초기 헬스체크
        if not health_check():
            logger.error("초기 헬스체크 실패")
            return 1
        
        # 스크래핑 시스템 실행
        exit_code = run_scraping_system()
        
        # 종료 로그
        if exit_code == 0:
            logger.info("🎉 시스템이 성공적으로 종료되었습니다.")
        else:
            logger.error("💥 시스템이 오류와 함께 종료되었습니다.")
        
        return exit_code
        
    except KeyboardInterrupt:
        logger.info("⚠️ 사용자에 의해 중단되었습니다.")
        return 1
        
    except Exception as e:
        logger.error(f"❌ 예상치 못한 오류가 발생했습니다: {e}")
        return 1
        
    finally:
        logger.info("시스템 종료 중...")

if __name__ == '__main__':
    try:
        exit_code = main()
        sys.exit(exit_code)
    except Exception as e:
        print(f"치명적 오류: {e}")
        sys.exit(1)
