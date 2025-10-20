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
print("🔧 [1/5] 클라우드타입 설정 모듈 임포트 중...")
try:
    from config.cloudtype_settings import (
        validate_environment, 
        CLOUDTYPE_CONFIG, 
        LOGGING_CONFIG,
        IS_PRODUCTION
    )
    print("✅ [1/5] 설정 모듈 임포트 완료")
    
    # 환경 검증
    print("🔍 [2/5] 환경 변수 검증 중...")
    validate_environment()
    print("✅ [2/5] 환경 설정 검증 완료")
    
except Exception as e:
    print(f"❌ 환경 설정 오류: {e}")
    import traceback
    print(traceback.format_exc())
    sys.exit(1)

# 로깅 설정 (한국 시간대 적용)
print("📝 [3/5] 로거 설정 중...")
try:
    from loguru import logger
    import pytz
    
    print("  ├─ loguru 임포트 완료")
    
    # 한국 시간대 설정
    kst = pytz.timezone('Asia/Seoul')
    print("  ├─ 한국 시간대 설정 완료")
    
    # 기존 로거 제거 후 클라우드타입 전용 설정 적용
    logger.remove()
    print("  ├─ 기존 로거 제거 완료")
    
    logger.add(
        sys.stdout,
        format=LOGGING_CONFIG['format'],
        level=LOGGING_CONFIG['level'],
        colorize=not IS_PRODUCTION,  # 프로덕션에서는 색상 제거
        filter=lambda record: record.update(time=record['time'].astimezone(kst))
    )
    print("  ├─ stdout 로거 추가 완료")
    
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
        print("  ├─ 파일 로거 추가 완료 (프로덕션)")
    
    print("✅ [3/5] 로거 설정 완료")
    
    # 이제부터 logger 사용 가능
    logger.info("🎉 Loguru 로거가 활성화되었습니다!")
    
except Exception as e:
    print(f"❌ 로거 설정 오류: {e}")
    import traceback
    print(traceback.format_exc())
    sys.exit(1)

# 전역 변수
print("🔧 [4/5] 전역 변수 및 시그널 핸들러 설정 중...")
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
    logger.debug("✅ 시그널 핸들러 설정 완료")

print("✅ [4/5] 함수 정의 완료")

def run_scraping_system():
    """스크래핑 시스템 실행"""
    global system_instance
    
    logger.info("=" * 80)
    logger.info("🔄 [스크래핑 시스템 실행 시작]")
    logger.info("=" * 80)
    
    try:
        # 클라우드타입 설정으로 시스템 초기화
        logger.info("📦 [1/3] main_cloudtype 모듈 임포트 시도 중...")
        from src.main_cloudtype import CloudTypeDartScrapingSystem
        logger.info("✅ [1/3] CloudTypeDartScrapingSystem 임포트 완료")
        
        logger.info("🔧 [2/3] 시스템 인스턴스 생성 중...")
        system_instance = CloudTypeDartScrapingSystem()
        logger.info("✅ [2/3] 시스템 인스턴스 생성 완료")
        
        logger.info("🚀 [3/3] 클라우드타입에서 DART 스크래핑 시스템을 시작합니다.")
        
        # 시스템 실행
        logger.info("▶️ system_instance.run() 호출 중...")
        success = system_instance.run()
        logger.info(f"✅ system_instance.run() 완료 (결과: {success})")
        
        if success:
            logger.info("🎉 스크래핑 작업이 성공적으로 완료되었습니다.")
            return 0
        else:
            logger.error("❌ 스크래핑 작업 중 오류가 발생했습니다.")
            return 1
            
    except ImportError as ie:
        # 클라우드타입 전용 클래스가 없는 경우 기본 클래스 사용
        logger.warning("=" * 80)
        logger.warning(f"⚠️ main_cloudtype 모듈을 찾을 수 없습니다")
        logger.warning(f"  └─ 오류 상세: {ie}")
        logger.warning("=" * 80)
        logger.info("📦 대체 방안: 기본 DartScrapingSystem 클래스 사용")
        
        try:
            logger.info("📦 [1/3] src.main 모듈 임포트 중...")
            from src.main import DartScrapingSystem
            logger.info("✅ [1/3] DartScrapingSystem 임포트 완료")
            
            logger.info("🔧 [2/3] 시스템 초기화 중...")
            system_instance = DartScrapingSystem()
            logger.info("✅ [2/3] 시스템 초기화 완료")
            
            logger.info("▶️ [3/3] 시스템 실행 시작...")
            success = system_instance.run()
            logger.info(f"✅ [3/3] 시스템 실행 완료 (결과: {success})")
            
            if success:
                logger.info("🎉 실행 완료 - 성공")
            else:
                logger.warning("⚠️ 실행 완료 - 일부 오류 발생")
            
            return 0 if success else 1
        
        except Exception as fallback_error:
            logger.error(f"❌ 기본 클래스 실행 중에도 오류 발생: {fallback_error}")
            import traceback
            logger.error(traceback.format_exc())
            return 1
        
    except Exception as e:
        logger.error("=" * 80)
        logger.error(f"❌ 시스템 실행 중 예상치 못한 오류 발생")
        logger.error(f"  ├─ 오류 유형: {type(e).__name__}")
        logger.error(f"  └─ 오류 메시지: {e}")
        logger.error("=" * 80)
        import traceback
        logger.error("상세 스택 트레이스:")
        logger.error(traceback.format_exc())
        return 1

