"""
DART 공시 스크래핑 및 자동매매 시스템 메인 실행 모듈

이 모듈은 전체 시스템의 실행 흐름을 관리합니다.
- 공시 모니터링 및 분석
- 자동매매 실행 (조건 충족 시)
- 보유 포지션 관리
"""

import time
import os
from typing import List, Dict
from loguru import logger
from datetime import datetime

from config.settings import (
    LOGGING_CONFIG, REQUIRED_FIELDS, SLACK_WEBHOOK_URL, TRADING_CONFIG,
    SERVICE_ACCOUNT_FILE, GOOGLE_DRIVE_FOLDER_ID
)
from src.dart_api.client import DartApiClient
from src.dart_api.analyzer import ReportAnalyzer
from src.google_sheets.client import GoogleSheetsClient
from src.utils.slack_notifier import SlackNotifier
from src.utils.market_schedule import should_run_dart_scraping, get_market_status, is_market_open
from src.trading.auto_trading_system import AutoTradingSystem
from src.utils.error_handler import initialize_error_handler, get_error_handler


class DartScrapingSystem:
    """DART 공시 스크래핑 시스템의 메인 클래스"""
    
    def __init__(self):
        """시스템 컴포넌트들을 초기화합니다."""
        print("🚀 DART 스크래핑 및 자동매매 시스템 초기화 시작")
        logger.info("="*80)
        logger.info("🚀 DART 스크래핑 및 자동매매 시스템 초기화 시작")
        logger.info("="*80)
        
        print("  ├─ DART API 클라이언트 초기화 중...")
        self.dart_client = DartApiClient()
        print("  ├─ 보고서 분석기 초기화 중...")
        self.analyzer = ReportAnalyzer()
        print("  ├─ 구글 시트 클라이언트 초기화 중...")
        self.sheets_client = GoogleSheetsClient()
        print("  ├─ 슬랙 알림 클라이언트 초기화 중...")
        self.slack_notifier = SlackNotifier(
            webhook_url=SLACK_WEBHOOK_URL,
            service_account_file=SERVICE_ACCOUNT_FILE,
            drive_folder_id=GOOGLE_DRIVE_FOLDER_ID
        )
        
        # 통합 오류 처리기 초기화
        print("  ├─ 통합 오류 처리기 초기화 중...")
        initialize_error_handler(self.sheets_client, self.slack_notifier)
        self.error_handler = get_error_handler()
        logger.info("✅ 통합 오류 처리기 초기화 완료")
        
        # 자동매매 시스템 초기화
        print("  ├─ 자동매매 시스템 초기화 중...")
        self.auto_trading = AutoTradingSystem(self.sheets_client, self.slack_notifier)
        
        # 로깅 설정
        print("  ├─ 로깅 설정 중...")
        self._setup_logging()
        
        # 중복 실행 방지 락
        self.lock_file = "logs/trading.lock"
        
        print("✅ DART 스크래핑 및 자동매매 시스템 초기화 완료!")
        logger.info("✅ DART 스크래핑 및 자동매매 시스템이 초기화되었습니다.")
        logger.info("="*80)
    
    def _setup_logging(self):
        """로깅 설정을 초기화합니다."""
        import pytz
        
        # 한국 시간대 설정
        kst = pytz.timezone('Asia/Seoul')
        
        logger.add(
            LOGGING_CONFIG['file_path'],
            format=LOGGING_CONFIG['format'],
            level=LOGGING_CONFIG['level'],
            rotation=LOGGING_CONFIG['rotation'],
            retention=LOGGING_CONFIG['retention'],
            encoding='utf-8',
            serialize=LOGGING_CONFIG.get('serialize', False),
            filter=lambda record: record.update(time=record['time'].astimezone(kst))
        )
    
    def run(self) -> bool:
        """
        전체 스크래핑 프로세스를 실행합니다.
        
        Returns:
            bool: 실행 성공 여부
        """
        print("🔄 DartScrapingSystem.run() 메서드 실행 시작")
        logger.info("🚀 DART 공시 스크래핑 및 구글 시트 저장 자동화를 시작합니다.")
        
        try:
            result = self._run_with_error_handling()
            print(f"✅ DartScrapingSystem.run() 완료 (결과: {result})")
            return result
        except Exception as e:
            print(f"❌ DartScrapingSystem.run() 예외 발생: {e}")
            # 전역 예외 처리 - 모든 예상치 못한 오류 캐치
            self._handle_critical_error("시스템 전체 실행 실패", e)
            return False
    
    def _run_with_error_handling(self) -> bool:
        """
        실제 실행 로직 (오류 처리 포함)
        
        Returns:
            bool: 실행 성공 여부
        """
        try:
            # 0단계: 시스템 시작 알림 전송 (비활성화 - 1분마다 실행되므로 알림 불필요)
            # self._send_startup_notification()
            
            # 1단계: 시장 개장 여부 확인
            print("📊 [1/6] 시장 개장 여부 확인 중...")
            should_run, market_status = should_run_dart_scraping()
            print(f"  └─ 시장 상태: {market_status}")
            logger.info(f"📊 시장 상태: {market_status}")
            
            if not should_run:
                print("⏸️ 시장이 휴장 중이므로 스크래핑을 건너뜁니다.")
                logger.info("⏸️ 시장이 휴장 중이므로 스크래핑을 건너뜁니다.")
                # 시스템은 정상 작동 중이지만 휴장일이므로 대기
                return True  # 정상적인 스킵이므로 True 반환
            
            print("✅ 시장 개장 중! DART 스크래핑 진행합니다.")
            logger.info("✅ 시장 개장 중이므로 스크래핑을 진행합니다.")
            
            # 2단계: 구글 스프레드시트 연결
            print("📊 [2/6] 구글 스프레드시트 연결 중...")
            if not self._connect_to_sheets():
                print("❌ 구글 시트 연결 실패")
                return False
            print("✅ 구글 시트 연결 성공")
            
            # 3단계: 기존 데이터 로드
            print("📊 [3/6] 기존 데이터 로드 중...")
            existing_reports, company_list = self._load_existing_data()
            if company_list is None:
                print("❌ 기존 데이터 로드 실패")
                return False
            print(f"✅ 기존 데이터 로드 완료 (회사 {len(company_list)}개)")
            
            # 4단계: 각 회사별 공시 처리
            print(f"📊 [4/6] {len(company_list)}개 회사의 DART 공시 처리 시작...")
            total_new_contracts = self._process_companies(company_list, existing_reports)
            print(f"✅ 공시 처리 완료 (신규 계약: {total_new_contracts}건)")
            
            # 5단계: 완료 알림
            completion_message = f"🏁 모든 회사에 대한 분석 및 저장이 완료되었습니다. (신규 계약: {total_new_contracts}건)"
            print(completion_message)
            logger.info(completion_message)
            
            # 신규 계약이 있을 때만 완료 알림 전송 (의미있는 정보만)
            if total_new_contracts > 0:
                self.slack_notifier.send_system_notification(
                    f"🎉 DART 스크래핑 완료: 총 {total_new_contracts}건의 신규 계약을 발견했습니다!",
                    "info"
                )
            # 신규 계약이 없으면 슬랙 알림 전송하지 않음 (스팸 방지)
            
            # 6단계: 보유 포지션 관리 (자동매매 활성화 시)
            if is_market_open():
                print("📊 [6/6] 보유 포지션 관리 시작...")
                logger.info("보유 포지션 관리를 시작합니다...")
                try:
                    self.auto_trading.manage_positions()
                    print("✅ 포지션 관리 완료")
                except Exception as e:
                    print(f"⚠️ 포지션 관리 중 오류: {e}")
                    logger.error(f"포지션 관리 중 오류 발생: {e}")
                    # 포지션 관리 실패는 시스템을 중단시키지 않음
            
            print("🎉 전체 프로세스 완료!")
            return True
            
        except Exception as e:
            logger.error(f"시스템 실행 중 예상치 못한 오류 발생: {e}")
            # 시스템 전체 오류만 슬랙 알림 (중요한 오류)
            self.slack_notifier.send_system_notification(
                f"🚨 시스템 전체 오류 발생: {str(e)}",
                "error"
            )
            return False
    
    def _connect_to_sheets(self) -> bool:
        """구글 스프레드시트에 연결합니다."""
        try:
            success = self.sheets_client.connect()
            if success:
                # 시트 통계 출력
                stats = self.sheets_client.get_sheet_statistics()
                logger.info(f"✅ 구글 시트 연결 성공. 현재 데이터: {stats}")
            return success
        except Exception as e:
            logger.error(f"❌ 구글 시트 연결에 실패했습니다: {e}")
            return False
    
    def _load_existing_data(self) -> tuple:
        """기존 데이터를 로드합니다."""
        try:
            # 기존 처리된 보고서 번호 가져오기
            existing_reports = self.sheets_client.get_existing_report_numbers()
            logger.info(f"✅ 기존 처리된 보고서 {len(existing_reports)}건을 확인했습니다.")
            
            # 분석 대상 회사 목록 가져오기
            company_list = self.sheets_client.get_company_list()
            if company_list is None:
                logger.error("❌ 회사 목록을 가져올 수 없습니다.")
                return existing_reports, None
            
            logger.info(f"✅ 분석 대상 회사 {len(company_list)}개를 확인했습니다.")
            return existing_reports, company_list
            
        except Exception as e:
            logger.error(f"❌ 기존 데이터 로드 실패: {e}")
            return set(), None
    
    def _process_companies(self, company_list, existing_reports: set) -> int:
        """각 회사별로 공시를 처리합니다."""
        total_companies = len(company_list)
        total_new_contracts = 0
        failed_companies = []
        
        print(f"\n{'='*80}")
        print(f"📊 회사별 공시 처리 시작 (총 {total_companies}개 회사)")
        print(f"{'='*80}\n")
        logger.info(f"\n{'='*60}")
        logger.info(f"📊 회사별 공시 처리 시작 (총 {total_companies}개 회사)")
        logger.info(f"{'='*60}")
        
        for idx, (index, company_row) in enumerate(company_list.iterrows()):
            corp_code = company_row['조회코드']
            corp_name = company_row['종목명']
            current_num = idx + 1  # 1부터 시작하는 현재 번호
            progress = (current_num / total_companies * 100)
            
            # 진행 바 생성 (20칸)
            bar_length = 20
            filled = int(bar_length * current_num / total_companies)
            bar = '█' * filled + '░' * (bar_length - filled)
            
            # 10개마다 또는 첫 번째/마지막 회사일 때 진행 상황 출력
            if current_num % 10 == 0 or idx == 0 or current_num == total_companies:
                print(f"🔍 [{current_num}/{total_companies}] {bar} {progress:.1f}% | 최근: {corp_name[:15]}...")
            
            logger.info(f"\n🔎 [{current_num}/{total_companies}] '{corp_name}'({corp_code}) 처리 시작...")
            self.error_handler.log_operation(
                module="공시 처리",
                operation=f"{corp_name} 분석",
                status="시작",
                details=f"진행률: {progress:.1f}%"
            )
            
            try:
                # 회사별 공시 처리
                new_contracts, new_excluded = self._process_company_disclosures(
                    company_row, existing_reports
                )
                
                # 결과 저장 및 슬랙 알림
                saved_contracts = self._save_company_results(corp_name, new_contracts, new_excluded)
                total_new_contracts += saved_contracts
                
                # 중요한 결과만 즉시 출력
                if saved_contracts > 0:
                    print(f"  ✅ [{current_num}] {corp_name[:20]:20s} → 🎉 신규 계약 {saved_contracts}건 발견!")
                elif len(new_excluded) > 0:
                    print(f"  ⚠️ [{current_num}] {corp_name[:20]:20s} → 분석제외 {len(new_excluded)}건")
                # 신규 없으면 출력 안 함 (로그만)
                
                self.error_handler.log_operation(
                    module="공시 처리",
                    operation=f"{corp_name} 분석",
                    status="완료",
                    details=f"신규 계약: {saved_contracts}건, 제외: {len(new_excluded)}건"
                )
                
            except Exception as e:
                print(f"  ❌ [{current_num}] {corp_name[:20]:20s} → 오류: {str(e)[:40]}...")
                logger.error(f"❌ 회사 '{corp_name}' 처리 중 오류 발생: {e}")
                failed_companies.append(corp_name)
                
                # 오류 처리 (시트 기록 + 로그, 슬랙 알림은 생략)
                self.error_handler.handle_error(
                    error=e,
                    module="공시 처리",
                    operation=f"{corp_name} 공시 분석",
                    severity='WARNING',
                    related_stock=f"{corp_name}({corp_code})",
                    send_slack=False,  # 개별 회사 오류는 슬랙 스팸 방지
                    log_to_sheet=True
                )
                continue
        
        # 마지막 진행 상황 줄바꿈
        print()
        
        # 최종 요약
        print(f"\n{'='*80}")
        print(f"📊 회사별 공시 처리 완료")
        print(f"  ├─ 총 처리: {total_companies}개")
        print(f"  ├─ 성공: {total_companies - len(failed_companies)}개")
        print(f"  ├─ 실패: {len(failed_companies)}개")
        print(f"  └─ 신규 계약: {total_new_contracts}건 {'🎉' if total_new_contracts > 0 else ''}")
        if failed_companies:
            print(f"⚠️ 실패한 회사: {', '.join(failed_companies[:5])}")  # 최대 5개만 표시
        print(f"{'='*80}\n")
        
        logger.info(f"\n{'='*60}")
        logger.info(f"📊 회사별 공시 처리 완료")
        logger.info(f"  ├─ 총 처리: {total_companies}개")
        logger.info(f"  ├─ 성공: {total_companies - len(failed_companies)}개")
        logger.info(f"  ├─ 실패: {len(failed_companies)}개")
        logger.info(f"  └─ 신규 계약: {total_new_contracts}건")
        if failed_companies:
            logger.warning(f"⚠️ 실패한 회사: {', '.join(failed_companies)}")
        logger.info(f"{'='*60}\n")
        
        return total_new_contracts
    
    def _process_company_disclosures(self, company_row, existing_reports: set) -> tuple:
        """특정 회사의 공시를 처리합니다."""
        corp_code = company_row['조회코드']
        corp_name = company_row['종목명']
        
        new_contracts = []
        new_excluded = []
        
        # 1단계: 공시 검색
        logger.info(f"  → 1단계: DART API 공시 검색 중...")
        self.error_handler.log_api_call(
            api_name="DART API",
            endpoint="/api/list.json",
            method="GET",
            params={'corp_code': corp_code},
            status='시작'
        )
        
        disclosures = self.dart_client.search_disclosures_all_pages(corp_code)
        
        if not disclosures:
            logger.info(f"  ✅ 공시 검색 완료 → 관련 공시 없음")
            self.error_handler.log_api_call(
                api_name="DART API",
                endpoint="/api/list.json",
                status='성공',
                response_code=200
            )
            return new_contracts, new_excluded
        
        logger.info(f"  ✅ 공시 검색 완료 → {len(disclosures)}개 발견")
        self.error_handler.log_api_call(
            api_name="DART API",
            endpoint="/api/list.json",
            status='성공',
            response_code=200
        )
        
        # 2단계: 각 공시별 처리
        for disclosure in disclosures:
            rcept_no = disclosure['rcept_no']
            
            # 이미 처리된 보고서는 건너뛰기
            if rcept_no in existing_reports:
                continue
            
            logger.info(f"   ✨ 새로운 공시({rcept_no}) 발견! 데이터 추출을 시작합니다.")
            
            # 3단계: 보고서 분석
            contract_data = self._analyze_disclosure(disclosure, company_row)
            if not contract_data:
                logger.warning(f"   - 보고서({rcept_no}) 분석 실패. 건너뜁니다.")
                continue
            
            # 4단계: 데이터 완전성 검증 및 분류
            if self.analyzer.validate_extracted_data(contract_data):
                new_contracts.append(contract_data)
                logger.info(f"   ✅ 완전한 데이터. '계약' 시트로 분류됩니다.")
            else:
                new_excluded.append(contract_data)
                logger.info(f"   ⚠️ 불완전한 데이터. '분석제외' 시트로 분류됩니다.")
            
            # 처리된 보고서로 표시
            existing_reports.add(rcept_no)
            
            # API 호출 제한 준수
            time.sleep(0.5)
        
        return new_contracts, new_excluded
    
    def _analyze_disclosure(self, disclosure: Dict, company_row) -> Dict:
        """개별 공시를 분석합니다."""
        rcept_no = disclosure['rcept_no']
        
        try:
            # 1단계: 보고서 내용 다운로드
            report_content = self.dart_client.get_report_content(rcept_no)
            if not report_content:
                logger.warning(f"   - 보고서({rcept_no}) 내용을 가져올 수 없습니다.")
                return None
            
            # 2단계: 보고서 분석
            extracted_data = self.analyzer.analyze_report(report_content)
            
            # 3단계: 데이터 정제
            cleaned_data = self.analyzer.clean_extracted_data(extracted_data)
            
            # 4단계: 회사 정보와 공시 정보 결합
            report_url = f"https://dart.fss.or.kr/dsaf001/main.do?rcpNo={rcept_no}"
            
            final_data = {
                **company_row.to_dict(),  # 회사 기본 정보
                '접수일자': disclosure['rcept_dt'],
                '보고서명': disclosure['report_nm'],
                '접수번호': rcept_no,
                '보고서링크': report_url,
                **cleaned_data  # 추출된 계약 정보
            }
            
            return final_data
            
        except Exception as e:
            logger.error(f"   - 공시({rcept_no}) 분석 중 오류 발생: {e}")
            return None
    
    def _save_company_results(self, corp_name: str, new_contracts: List, new_excluded: List) -> int:
        """회사별 처리 결과를 저장하고 슬랙 알림을 전송합니다."""
        saved_contracts_count = 0
        
        try:
            # 계약 데이터 저장
            if new_contracts:
                success = self.sheets_client.save_contract_data(new_contracts)
                if success:
                    saved_contracts_count = len(new_contracts)
                    logger.info(f"   ✅ '{corp_name}': {len(new_contracts)}개 계약 데이터 저장 완료")
                    
                    # 슬랙 알림 전송
                    self.slack_notifier.send_new_contract_notification(new_contracts)
                    
                    # 자동매매 처리: 각 신규 계약에 대해 매수 조건 확인
                    for contract in new_contracts:
                        try:
                            self.auto_trading.process_new_contract(contract)
                        except Exception as e:
                            logger.error(f"자동매매 처리 중 오류 발생: {e}")
                            # 자동매매 실패는 시스템을 중단시키지 않음
                    
                else:
                    logger.error(f"   ❌ '{corp_name}': 계약 데이터 저장 실패")
                    # 데이터 저장 실패는 중요한 오류이므로 슬랙 알림
                    self.slack_notifier.send_system_notification(
                        f"🚨 데이터 저장 실패: '{corp_name}' 계약 데이터를 저장할 수 없습니다",
                        "error"
                    )
            
            # 분석 제외 데이터 저장
            if new_excluded:
                success = self.sheets_client.save_excluded_data(new_excluded)
                if success:
                    logger.info(f"   ✅ '{corp_name}': {len(new_excluded)}개 분석제외 데이터 저장 완료")
                else:
                    logger.error(f"   ❌ '{corp_name}': 분석제외 데이터 저장 실패")
            
            # 새로운 데이터가 없는 경우
            if not new_contracts and not new_excluded:
                logger.info(f" -> '{corp_name}': 새로운 공시가 없습니다.")
                
        except Exception as e:
            logger.error(f"'{corp_name}' 결과 저장 중 오류 발생: {e}")
            # 저장 오류는 중요하므로 슬랙 알림
            self.slack_notifier.send_system_notification(
                f"🚨 데이터 저장 오류: '{corp_name}' - {str(e)}",
                "error"
            )
        
        return saved_contracts_count
    
    def _send_startup_notification(self):
        """
        시스템 시작 알림을 슬랙으로 전송합니다.
        
        ⚠️ 하루에 한 번만 알림을 보냅니다 (중복 알림 방지)
        """
        try:
            # 1. 시스템 임시 디렉토리 사용 (모든 환경에서 접근 가능)
            import tempfile
            temp_dir = tempfile.gettempdir()  # /tmp/ 또는 시스템 임시 디렉토리
            
            today = datetime.now().strftime('%Y%m%d')
            flag_file = os.path.join(temp_dir, f"trading_startup_notified_{today}.flag")
            
            # 2. 오늘 이미 알림을 보냈는지 확인
            if os.path.exists(flag_file):
                logger.debug(f"✅ 오늘({today}) 이미 시작 알림을 보냈습니다. 스킵합니다. (플래그: {flag_file})")
                return
            
            logger.info(f"📢 시스템 시작 알림을 준비 중... (하루 첫 실행, 플래그: {flag_file})")
            
            balance_info = None
            position_info = None
            trading_enabled = False
            
            # 시장 상태 확인
            should_run, market_status = should_run_dart_scraping()
            
            # 자동매매 시스템 존재 여부 확인
            auth_failed = False
            if hasattr(self, 'auto_trading'):
                # 자동매매 활성화 여부
                trading_enabled = self.auto_trading.trading_enabled
                
                if trading_enabled:
                    logger.info("✅ 자동매매 활성화 상태 - API 연결 확인 중...")
                    
                    # 예수금 조회 시도 (활성화 상태에서만)
                    try:
                        balance_info = self.auto_trading.kiwoom_client.get_balance()
                        if balance_info:
                            logger.info(f"✅ 키움 API 연결 성공 - 예수금: {balance_info['available_amount']:,.0f}원")
                    except Exception as e:
                        logger.error(f"🚨 키움 API 연결 실패 - 예수금 조회 실패: {e}")
                    
                    # 보유 포지션 조회 시도
                    try:
                        position_info = self.auto_trading.position_mgr.get_current_position()
                        if position_info:
                            logger.info(f"✅ 보유 종목: {position_info['stock_name']}({position_info['stock_code']}) {position_info['quantity']}주")
                        else:
                            logger.info("ℹ️ 보유 종목 없음")
                    except Exception as e:
                        logger.error(f"🚨 보유 포지션 조회 실패: {e}")
                else:
                    # 자동매매가 비활성화된 경우 - 인증 실패일 가능성 높음
                    logger.warning("⚠️ 자동매매 비활성화 상태 - 키움 API 인증 실패 가능성")
                    auth_failed = True
            else:
                logger.info("자동매매 시스템이 초기화되지 않았습니다")
            
            # 슬랙 알림 전송
            self.slack_notifier.send_system_startup_notification(
                balance_info=balance_info,
                position_info=position_info,
                trading_enabled=trading_enabled,
                market_status=market_status,
                is_market_open=should_run,
                auth_failed=auth_failed
            )
            
            # 3. 플래그 파일 생성 (오늘 알림을 보냈다는 표시)
            try:
                with open(flag_file, 'w') as f:
                    f.write(f"{datetime.now().isoformat()}\n")
                    f.write(f"Process ID: {os.getpid()}\n")
                logger.info(f"✅ 시스템 시작 알림 전송 완료 (플래그 생성: {flag_file})")
            except Exception as e:
                logger.error(f"❌ 플래그 파일 생성 실패: {e}")
                logger.error(f"플래그 경로: {flag_file}")
            
            # 4. 이전 날짜의 플래그 파일 삭제 (정리)
            try:
                import glob
                search_pattern = os.path.join(temp_dir, "trading_startup_notified_*.flag")
                for old_flag in glob.glob(search_pattern):
                    if old_flag != flag_file:
                        os.remove(old_flag)
                        logger.debug(f"🗑️ 이전 플래그 파일 삭제: {old_flag}")
            except Exception as e:
                logger.warning(f"이전 플래그 파일 삭제 실패 (무시): {e}")
            
        except Exception as e:
            logger.error(f"시스템 시작 알림 전송 중 오류 발생: {e}")
            # 알림 전송 실패는 시스템 실행을 막지 않음
    
    def _handle_critical_error(self, error_title: str, exception: Exception):
        """
        치명적 오류를 처리하고 상세 정보를 슬랙으로 전송하며 시트에 기록합니다.
        
        Args:
            error_title: 오류 제목
            exception: 발생한 예외
        """
        import traceback
        from datetime import datetime
        
        logger.error(f"치명적 오류 발생: {error_title}")
        logger.error(f"예외 타입: {type(exception).__name__}")
        logger.error(f"예외 메시지: {str(exception)}")
        
        # 스택 트레이스 추출
        stack_trace = traceback.format_exc()
        logger.error(f"스택 트레이스:\n{stack_trace}")
        
        # 상세 정보 수집
        error_details = {
            "⚠️ 오류 유형": type(exception).__name__,
            "📝 오류 메시지": str(exception),
            "📍 발생 위치": error_title,
        }
        
        # 시트 기록용 변수 초기화
        trading_status = "비활성화"
        position_info = "없음"
        related_stock = "해당없음"
        
        # 자동매매 시스템 상태 추가
        try:
            if hasattr(self, 'auto_trading') and self.auto_trading.trading_enabled:
                error_details["🤖 자동매매 상태"] = "활성화됨"
                trading_status = "활성화"
                
                # 예수금 조회 시도
                try:
                    balance = self.auto_trading.kiwoom_client.get_balance()
                    if balance:
                        error_details["💰 예수금"] = f"{balance['available_amount']:,}원"
                except:
                    error_details["💰 예수금"] = "조회 실패"
                
                # 보유 포지션 조회 시도
                try:
                    position = self.auto_trading.position_mgr.get_current_position()
                    if position:
                        position_text = f"{position['stock_name']}({position['stock_code']}) {position['quantity']}주"
                        error_details["📊 보유 종목"] = position_text
                        position_info = position_text
                        related_stock = f"{position['stock_name']}({position['stock_code']})"
                    else:
                        error_details["📊 보유 종목"] = "없음"
                except:
                    error_details["📊 보유 종목"] = "조회 실패"
                    position_info = "조회 실패"
            else:
                error_details["🤖 자동매매 상태"] = "비활성화됨"
        except Exception as e:
            error_details["🤖 자동매매 상태"] = f"상태 확인 실패: {str(e)}"
            trading_status = f"확인 실패: {str(e)}"
        
        # 슬랙으로 치명적 오류 알림 전송
        try:
            self.slack_notifier.send_critical_error(
                error_title=error_title,
                error_details=error_details,
                stack_trace=stack_trace
            )
            logger.info("치명적 오류 슬랙 알림 전송 완료")
        except Exception as e:
            logger.error(f"치명적 오류 알림 전송 실패: {e}")
        
        # 구글 시트에 오류 로그 기록
        try:
            # 상세 정보 텍스트 생성
            details_text = f"발생 위치: {error_title}\n"
            details_text += f"예외 메시지: {str(exception)}\n"
            if stack_trace:
                # 스택 트레이스가 너무 길면 마지막 500자만
                if len(stack_trace) > 500:
                    details_text += f"스택 트레이스: ...\n{stack_trace[-500:]}"
                else:
                    details_text += f"스택 트레이스:\n{stack_trace}"
            
            error_log = {
                'timestamp': datetime.now(),
                'severity': 'CRITICAL',
                'module': '시스템 전체',
                'error_type': type(exception).__name__,
                'error_message': str(exception)[:200],  # 메시지는 200자로 제한
                'related_stock': related_stock,
                'trading_status': trading_status,
                'position_info': position_info,
                'resolution_status': '미해결',
                'details': details_text[:1000]  # 상세 정보는 1000자로 제한
            }
            
            self.google_client.log_error_to_sheet(error_log)
            logger.info("오류 로그 시트 기록 완료")
        except Exception as e:
            logger.error(f"오류 로그 시트 기록 실패: {e}")
            # 시트 기록 실패는 시스템을 중단시키지 않음


