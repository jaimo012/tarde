"""
DART 공시 스크래핑 및 구글 시트 저장 자동화 메인 실행 모듈

이 모듈은 전체 시스템의 실행 흐름을 관리합니다.
"""

import time
from typing import List, Dict
from loguru import logger

from config.settings import LOGGING_CONFIG, REQUIRED_FIELDS, SLACK_WEBHOOK_URL
from src.dart_api.client import DartApiClient
from src.dart_api.analyzer import ReportAnalyzer
from src.google_sheets.client import GoogleSheetsClient
from src.utils.slack_notifier import SlackNotifier
from src.utils.market_schedule import should_run_dart_scraping, get_market_status


class DartScrapingSystem:
    """DART 공시 스크래핑 시스템의 메인 클래스"""
    
    def __init__(self):
        """시스템 컴포넌트들을 초기화합니다."""
        self.dart_client = DartApiClient()
        self.analyzer = ReportAnalyzer()
        self.sheets_client = GoogleSheetsClient()
        self.slack_notifier = SlackNotifier(SLACK_WEBHOOK_URL)
        
        # 로깅 설정
        self._setup_logging()
        
        logger.info("DART 스크래핑 시스템이 초기화되었습니다.")
    
    def _setup_logging(self):
        """로깅 설정을 초기화합니다."""
        logger.add(
            LOGGING_CONFIG['file_path'],
            format=LOGGING_CONFIG['format'],
            level=LOGGING_CONFIG['level'],
            rotation=LOGGING_CONFIG['rotation'],
            retention=LOGGING_CONFIG['retention'],
            encoding='utf-8'
        )
    
    def run(self) -> bool:
        """
        전체 스크래핑 프로세스를 실행합니다.
        
        Returns:
            bool: 실행 성공 여부
        """
        logger.info("🚀 DART 공시 스크래핑 및 구글 시트 저장 자동화를 시작합니다.")
        
        try:
            # 0단계: 시장 개장 여부 확인
            should_run, market_status = should_run_dart_scraping()
            logger.info(f"📊 시장 상태: {market_status}")
            
            if not should_run:
                logger.info("⏸️ 시장이 휴장 중이므로 스크래핑을 건너뜁니다.")
                
                # 휴장일 알림 전송
                self.slack_notifier.send_system_notification(
                    f"⏸️ DART 스크래핑 건너뜀: {market_status}",
                    "info"
                )
                
                return True  # 정상적인 스킵이므로 True 반환
            
            logger.info("✅ 시장 개장 중이므로 스크래핑을 진행합니다.")
            
            # 1단계: 구글 스프레드시트 연결
            if not self._connect_to_sheets():
                return False
            
            # 2단계: 기존 데이터 로드
            existing_reports, company_list = self._load_existing_data()
            if company_list is None:
                return False
            
            # 3단계: 각 회사별 공시 처리
            total_new_contracts = self._process_companies(company_list, existing_reports)
            
            # 4단계: 완료 알림
            completion_message = f"🏁 모든 회사에 대한 분석 및 저장이 완료되었습니다. (신규 계약: {total_new_contracts}건)"
            logger.info(completion_message)
            
            # 시스템 완료 알림 전송
            if total_new_contracts > 0:
                self.slack_notifier.send_system_notification(
                    f"DART 스크래핑 완료: 총 {total_new_contracts}건의 신규 계약을 발견했습니다.",
                    "info"
                )
            else:
                self.slack_notifier.send_system_notification(
                    f"DART 스크래핑 완료: 신규 계약이 발견되지 않았습니다. ({market_status})",
                    "info"
                )
            
            return True
            
        except Exception as e:
            logger.error(f"시스템 실행 중 예상치 못한 오류 발생: {e}")
            # 오류 발생 시 슬랙 알림
            self.slack_notifier.send_system_notification(
                f"❌ 시스템 실행 중 오류 발생: {str(e)}",
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
        
        for index, company_row in company_list.iterrows():
            corp_code = company_row['조회코드']
            corp_name = company_row['종목명']
            
            logger.info(f"🔎 [{index+1}/{total_companies}] '{corp_name}'({corp_code}) 처리 시작...")
            
            try:
                # 회사별 공시 처리
                new_contracts, new_excluded = self._process_company_disclosures(
                    company_row, existing_reports
                )
                
                # 결과 저장 및 슬랙 알림
                saved_contracts = self._save_company_results(corp_name, new_contracts, new_excluded)
                total_new_contracts += saved_contracts
                
            except Exception as e:
                logger.error(f"회사 '{corp_name}' 처리 중 오류 발생: {e}")
                # 오류 발생 시 슬랙 알림
                self.slack_notifier.send_system_notification(
                    f"❌ 회사 '{corp_name}' 처리 중 오류 발생: {str(e)}",
                    "error"
                )
                continue
        
        return total_new_contracts
    
    def _process_company_disclosures(self, company_row, existing_reports: set) -> tuple:
        """특정 회사의 공시를 처리합니다."""
        corp_code = company_row['조회코드']
        corp_name = company_row['종목명']
        
        new_contracts = []
        new_excluded = []
        
        # 1단계: 공시 검색
        disclosures = self.dart_client.search_disclosures_all_pages(corp_code)
        if not disclosures:
            logger.info(f" -> '{corp_name}'의 관련 공시를 찾지 못했습니다.")
            return new_contracts, new_excluded
        
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
                    
                else:
                    logger.error(f"   ❌ '{corp_name}': 계약 데이터 저장 실패")
                    # 저장 실패 알림
                    self.slack_notifier.send_system_notification(
                        f"❌ '{corp_name}': 계약 데이터 저장 실패",
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
            # 저장 오류 알림
            self.slack_notifier.send_system_notification(
                f"❌ '{corp_name}' 결과 저장 중 오류: {str(e)}",
                "error"
            )
        
        return saved_contracts_count


def main():
    """메인 실행 함수"""
    system = DartScrapingSystem()
    success = system.run()
    
    if success:
        logger.info("✅ 시스템이 성공적으로 완료되었습니다.")
        return 0
    else:
        logger.error("❌ 시스템 실행 중 오류가 발생했습니다.")
        return 1


if __name__ == '__main__':
    exit(main())