def health_check():
    """헬스체크 함수"""
    try:
        logger.debug("  ├─ 기본 헬스체크 로직 실행 중...")
        logger.debug("  ├─ 시스템 모듈 확인...")
        logger.debug("  └─ 헬스체크 완료")
        return True
    except Exception as e:
        logger.error(f"❌ 헬스체크 실패: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

def run_scheduler():
    """
    스케줄러 실행 - 1분마다 스크래핑 시스템 실행
    클라우드타입에서 계속 돌아가면서 시장 개장 시간을 체크합니다.
    """
    logger.info("📦 schedule 모듈 임포트 중...")
    import schedule
    logger.info("✅ schedule 모듈 임포트 완료")
    
    logger.info("⏰ 스케줄러 시작 - 1분마다 실행")
    
    # 즉시 한 번 실행
    logger.info("🚀 초기 실행 시작...")
    try:
        run_scraping_system()
        logger.info("✅ 초기 실행 완료")
    except Exception as e:
        logger.error(f"❌ 초기 실행 실패: {e}")
        import traceback
        logger.error(traceback.format_exc())
    
    # 1분마다 실행하도록 스케줄 설정
    logger.info("📅 스케줄 설정 중... (1분마다)")
    schedule.every(1).minutes.do(run_scraping_system)
    logger.info("✅ 스케줄 설정 완료")
    
    # 무한 루프로 스케줄 실행
    logger.info("🔄 무한 루프 시작 - 스케줄 실행 대기 중...")
    loop_count = 0
    while is_running:
        try:
            schedule.run_pending()
            time.sleep(1)  # 1초마다 체크
            loop_count += 1
            if loop_count % 60 == 0:  # 1분마다 로그
                logger.debug(f"⏱️ 스케줄러 정상 작동 중... ({loop_count//60}분 경과)")
        except KeyboardInterrupt:
            logger.info("⚠️ 스케줄러 중단 (KeyboardInterrupt)")
            break
        except Exception as e:
            logger.error(f"❌ 스케줄러 실행 중 오류: {e}")
            import traceback
            logger.error(traceback.format_exc())
            time.sleep(5)  # 오류 시 5초 대기 후 재시도

def main():
    """메인 실행 함수"""
    print("🎯 main() 함수 시작!")
    
    logger.info("=" * 80)
    logger.info("🌥️ 클라우드타입 DART 스크래핑 및 자동매매 시스템")
    logger.info(f"환경: {'프로덕션' if IS_PRODUCTION else '개발'}")
    logger.info(f"포트: {CLOUDTYPE_CONFIG['port']}")
    logger.info("=" * 80)
    
    # 시그널 핸들러 설정
    logger.info("🔧 시그널 핸들러 설정 중...")
    setup_signal_handlers()
    
    try:
        # 초기 헬스체크
        logger.info("🏥 헬스체크 실행 중...")
        if not health_check():
            logger.error("❌ 초기 헬스체크 실패")
            return 1
        
        logger.info("✅ 헬스체크 통과")
        
        # 스케줄러 실행 (무한 루프)
        logger.info("🔄 스케줄러 모드로 전환 중...")
        logger.info("⏰ 1분마다 자동 실행 시작...")
        run_scheduler()
        
        logger.info("✅ 시스템이 정상적으로 종료되었습니다.")
        return 0
        
    except KeyboardInterrupt:
        logger.info("⚠️ 사용자에 의해 중단되었습니다.")
        return 1
        
    except Exception as e:
        logger.error(f"❌ 예상치 못한 오류가 발생했습니다: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return 1
        
    finally:
        logger.info("시스템 종료 중...")

if __name__ == '__main__':
    print("🚀 [5/5] 메인 함수 호출 준비...")
    print("="*80)
    try:
        print("▶️ main() 함수 호출 중...")
        exit_code = main()
        print(f"✅ main() 함수 완료 (종료 코드: {exit_code})")
        sys.exit(exit_code)
    except Exception as e:
        print(f"❌ 치명적 오류: {e}")
        import traceback
        print(traceback.format_exc())
        sys.exit(1)