def acquire_lock(lock_file: str) -> bool:
    """
    프로세스 락을 획득합니다 (중복 실행 방지).
    
    Args:
        lock_file: 락 파일 경로
        
    Returns:
        bool: 락 획득 성공 여부
    """
    try:
        # 락 파일 디렉토리 생성
        os.makedirs(os.path.dirname(lock_file), exist_ok=True)
        
        # 락 파일이 이미 존재하는지 확인
        if os.path.exists(lock_file):
            # 락 파일의 생성 시간 확인 (10분 이상 오래된 경우 제거)
            file_age = time.time() - os.path.getmtime(lock_file)
            if file_age > 600:  # 10분
                logger.warning(f"오래된 락 파일 발견 ({file_age:.0f}초 전). 제거합니다.")
                os.remove(lock_file)
            else:
                logger.warning("다른 프로세스가 실행 중입니다. 중복 실행을 방지합니다.")
                return False
        
        # 락 파일 생성
        with open(lock_file, 'w') as f:
            f.write(f"{os.getpid()}\n{datetime.now().isoformat()}")
        
        logger.info(f"프로세스 락 획득: {lock_file}")
        return True
        
    except Exception as e:
        logger.error(f"락 획득 중 오류 발생: {e}")
        return False


def release_lock(lock_file: str):
    """
    프로세스 락을 해제합니다.
    
    Args:
        lock_file: 락 파일 경로
    """
    try:
        if os.path.exists(lock_file):
            os.remove(lock_file)
            logger.info(f"프로세스 락 해제: {lock_file}")
    except Exception as e:
        logger.error(f"락 해제 중 오류 발생: {e}")


def main():
    """메인 실행 함수"""
    lock_file = "logs/trading.lock"
    
    # 중복 실행 방지
    if not acquire_lock(lock_file):
        return 1
    
    try:
        system = DartScrapingSystem()
        success = system.run()
        
        if success:
            logger.info("✅ 시스템이 성공적으로 완료되었습니다.")
            return 0
        else:
            logger.error("❌ 시스템 실행 중 오류가 발생했습니다.")
            return 1
    
    finally:
        # 락 해제
        release_lock(lock_file)


if __name__ == '__main__':
    exit(main())
