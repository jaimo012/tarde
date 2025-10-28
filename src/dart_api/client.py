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
from utils.error_handler import get_error_handler


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
        error_handler = get_error_handler()
        
        # 입력값 검증 (1단계)
        if not rcept_no or not isinstance(rcept_no, str):
            error_msg = f"잘못된 접수번호: {rcept_no}"
            logger.error(error_msg)
            if error_handler:
                error_handler.handle_error(
                    error=ValueError(error_msg),
                    module="dart_api.client",
                    operation="download_report_document",
                    severity="ERROR",
                    additional_context={"rcept_no": rcept_no}
                )
            return None
        
        api_url = f"{self.base_url}{DART_API_CONFIG['document_endpoint']}"
        params = {
            'crtfc_key': self.api_key,
            'rcept_no': rcept_no
        }
        
        try:
            logger.debug(f"보고서({rcept_no}) 다운로드를 시작합니다.")
            
            # 2단계: 핵심 로직 실행
            response = requests.get(api_url, params=params, timeout=60)
            response.raise_for_status()
            
            # 3단계: 결과 검증
            if response.status_code == 200 and response.content:
                content_length = len(response.content)
                logger.debug(f"보고서({rcept_no}) 다운로드 완료: {content_length:,} bytes")
                
                # 다운로드된 파일이 너무 작으면 오류로 판단
                if content_length < 100:
                    raise ValueError(f"다운로드된 파일 크기가 너무 작음: {content_length} bytes")
                    
                return response.content
            else:
                error_msg = f"보고서 다운로드 실패 (상태 코드: {response.status_code})"
                logger.warning(error_msg)
                if error_handler:
                    error_handler.handle_error(
                        error=RuntimeError(error_msg),
                        module="dart_api.client",
                        operation="download_report_document",
                        severity="WARNING",
                        related_stock=f"접수번호:{rcept_no}",
                        additional_context={
                            "status_code": response.status_code,
                            "content_length": len(response.content) if response.content else 0
                        }
                    )
                return None
                
        except requests.exceptions.Timeout as e:
            if error_handler:
                error_handler.handle_error(
                    error=e,
                    module="dart_api.client", 
                    operation="download_report_document",
                    severity="WARNING",
                    related_stock=f"접수번호:{rcept_no}",
                    additional_context={"timeout": 60, "api_url": api_url},
                    auto_recovery_attempted=True
                )
            logger.warning(f"보고서({rcept_no}) 다운로드 타임아웃 (60초)")
            return None
            
        except requests.exceptions.ConnectionError as e:
            if error_handler:
                error_handler.handle_error(
                    error=e,
                    module="dart_api.client",
                    operation="download_report_document", 
                    severity="ERROR",
                    related_stock=f"접수번호:{rcept_no}",
                    additional_context={"api_url": api_url},
                    auto_recovery_attempted=False
                )
            logger.error(f"보고서({rcept_no}) 다운로드 연결 오류: {e}")
            return None
            
        except requests.exceptions.RequestException as e:
            if error_handler:
                error_handler.handle_error(
                    error=e,
                    module="dart_api.client",
                    operation="download_report_document",
                    severity="ERROR", 
                    related_stock=f"접수번호:{rcept_no}",
                    additional_context={"api_url": api_url, "params": {"rcept_no": rcept_no}}
                )
            logger.error(f"보고서({rcept_no}) 다운로드 중 요청 오류: {e}")
            return None
            
        except Exception as e:
            if error_handler:
                error_handler.handle_error(
                    error=e,
                    module="dart_api.client",
                    operation="download_report_document",
                    severity="CRITICAL",
                    related_stock=f"접수번호:{rcept_no}",
                    additional_context={"api_url": api_url, "params": {"rcept_no": rcept_no}}
                )
            logger.error(f"보고서({rcept_no}) 다운로드 중 예상치 못한 오류: {e}")
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
        error_handler = get_error_handler()
        temp_dir = None
        
        # 1단계: 입력값 검증
        if not zip_content or not isinstance(zip_content, bytes):
            error_msg = f"잘못된 ZIP 내용: {type(zip_content)}, 크기: {len(zip_content) if zip_content else 0}"
            logger.error(error_msg)
            if error_handler:
                error_handler.handle_error(
                    error=ValueError(error_msg),
                    module="dart_api.client",
                    operation="extract_document_from_zip",
                    severity="ERROR",
                    related_stock=f"접수번호:{rcept_no}",
                    additional_context={"zip_size": len(zip_content) if zip_content else 0}
                )
            return None
        
        if not rcept_no:
            error_msg = "접수번호가 없습니다"
            logger.error(error_msg)
            if error_handler:
                error_handler.handle_error(
                    error=ValueError(error_msg),
                    module="dart_api.client", 
                    operation="extract_document_from_zip",
                    severity="ERROR"
                )
            return None
        
        try:
            # 2단계: 핵심 로직 실행
            temp_dir = tempfile.mkdtemp()
            logger.debug(f"보고서({rcept_no}) ZIP 압축 해제 시작: {len(zip_content):,} bytes")
            
            # ZIP 파일을 임시 디렉토리에 저장
            zip_file_path = os.path.join(temp_dir, f"{rcept_no}.zip")
            with open(zip_file_path, 'wb') as f:
                f.write(zip_content)
            
            # ZIP 파일 검증 및 압축 해제
            try:
                with zipfile.ZipFile(zip_file_path, 'r') as zip_ref:
                    # ZIP 파일 무결성 검사
                    bad_file = zip_ref.testzip()
                    if bad_file:
                        raise zipfile.BadZipFile(f"손상된 파일 발견: {bad_file}")
                    
                    zip_ref.extractall(temp_dir)
                    logger.debug(f"보고서({rcept_no}) ZIP 압축 해제 완료")
                    
            except zipfile.BadZipFile as e:
                if error_handler:
                    error_handler.handle_error(
                        error=e,
                        module="dart_api.client",
                        operation="extract_document_from_zip",
                        severity="ERROR",
                        related_stock=f"접수번호:{rcept_no}",
                        additional_context={"zip_size": len(zip_content)}
                    )
                logger.error(f"보고서({rcept_no}) ZIP 파일이 손상됨: {e}")
                return None
            
            # 보고서 본문 파일 찾기 (HTML 또는 XML 파일)
            report_file_path = None
            available_files = []
            
            for file_name in os.listdir(temp_dir):
                if file_name != f"{rcept_no}.zip":  # ZIP 파일은 제외
                    available_files.append(file_name)
                    if file_name.endswith(('.xml', '.html', '.htm')):
                        report_file_path = os.path.join(temp_dir, file_name)
                        logger.debug(f"보고서 본문 파일 발견: {file_name}")
                        break
            
            # 3단계: 결과 검증
            if not report_file_path:
                error_msg = f"보고서 본문 파일을 찾을 수 없음. 사용 가능한 파일: {available_files}"
                logger.warning(error_msg)
                if error_handler:
                    error_handler.handle_error(
                        error=FileNotFoundError(error_msg),
                        module="dart_api.client",
                        operation="extract_document_from_zip",
                        severity="WARNING",
                        related_stock=f"접수번호:{rcept_no}",
                        additional_context={"available_files": available_files}
                    )
                return None
            
            # 파일 내용 읽기
            try:
                with open(report_file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                
                # 내용 검증
                if not content or len(content.strip()) < 100:
                    raise ValueError(f"추출된 내용이 너무 짧음: {len(content)} 문자")
                    
                logger.debug(f"보고서({rcept_no}) 본문 추출 완료: {len(content):,} 문자")
                return content
                
            except UnicodeDecodeError:
                # UTF-8 실패 시 다른 인코딩 시도
                logger.warning(f"UTF-8 디코딩 실패, 다른 인코딩 시도: {rcept_no}")
                for encoding in ['cp949', 'euc-kr', 'iso-8859-1']:
                    try:
                        with open(report_file_path, 'r', encoding=encoding, errors='ignore') as f:
                            content = f.read()
                        if content and len(content.strip()) >= 100:
                            logger.info(f"보고서({rcept_no}) {encoding} 인코딩으로 성공")
                            return content
                    except Exception:
                        continue
                
                # 모든 인코딩 실패
                error_msg = f"모든 인코딩 시도 실패"
                if error_handler:
                    error_handler.handle_error(
                        error=UnicodeDecodeError('all-encodings', b'', 0, 1, error_msg),
                        module="dart_api.client",
                        operation="extract_document_from_zip",
                        severity="ERROR",
                        related_stock=f"접수번호:{rcept_no}",
                        additional_context={"attempted_encodings": ['utf-8', 'cp949', 'euc-kr', 'iso-8859-1']}
                    )
                return None
                
        except PermissionError as e:
            if error_handler:
                error_handler.handle_error(
                    error=e,
                    module="dart_api.client",
                    operation="extract_document_from_zip",
                    severity="ERROR",
                    related_stock=f"접수번호:{rcept_no}",
                    additional_context={"temp_dir": temp_dir}
                )
            logger.error(f"보고서({rcept_no}) 파일 권한 오류: {e}")
            return None
            
        except OSError as e:
            if error_handler:
                error_handler.handle_error(
                    error=e,
                    module="dart_api.client",
                    operation="extract_document_from_zip",
                    severity="ERROR",
                    related_stock=f"접수번호:{rcept_no}",
                    additional_context={"temp_dir": temp_dir}
                )
            logger.error(f"보고서({rcept_no}) 파일 시스템 오류: {e}")
            return None
            
        except Exception as e:
            if error_handler:
                error_handler.handle_error(
                    error=e,
                    module="dart_api.client",
                    operation="extract_document_from_zip",
                    severity="CRITICAL",
                    related_stock=f"접수번호:{rcept_no}",
                    additional_context={"temp_dir": temp_dir, "zip_size": len(zip_content)}
                )
            logger.error(f"보고서({rcept_no}) ZIP 파일 처리 중 예상치 못한 오류: {e}")
            return None
            
        finally:
            # 임시 디렉토리 정리
            if temp_dir and os.path.exists(temp_dir):
                try:
                    shutil.rmtree(temp_dir)
                    logger.debug(f"임시 디렉토리 정리 완료: {temp_dir}")
                except Exception as cleanup_error:
                    logger.warning(f"임시 디렉토리 정리 실패: {cleanup_error}")
                    if error_handler:
                        error_handler.handle_error(
                            error=cleanup_error,
                            module="dart_api.client",
                            operation="extract_document_from_zip_cleanup",
                            severity="WARNING",
                            additional_context={"temp_dir": temp_dir}
                        )
    
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
