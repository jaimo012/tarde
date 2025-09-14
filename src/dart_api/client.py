"""
DART API 클라이언트

이 모듈은 DART(전자공시시스템) API와의 통신을 담당합니다.
공시 검색, 문서 다운로드 등의 기능을 제공합니다.
"""

import requests
import time
import os
import zipfile
import tempfile
import shutil
from typing import List, Dict, Optional
from loguru import logger

from config.settings import DART_API_KEY, DART_API_CONFIG, REPORT_SEARCH_CONFIG


class DartApiClient:
    """DART API와의 통신을 담당하는 클라이언트 클래스"""
    
    def __init__(self, api_key: str = DART_API_KEY):
        """
        DART API 클라이언트를 초기화합니다.
        
        Args:
            api_key (str): DART API 인증키
        """
        self.api_key = api_key
        self.base_url = DART_API_CONFIG['base_url']
        self.request_delay = DART_API_CONFIG['request_delay']
        
        logger.info(f"DART API 클라이언트가 초기화되었습니다. (API Key: {api_key[:10]}...)")
    
    def search_disclosures_all_pages(self, corp_code: str) -> List[Dict]:
        """
        특정 회사의 '단일판매ㆍ공급계약체결' 공시를 모든 페이지에서 검색합니다.
        
        Args:
            corp_code (str): 회사의 고유번호 (8자리)
            
        Returns:
            List[Dict]: 검색된 공시 목록
        """
        all_results = []
        current_page = 1
        
        logger.info(f"회사({corp_code})의 공시 검색을 시작합니다.")
        
        while True:
            # API 요청 파라미터 설정
            params = {
                'crtfc_key': self.api_key,
                'corp_code': corp_code,
                'bgn_de': DART_API_CONFIG['search_start_date'],
                'pblntf_ty': 'I',  # 정기공시가 아닌 수시공시
                'sort': 'date',
                'sort_mth': 'desc',  # 최신순 정렬
                'page_no': current_page,
                'page_count': DART_API_CONFIG['page_size']
            }
            
            try:
                # API 요청 실행
                response = requests.get(
                    f"{self.base_url}{DART_API_CONFIG['list_endpoint']}", 
                    params=params,
                    timeout=30
                )
                response.raise_for_status()
                data = response.json()
                
                # API 응답 상태 확인
                if data.get('status') != '000':
                    logger.warning(f"API 응답 오류: {data.get('message', '알 수 없는 오류')}")
                    break
                
                # 검색 결과가 있는지 확인
                if 'list' not in data or not data['list']:
                    logger.info(f"페이지 {current_page}에서 더 이상 검색 결과가 없습니다.")
                    break
                
                # 단일판매 관련 공시만 필터링
                filtered_list = self._filter_target_reports(data['list'])
                all_results.extend(filtered_list)
                
                logger.debug(f"페이지 {current_page}: {len(filtered_list)}개의 관련 공시 발견")
                
                # 마지막 페이지 확인
                if current_page >= data.get('total_page', 1):
                    break
                    
                current_page += 1
                time.sleep(self.request_delay)  # API 호출 제한 준수
                
            except requests.exceptions.RequestException as e:
                logger.error(f"API 요청 중 오류 발생: {e}")
                break
            except Exception as e:
                logger.error(f"예상치 못한 오류 발생: {e}")
                break
        
        logger.info(f"회사({corp_code}) 검색 완료: 총 {len(all_results)}개의 관련 공시 발견")
        return all_results
    
    def _filter_target_reports(self, reports: List[Dict]) -> List[Dict]:
        """
        보고서 목록에서 단일판매 관련 보고서만 필터링합니다.
        
        Args:
            reports (List[Dict]): 전체 보고서 목록
            
        Returns:
            List[Dict]: 필터링된 보고서 목록
        """
        filtered_reports = []
        
        for report in reports:
            report_name = report.get('report_nm', '')
            
            # 포함되어야 할 키워드 확인
            include_match = any(
                keyword in report_name 
                for keyword in REPORT_SEARCH_CONFIG['include_keywords']
            )
            
            # 제외되어야 할 키워드 확인
            exclude_match = any(
                keyword in report_name 
                for keyword in REPORT_SEARCH_CONFIG['exclude_keywords']
            )
            
            if include_match and not exclude_match:
                filtered_reports.append(report)
        
        return filtered_reports
    
    def download_report_document(self, rcept_no: str) -> Optional[bytes]:
        """
        접수번호를 기반으로 공시 원본파일(ZIP)을 다운로드합니다.
        
        Args:
            rcept_no (str): 공시 접수번호
            
        Returns:
            Optional[bytes]: 다운로드된 파일 내용 (실패 시 None)
        """
        api_url = f"{self.base_url}{DART_API_CONFIG['document_endpoint']}"
        params = {
            'crtfc_key': self.api_key,
            'rcept_no': rcept_no
        }
        
        try:
            logger.debug(f"보고서({rcept_no}) 다운로드를 시작합니다.")
            
            response = requests.get(api_url, params=params, timeout=60)
            response.raise_for_status()
            
            if response.status_code == 200:
                logger.debug(f"보고서({rcept_no}) 다운로드 완료")
                return response.content
            else:
                logger.warning(f"보고서({rcept_no}) 다운로드 실패 (상태 코드: {response.status_code})")
                return None
                
        except requests.exceptions.RequestException as e:
            logger.error(f"보고서({rcept_no}) 다운로드 중 오류 발생: {e}")
            return None
    
    def extract_document_from_zip(self, zip_content: bytes, rcept_no: str) -> Optional[str]:
        """
        ZIP 파일에서 보고서 본문을 추출합니다.
        
        Args:
            zip_content (bytes): ZIP 파일 내용
            rcept_no (str): 접수번호 (로깅용)
            
        Returns:
            Optional[str]: 추출된 HTML/XML 내용 (실패 시 None)
        """
        temp_dir = tempfile.mkdtemp()
        
        try:
            # ZIP 파일을 임시 디렉토리에 저장
            zip_file_path = os.path.join(temp_dir, f"{rcept_no}.zip")
            with open(zip_file_path, 'wb') as f:
                f.write(zip_content)
            
            # ZIP 파일 압축 해제
            with zipfile.ZipFile(zip_file_path, 'r') as zip_ref:
                zip_ref.extractall(temp_dir)
            
            # 보고서 본문 파일 찾기 (HTML 또는 XML 파일)
            report_file_path = None
            for file_name in os.listdir(temp_dir):
                if file_name.endswith(('.xml', '.html', '.htm')):
                    report_file_path = os.path.join(temp_dir, file_name)
                    break
            
            if not report_file_path:
                logger.warning(f"보고서({rcept_no}) ZIP 파일 내에서 본문 파일을 찾을 수 없습니다.")
                return None
            
            # 파일 내용 읽기
            with open(report_file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            logger.debug(f"보고서({rcept_no}) 본문 추출 완료")
            return content
            
        except Exception as e:
            logger.error(f"보고서({rcept_no}) ZIP 파일 처리 중 오류 발생: {e}")
            return None
            
        finally:
            # 임시 디렉토리 정리
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
    
    def get_report_content(self, rcept_no: str) -> Optional[str]:
        """
        접수번호로 보고서 전체 내용을 가져옵니다.
        
        Args:
            rcept_no (str): 공시 접수번호
            
        Returns:
            Optional[str]: 보고서 HTML/XML 내용 (실패 시 None)
        """
        # 1단계: ZIP 파일 다운로드
        zip_content = self.download_report_document(rcept_no)
        if not zip_content:
            return None
        
        # 2단계: ZIP 파일에서 본문 추출
        document_content = self.extract_document_from_zip(zip_content, rcept_no)
        return document_content
